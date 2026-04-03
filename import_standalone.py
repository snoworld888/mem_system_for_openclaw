#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChromaDB 数据导入脚本（独立版本，无外部依赖）
从导出的 JSON 文件恢复数据到新的 ChromaDB
"""
import os
import sys
import json
import math
import hashlib
import re
from collections import Counter
from pathlib import Path

# 修复 Windows 控制台编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(__file__).parent / "data"
EXPORT_FILE = DATA_DIR / "chromadb_export.json"


class TFIDFEmbedder:
    """基于TF-IDF的轻量嵌入器（完全离线）"""
    DIM = 512

    def _tokenize(self, text: str) -> list[str]:
        text = text.lower().strip()
        tokens = []
        eng = re.findall(r"[a-z0-9]+", text)
        tokens.extend(eng)
        chinese = re.findall(r"[\u4e00-\u9fff]", text)
        tokens.extend(chinese)
        for i in range(len(chinese) - 1):
            tokens.append(chinese[i] + chinese[i + 1])
        return tokens

    def _hash_term(self, term: str) -> int:
        return int(hashlib.md5(term.encode()).hexdigest(), 16) % self.DIM

    def encode(self, texts: list[str]) -> list[list[float]]:
        result = []
        for text in texts:
            tokens = self._tokenize(text)
            if not tokens:
                result.append([0.0] * self.DIM)
                continue
            tf = Counter(tokens)
            vec = [0.0] * self.DIM
            total = sum(tf.values())
            for term, cnt in tf.items():
                tf_val = cnt / total
                idf = 1.0 + math.log(1 + 1 / (1 + 0))  # 简化IDF
                bucket = self._hash_term(term)
                vec[bucket] += tf_val * idf
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vec = [v / norm for v in vec]
            result.append(vec)
        return result


def import_data():
    """从导出文件导入数据到新的 ChromaDB"""
    if not EXPORT_FILE.exists():
        print(f"[ERROR] 导出文件不存在: {EXPORT_FILE}")
        return 1
    
    print("=" * 60)
    print("ChromaDB 数据导入工具（独立版）")
    print("=" * 60)
    
    # 读取导出数据
    print(f"\n[LOAD] 读取导出数据: {EXPORT_FILE}")
    with open(EXPORT_FILE, "r", encoding="utf-8") as f:
        export_data = json.load(f)
    
    client_export = export_data.get("chromadb_client_export")
    if not client_export:
        print("[ERROR] 未找到客户端导出数据")
        return 1
    
    collections_data = client_export.get("collections", [])
    if not collections_data:
        print("[ERROR] 没有要导入的 collection")
        return 1
    
    # 初始化 embedder
    print("\n[INIT] 初始化 TF-IDF Embedder...")
    embedder = TFIDFEmbedder()
    
    # 初始化新的 ChromaDB
    print("[INIT] 初始化新的 ChromaDB...")
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    
    db_path = DATA_DIR / "chromadb"
    
    # 删除旧的数据库（如果存在且损坏）
    if db_path.exists():
        import shutil
        print(f"[CLEAN] 清理旧数据库...")
        try:
            shutil.rmtree(db_path)
        except Exception as e:
            print(f"[WARN] 无法删除旧数据库: {e}")
            print("[INFO] 尝试直接使用...")
    
    os.makedirs(db_path, exist_ok=True)
    
    try:
        client = chromadb.PersistentClient(
            path=str(db_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        print(f"[OK] ChromaDB 初始化成功: {db_path}")
    except Exception as e:
        print(f"[ERROR] ChromaDB 初始化失败: {e}")
        return 1
    
    # 导入每个 collection
    total_imported = 0
    for col_data in collections_data:
        name = col_data.get("name")
        if not name:
            continue
        
        error = col_data.get("error")
        if error:
            print(f"\n[SKIP] {name}: {error}")
            continue
        
        ids = col_data.get("ids", [])
        documents = col_data.get("documents", [])
        metadatas = col_data.get("metadatas", [])
        
        if not ids:
            print(f"\n[SKIP] {name}: 无数据")
            continue
        
        print(f"\n[IMPORT] {name}: {len(ids)} 条记录")
        
        # 创建 collection
        try:
            collection = client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            print(f"  [ERROR] 创建 collection 失败: {e}")
            continue
        
        # 批量导入
        batch_size = 50
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_docs = documents[i:i+batch_size]
            batch_metas = metadatas[i:i+batch_size]
            
            print(f"  [EMBED] 生成向量 {i+1}-{min(i+batch_size, len(ids))}...")
            embeddings = embedder.encode(batch_docs)
            
            try:
                collection.upsert(
                    ids=batch_ids,
                    documents=batch_docs,
                    metadatas=batch_metas,
                    embeddings=embeddings,
                )
                print(f"  [OK] 导入 {len(batch_ids)} 条")
                total_imported += len(batch_ids)
            except Exception as e:
                print(f"  [ERROR] 导入失败: {e}")
    
    print("\n" + "=" * 60)
    print(f"[DONE] 导入完成! 共导入 {total_imported} 条记录")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(import_data())
