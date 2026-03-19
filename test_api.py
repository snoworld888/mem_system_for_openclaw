#!/usr/bin/env python3
"""
记忆服务测试脚本 - 无需 Swagger UI
直接测试所有 API 端点
"""

import sys
import requests
import json
import time

# 配置
BASE_URL = "http://127.0.0.1:9000"
SESSION_ID = "test_user_001"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def test_health():
    """测试健康检查"""
    print_section("1️⃣ 健康检查")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"状态码: {resp.status_code}")
        print(f"响应: {json.dumps(resp.json(), ensure_ascii=False, indent=2)}")
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_add_profile():
    """添加用户档案"""
    print_section("2️⃣ 添加用户档案")
    try:
        data = {
            "session_id": SESSION_ID,
            "content": "姓名：张三\n职位：Python工程师\n技能：异步编程、数据分析"
        }
        resp = requests.post(f"{BASE_URL}/memory/profile", json=data, timeout=5)
        print(f"状态码: {resp.status_code}")
        print(f"响应: {json.dumps(resp.json(), ensure_ascii=False, indent=2)}")
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_add_rule():
    """添加规则"""
    print_section("3️⃣ 添加行为规则")
    try:
        data = {
            "session_id": SESSION_ID,
            "content": "回答技术问题时必须提供代码示例",
            "importance": "high"
        }
        resp = requests.post(f"{BASE_URL}/memory/rule", json=data, timeout=5)
        print(f"状态码: {resp.status_code}")
        print(f"响应: {json.dumps(resp.json(), ensure_ascii=False, indent=2)}")
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_query_memory():
    """查询记忆上下文"""
    print_section("4️⃣ 查询记忆上下文 ⭐")
    try:
        data = {
            "session_id": SESSION_ID,
            "user_query": "我想学习 Python 异步编程",
            "max_tokens": 2000
        }
        resp = requests.post(f"{BASE_URL}/memory/query", json=data, timeout=5)
        print(f"状态码: {resp.status_code}")
        result = resp.json()
        print(f"\n【返回数据】")
        print(f"  规则: {result.get('rules', '(无)')[:80]}")
        print(f"  档案: {result.get('profile', '(无)')[:80]}")
        print(f"  短期记忆: {result.get('short_term', '(无)')[:80]}")
        print(f"  长期记忆: {result.get('long_term_relevant', '(无)')[:80]}")
        print(f"  总 tokens: {result.get('total_tokens', 0)}")
        print(f"  消息数: {len(result.get('messages', []))}")
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_add_turn():
    """记录对话"""
    print_section("5️⃣ 记录对话轮次")
    try:
        data = {
            "session_id": SESSION_ID,
            "user_message": "我想学习 Python 异步编程",
            "assistant_message": "Python 异步编程使用 async/await 和 asyncio 库。这是一个简单示例：\n\nimport asyncio\n\nasync def hello():\n    print('Hello')\n    await asyncio.sleep(1)\n    print('World')\n\nasyncio.run(hello())",
            "important": False
        }
        resp = requests.post(f"{BASE_URL}/memory/turn", json=data, timeout=5)
        print(f"状态码: {resp.status_code}")
        print(f"响应: {json.dumps(resp.json(), ensure_ascii=False, indent=2)}")
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_save_memory():
    """保存重要信息"""
    print_section("6️⃣ 保存到长期记忆")
    try:
        data = {
            "session_id": SESSION_ID,
            "content": "用户对异步编程感兴趣，需要详细代码示例",
            "memory_type": "long_term",
            "importance": "high"
        }
        resp = requests.post(f"{BASE_URL}/memory/save", json=data, timeout=5)
        print(f"状态码: {resp.status_code}")
        print(f"响应: {json.dumps(resp.json(), ensure_ascii=False, indent=2)}")
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_search():
    """搜索记忆"""
    print_section("7️⃣ 搜索记忆")
    try:
        data = {
            "session_id": SESSION_ID,
            "query": "异步编程",
            "memory_type": "long_term",
            "top_k": 3
        }
        resp = requests.post(f"{BASE_URL}/memory/search", json=data, timeout=5)
        print(f"状态码: {resp.status_code}")
        result = resp.json()
        print(f"搜索结果: {result.get('results', [])}")
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_stats():
    """查看统计"""
    print_section("8️⃣ 查看统计信息")
    try:
        resp = requests.get(f"{BASE_URL}/memory/stats?session_id={SESSION_ID}", timeout=5)
        print(f"状态码: {resp.status_code}")
        print(f"响应: {json.dumps(resp.json(), ensure_ascii=False, indent=2)}")
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("  记忆服务 API 测试")
    print("="*60)
    print(f"测试地址: {BASE_URL}")
    print(f"会话ID: {SESSION_ID}")
    
    # 检查连接
    print(f"\n正在连接到服务... ", end="", flush=True)
    for i in range(3):
        try:
            resp = requests.get(f"{BASE_URL}/health", timeout=2)
            print(f"✅ 连接成功！\n")
            break
        except Exception as e:
            if i < 2:
                print(".", end="", flush=True)
                time.sleep(1)
            else:
                print(f"\n❌ 无法连接到 {BASE_URL}")
                print("   请确保服务已启动:")
                print("   cd c:\\07code\\mem_server")
                print("   python main.py --host 127.0.0.1 --port 9000")
                return 1
    
    # 运行测试
    tests = [
        test_health,
        test_add_profile,
        test_add_rule,
        test_query_memory,
        test_add_turn,
        test_save_memory,
        test_search,
        test_stats,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except KeyboardInterrupt:
            print("\n\n[已中止]")
            break
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            results.append(False)
    
    # 总结
    print_section("📊 测试总结")
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("\n✅ 所有测试通过！记忆服务运行正常。\n")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
