#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChromaDB 数据迁移脚本
- 备份损坏的 ChromaDB 数据
- 尝试从 SQLite 导出数据
- 重建 ChromaDB 并导入数据
"""
import os
import sys
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

# 修复 Windows 控制台编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
CHROMADB_DIR = DATA_DIR / "chromadb"
BACKUP_DIR = DATA_DIR / f"chromadb_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
EXPORT_FILE = DATA_DIR / "chromadb_export.json"


def backup_chromadb():
    """备份 ChromaDB 数据目录"""
    if not CHROMADB_DIR.exists():
        print("❌ ChromaDB 目录不存在")
        return False
    
    print(f"📦 备份 ChromaDB 到: {BACKUP_DIR}")
    shutil.copytree(CHROMADB_DIR, BACKUP_DIR)
    print("✅ 备份完成")
    return True


def export_from_sqlite():
    """从 SQLite 数据库导出数据"""
    sqlite_path = BACKUP_DIR / "chroma.sqlite3"
    if not sqlite_path.exists():
        print("❌ SQLite 数据库文件不存在")
        return None
    
    print(f"\n📊 从 SQLite 导出数据: {sqlite_path}")
    
    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 查看表结构
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    print(f"📋 发现表: {[t['name'] for t in tables]}")
    
    exported_data = {
        "collections": [],
        "embeddings": [],
        "metadata": [],
        "export_time": datetime.now().isoformat(),
        "status": "partial"  # 可能无法导出嵌入向量
    }
    
    try:
        # 导出 collections
        collections = cursor.execute("SELECT * FROM collections").fetchall()
        print(f"\n✅ 发现 {len(collections)} 个 collection:")
        for col in collections:
            col_dict = dict(col)
            print(f"   - {col_dict.get('name', 'unknown')}: id={col_dict.get('id')}")
            exported_data["collections"].append(col_dict)
        
        # 导出 embeddings (segment 相关)
        # ChromaDB 的向量存储在 segments 表中
        segments = cursor.execute("SELECT * FROM segments").fetchall()
        print(f"\n📦 发现 {len(segments)} 个 segment")
        for seg in segments:
            exported_data["metadata"].append(dict(seg))
        
        # 尝试导出 embedding_fulltext_search (如果有)
        try:
            # 检查是否有嵌入数据表
            for table in tables:
                table_name = table['name']
                if 'embedding' in table_name.lower() or 'vector' in table_name.lower():
                    rows = cursor.execute(f"SELECT * FROM {table_name} LIMIT 10").fetchall()
                    print(f"   - {table_name}: {len(rows)} 行示例")
                    for row in rows:
                        exported_data["embeddings"].append(dict(row))
        except Exception as e:
            print(f"   ⚠️ 导出嵌入向量失败: {e}")
        
        exported_data["status"] = "success"
        print("\n✅ SQLite 数据导出成功")
        
    except Exception as e:
        print(f"\n❌ 导出失败: {e}")
        exported_data["status"] = f"error: {str(e)}"
    finally:
        conn.close()
    
    return exported_data


def try_export_via_chromadb_client():
    """尝试用 ChromaDB 客户端导出（可能失败）"""
    print("\n🔄 尝试用 ChromaDB 客户端导出...")
    
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        
        # 使用备份目录
        client = chromadb.PersistentClient(
            path=str(BACKUP_DIR),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        
        collections = client.list_collections()
        print(f"✅ 成功连接，发现 {len(collections)} 个 collection")
        
        exported_data = {
            "collections": [],
            "method": "chromadb_client",
            "export_time": datetime.now().isoformat()
        }
        
        for col in collections:
            print(f"\n📦 导出 collection: {col.name}")
            try:
                # 获取所有数据
                result = col.get(include=["documents", "metadatas", "embeddings"])
                
                col_data = {
                    "name": col.name,
                    "metadata": col.metadata,
                    "count": len(result["ids"]),
                    "ids": result["ids"],
                    "documents": result["documents"],
                    "metadatas": result["metadatas"],
                    "embeddings": result.get("embeddings", []),
                }
                exported_data["collections"].append(col_data)
                print(f"   ✅ 导出 {len(result['ids'])} 条记录")
            except Exception as e:
                print(f"   ❌ 导出失败: {e}")
                col_data = {
                    "name": col.name,
                    "error": str(e)
                }
                exported_data["collections"].append(col_data)
        
        return exported_data
        
    except Exception as e:
        print(f"❌ ChromaDB 客户端导出失败: {e}")
        return None


def save_export(data: dict):
    """保存导出数据到 JSON"""
    print(f"\n💾 保存导出数据到: {EXPORT_FILE}")
    
    # 处理不可序列化的数据
    def json_serializer(obj):
        if isinstance(obj, bytes):
            return f"<bytes:{len(obj)}>"
        if isinstance(obj, (list, dict)):
            return obj
        return str(obj)
    
    with open(EXPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=json_serializer)
    
    print("✅ 导出数据已保存")
    print(f"   文件大小: {EXPORT_FILE.stat().st_size / 1024:.1f} KB")


def remove_corrupted_db():
    """删除损坏的数据库"""
    print(f"\n🗑️ 删除损坏的 ChromaDB: {CHROMADB_DIR}")
    shutil.rmtree(CHROMADB_DIR)
    print("✅ 已删除")


def main():
    print("=" * 60)
    print("ChromaDB 数据迁移工具")
    print("=" * 60)
    
    # Step 1: 备份
    if not backup_chromadb():
        return 1
    
    # Step 2: 尝试用 ChromaDB 客户端导出（可能失败）
    client_export = try_export_via_chromadb_client()
    
    # Step 3: 从 SQLite 直接导出（备用方案）
    sqlite_export = export_from_sqlite()
    
    # Step 4: 合并导出数据
    final_export = {
        "chromadb_client_export": client_export,
        "sqlite_export": sqlite_export,
        "backup_dir": str(BACKUP_DIR),
    }
    save_export(final_export)
    
    # Step 5: 显示下一步操作
    print("\n" + "=" * 60)
    print("下一步操作:")
    print("1. 导出数据已保存，请检查导出结果")
    print("2. 确认无误后，运行以下命令删除损坏的数据库:")
    print(f"   rm -rf {CHROMADB_DIR}")
    print("   或在 Windows PowerShell:")
    print(f"   Remove-Item -Recurse -Force {CHROMADB_DIR}")
    print("3. 重新启动服务，ChromaDB 会自动重建")
    print("=" * 60)
    
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--delete":
        remove_corrupted_db()
        print("\n[OK] 迁移完成！请重新启动服务")
    else:
        print("\n提示: 使用 --delete 参数可自动删除损坏的数据库")
        print("示例: python migrate_chromadb.py --delete")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
