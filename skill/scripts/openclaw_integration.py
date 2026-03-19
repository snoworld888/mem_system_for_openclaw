#!/usr/bin/env python3
"""
OpenClaw Memory Integration Script

这个脚本提供了在 OpenClaw 中使用记忆服务的快速集成方式。
可以作为 OpenClaw 的自定义脚本或插件直接调用。

Usage:
    python openclaw_integration.py --query "user_id_123" "用户的问题"
    python openclaw_integration.py --save "user_id_123" "long_term" "重要信息"
"""

import argparse
import json
import sys
from pathlib import Path

# 添加父目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from memory_client import MemoryClient, ContextResponse


def format_context_for_openclaw(ctx: ContextResponse) -> str:
    """
    格式化上下文为 OpenClaw 可读的形式
    """
    output = {
        "status": "success",
        "session_id": ctx.session_id,
        "context": {
            "rules": ctx.rules or "（无规则设定）",
            "profile": ctx.profile or "（无用户档案）",
            "short_term": ctx.short_term or "（无最近对话）",
            "long_term": ctx.long_term_relevant or "（无相关历史）",
        },
        "tokens": {
            "total": ctx.total_tokens,
            "max_allowed": 2000,
            "usage_ratio": f"{ctx.total_tokens / 2000 * 100:.1f}%"
        },
        "messages": ctx.messages
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


def cmd_query(args):
    """查询上下文"""
    try:
        client = MemoryClient(args.server)
        ctx = client.query_memory(
            session_id=args.session_id,
            user_query=args.query,
            max_tokens=args.max_tokens
        )
        print(format_context_for_openclaw(ctx))
        return 0
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False, indent=2))
        return 1


def cmd_turn(args):
    """记录对话"""
    try:
        client = MemoryClient(args.server)
        result = client.add_turn(
            session_id=args.session_id,
            user_message=args.user_message,
            assistant_message=args.assistant_message,
            important=args.important
        )
        print(json.dumps({
            "status": "success",
            "message": "对话已记录",
            "data": result
        }, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False, indent=2))
        return 1


def cmd_save(args):
    """保存到记忆"""
    try:
        client = MemoryClient(args.server)
        result = client.save_memory(
            session_id=args.session_id,
            content=args.content,
            memory_type=args.memory_type,
            importance=args.importance
        )
        print(json.dumps({
            "status": "success",
            "message": f"已保存到 {args.memory_type}",
            "data": result
        }, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False, indent=2))
        return 1


def cmd_search(args):
    """搜索记忆"""
    try:
        client = MemoryClient(args.server)
        result = client.search(
            session_id=args.session_id,
            query=args.query,
            memory_type=args.memory_type,
            top_k=args.top_k,
            threshold=args.threshold
        )
        print(json.dumps({
            "status": "success",
            "data": result
        }, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False, indent=2))
        return 1


def cmd_profile(args):
    """管理用户档案"""
    try:
        client = MemoryClient(args.server)
        result = client.add_profile(
            session_id=args.session_id,
            content=args.content
        )
        print(json.dumps({
            "status": "success",
            "message": "用户档案已更新",
            "data": result
        }, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False, indent=2))
        return 1


def cmd_rule(args):
    """添加规则"""
    try:
        client = MemoryClient(args.server)
        result = client.add_rule(
            session_id=args.session_id,
            content=args.content,
            importance=args.importance
        )
        print(json.dumps({
            "status": "success",
            "message": "规则已添加",
            "data": result
        }, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False, indent=2))
        return 1


def cmd_stats(args):
    """查看统计"""
    try:
        client = MemoryClient(args.server)
        result = client.get_stats(args.session_id)
        print(json.dumps({
            "status": "success",
            "data": result
        }, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False, indent=2))
        return 1


def cmd_health(args):
    """健康检查"""
    try:
        client = MemoryClient(args.server)
        result = client.health()
        print(json.dumps({
            "status": "success",
            "data": result
        }, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False, indent=2))
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="OpenClaw Memory Service Integration"
    )
    
    parser.add_argument(
        "--server",
        default="http://127.0.0.1:7000",
        help="Memory service base URL (default: http://127.0.0.1:7000)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # query 命令
    query_parser = subparsers.add_parser("query", help="查询记忆上下文")
    query_parser.add_argument("session_id", help="User session ID")
    query_parser.add_argument("query", help="User query")
    query_parser.add_argument("--max-tokens", type=int, default=2000)
    query_parser.set_defaults(func=cmd_query)
    
    # turn 命令
    turn_parser = subparsers.add_parser("turn", help="记录对话轮次")
    turn_parser.add_argument("session_id", help="User session ID")
    turn_parser.add_argument("user_message", help="User message")
    turn_parser.add_argument("assistant_message", help="Assistant message")
    turn_parser.add_argument("--important", action="store_true")
    turn_parser.set_defaults(func=cmd_turn)
    
    # save 命令
    save_parser = subparsers.add_parser("save", help="保存到记忆")
    save_parser.add_argument("session_id", help="User session ID")
    save_parser.add_argument("memory_type", choices=["long_term", "profile", "rule"])
    save_parser.add_argument("content", help="Content to save")
    save_parser.add_argument("--importance", choices=["high", "medium", "low"], default="medium")
    save_parser.set_defaults(func=cmd_save)
    
    # search 命令
    search_parser = subparsers.add_parser("search", help="搜索记忆")
    search_parser.add_argument("session_id", help="User session ID")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--type", dest="memory_type", default="long_term")
    search_parser.add_argument("--top-k", type=int, default=3)
    search_parser.add_argument("--threshold", type=float, default=0.3)
    search_parser.set_defaults(func=cmd_search)
    
    # profile 命令
    profile_parser = subparsers.add_parser("profile", help="管理用户档案")
    profile_parser.add_argument("session_id", help="User session ID")
    profile_parser.add_argument("content", help="Profile content")
    profile_parser.set_defaults(func=cmd_profile)
    
    # rule 命令
    rule_parser = subparsers.add_parser("rule", help="添加规则")
    rule_parser.add_argument("session_id", help="User session ID")
    rule_parser.add_argument("content", help="Rule content")
    rule_parser.add_argument("--importance", choices=["high", "medium", "low"], default="high")
    rule_parser.set_defaults(func=cmd_rule)
    
    # stats 命令
    stats_parser = subparsers.add_parser("stats", help="查看统计")
    stats_parser.add_argument("session_id", help="User session ID")
    stats_parser.set_defaults(func=cmd_stats)
    
    # health 命令
    health_parser = subparsers.add_parser("health", help="健康检查")
    health_parser.set_defaults(func=cmd_health)
    
    args = parser.parse_args()
    
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
