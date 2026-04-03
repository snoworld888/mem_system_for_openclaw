#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理并重建 ChromaDB 数据库
"""
import os
import sys
import json
import math
import hashlib
import re
import shutil
from collections import Counter
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(__file__).parent / "data"
CHROMADB_DIR = DATA_DIR / "chromadb"
EXPORT_FILE = DATA_DIR / "chromadb_export.json"


class TFIDFEmbedder:
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
                idf = 1.0 + math.log(1 + 1 / (1 + 0))
                bucket = self._hash_term(term)
                vec[bucket] += tf_val * idf
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vec = [v / norm for v in vec]
            result.append(vec)
        return result


def force_delete(path: Path):
    """强制删除目录"""
    print(f"[CLEAN] 删除: {path}")
    for root, dirs, files in os.walk(path, topdown=False):
        for f in files:
            fp = os.path.join(root, f)
            try:
                os.chmod(fp, 0o777)
                os.remove(fp)
            except Exception as e:
                print(f"  [WARN] 无法删除 {fp}: {e}")
        for d in dirs:
            dp = os.path.join(root, d)
            try:
                os.chmod(dp, 0o777)
                os.rmdir(dp)
            except:
                pass
    try:
        shutil.rmtree(path, ignore_errors=True)
    except:
        pass
    print("[OK] 清理完成")


def main():
    print("=" * 60)
    print("ChromaDB 清理并重建")
    print("=" * 60)

    # Step 1: 强制删除旧数据库
    if CHROMADB_DIR.exists():
        force_delete(CHROMADB_DIR)

    # Step 2: 创建新目录
    os.makedirs(CHROMADB_DIR, exist_ok=True)
    print(f"\n[INIT] 创建目录: {CHROMADB_DIR}")

    # Step 3: 导入数据
    if not EXPORT_FILE.exists():
        print("[ERROR] 导出文件不存在，跳过导入")
        return 0

    print(f"\n[LOAD] 读取导出数据: {EXPORT_FILE}")
    with open(EXPORT_FILE, "r", encoding="utf-8") as f:
        export_data = json.load(f)

    client_export = export_data.get("chromadb_client_export")
    if not client_export:
        print("[ERROR] 未找到客户端导出数据")
        return 1

    collections_data = client_export.get("collections", [])
    if not collections_data:
        print("[WARN] 没有要导入的 collection")
        return 0

    # 初始化
    print("\n[INIT] 初始化 ChromaDB...")
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    embedder = TFIDFEmbedder()

    client = chromadb.PersistentClient(
        path=str(CHROMADB_DIR),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    print("[OK] ChromaDB 初始化成功")

    # 导入数据
    total_imported = 0
    for col_data in collections_data:
        name = col_data.get("name")
        if not name or col_data.get("error"):
            continue

        ids = col_data.get("ids", [])
        documents = col_data.get("documents", [])
        metadatas = col_data.get("metadatas", [])

        if not ids:
            continue

        print(f"\n[IMPORT] {name}: {len(ids)} 条")

        try:
            collection = client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            print(f"  [ERROR] {e}")
            continue

        batch_size = 50
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_docs = documents[i:i+batch_size]
            batch_metas = metadatas[i:i+batch_size]
            embeddings = embedder.encode(batch_docs)

            try:
                collection.upsert(
                    ids=batch_ids,
                    documents=batch_docs,
                    metadatas=batch_metas,
                    embeddings=embeddings,
                )
                print(f"  [OK] {len(batch_ids)} 条")
                total_imported += len(batch_ids)
            except Exception as e:
                print(f"  [ERROR] {e}")

    print("\n" + "=" * 60)
    print(f"[DONE] 完成! 共导入 {total_imported} 条记录")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
