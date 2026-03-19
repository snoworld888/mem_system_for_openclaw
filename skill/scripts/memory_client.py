"""
Memory Service HTTP Client for OpenClaw

Usage:
    client = MemoryClient("http://127.0.0.1:7000")
    ctx = client.query_memory("user_123", "用户的问题")
    client.add_turn("user_123", "用户消息", "AI回应")
"""

import httpx
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class ContextResponse:
    """查询返回的上下文"""
    session_id: str
    rules: str
    profile: str
    short_term: str
    long_term_relevant: str
    total_tokens: int
    messages: List[Dict[str, str]]


class MemoryClient:
    """记忆服务客户端"""

    def __init__(self, base_url: str = "http://127.0.0.1:7000", timeout: float = 30.0):
        """
        初始化客户端
        
        Args:
            base_url: 记忆服务地址
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.client = httpx.Client(timeout=timeout)

    def query_memory(
        self,
        session_id: str,
        user_query: str,
        max_tokens: int = 2000,
    ) -> ContextResponse:
        """
        查询记忆上下文（最常用）
        
        Args:
            session_id: 用户会话ID
            user_query: 用户当前查询/问题
            max_tokens: 返回上下文的最大 token 数
            
        Returns:
            ContextResponse 对象，包含可直接用于 LLM 的 messages
        """
        response = self.client.post(
            f"{self.base_url}/memory/query",
            json={
                "session_id": session_id,
                "user_query": user_query,
                "max_tokens": max_tokens,
            }
        )
        response.raise_for_status()
        data = response.json()
        
        return ContextResponse(
            session_id=data["session_id"],
            rules=data["rules"],
            profile=data["profile"],
            short_term=data["short_term"],
            long_term_relevant=data["long_term_relevant"],
            total_tokens=data["total_tokens"],
            messages=data["messages"],
        )

    def add_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        important: bool = False,
    ) -> Dict[str, Any]:
        """
        记录对话轮次
        
        Args:
            session_id: 用户会话ID
            user_message: 用户的消息
            assistant_message: AI的回应
            important: 是否为重要对话（会影响压缩优先级）
            
        Returns:
            API 响应字典
        """
        response = self.client.post(
            f"{self.base_url}/memory/turn",
            json={
                "session_id": session_id,
                "user_message": user_message,
                "assistant_message": assistant_message,
                "important": important,
            }
        )
        response.raise_for_status()
        return response.json()

    def save_memory(
        self,
        session_id: str,
        content: str,
        memory_type: str = "long_term",
        importance: str = "medium",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        保存内容到记忆库
        
        Args:
            session_id: 用户会话ID
            content: 要保存的内容
            memory_type: 记忆类型 (long_term | profile | rule)
            importance: 重要程度 (high | medium | low)
            metadata: 额外元数据
            
        Returns:
            API 响应字典
        """
        response = self.client.post(
            f"{self.base_url}/memory/save",
            json={
                "session_id": session_id,
                "content": content,
                "memory_type": memory_type,
                "importance": importance,
                "metadata": metadata or {},
            }
        )
        response.raise_for_status()
        return response.json()

    def search(
        self,
        session_id: str,
        query: str,
        memory_type: str = "long_term",
        top_k: int = 3,
        threshold: float = 0.3,
    ) -> Dict[str, Any]:
        """
        语义搜索记忆
        
        Args:
            session_id: 用户会话ID
            query: 搜索查询
            memory_type: 搜索范围 (long_term | profile | rule)
            top_k: 返回前K个结果
            threshold: 相似度阈值 (0-1)
            
        Returns:
            搜索结果
        """
        response = self.client.post(
            f"{self.base_url}/memory/search",
            json={
                "session_id": session_id,
                "query": query,
                "memory_type": memory_type,
                "top_k": top_k,
                "threshold": threshold,
            }
        )
        response.raise_for_status()
        return response.json()

    def add_profile(
        self,
        session_id: str,
        content: str,
    ) -> Dict[str, Any]:
        """
        添加或更新用户档案
        
        Args:
            session_id: 用户会话ID
            content: 用户档案内容（例如："姓名：张三\n职位：工程师"）
            
        Returns:
            API 响应
        """
        response = self.client.post(
            f"{self.base_url}/memory/profile",
            json={
                "session_id": session_id,
                "content": content,
                "action": "add",
            }
        )
        response.raise_for_status()
        return response.json()

    def add_rule(
        self,
        session_id: str,
        content: str,
        importance: str = "high",
    ) -> Dict[str, Any]:
        """
        添加行为规则
        
        Args:
            session_id: 用户会话ID
            content: 规则内容
            importance: 重要程度 (high | medium | low)
            
        Returns:
            API 响应
        """
        response = self.client.post(
            f"{self.base_url}/memory/rule",
            json={
                "session_id": session_id,
                "content": content,
                "importance": importance,
            }
        )
        response.raise_for_status()
        return response.json()

    def get_stats(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话统计信息
        
        Args:
            session_id: 用户会话ID
            
        Returns:
            统计信息
        """
        response = self.client.get(
            f"{self.base_url}/memory/stats",
            params={"session_id": session_id}
        )
        response.raise_for_status()
        return response.json()

    def clear(self, session_id: str) -> Dict[str, Any]:
        """
        清空会话的所有记忆
        
        Args:
            session_id: 用户会话ID
            
        Returns:
            API 响应
        """
        response = self.client.post(
            f"{self.base_url}/memory/clear",
            json={"session_id": session_id}
        )
        response.raise_for_status()
        return response.json()

    def health(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            服务状态
        """
        response = self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    def close(self):
        """关闭客户端连接"""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 使用示例
if __name__ == "__main__":
    # 初始化客户端
    with MemoryClient("http://127.0.0.1:7000") as client:
        session_id = "user_demo_001"
        
        # 1. 添加用户档案
        print("[1] 添加用户档案...")
        client.add_profile(
            session_id=session_id,
            content="姓名：张三\n职位：Python工程师\n擅长领域：后端、数据分析"
        )
        
        # 2. 添加规则
        print("[2] 添加行为规则...")
        client.add_rule(
            session_id=session_id,
            content="回答技术问题时必须提供代码示例",
            importance="high"
        )
        client.add_rule(
            session_id=session_id,
            content="尊重用户隐私，不要要求敏感信息",
            importance="high"
        )
        
        # 3. 首次查询
        print("[3] 首次查询上下文...")
        ctx = client.query_memory(
            session_id=session_id,
            user_query="我想学习 Python 异步编程"
        )
        print(f"    规则：{ctx.rules[:50]}...")
        print(f"    档案：{ctx.profile[:50]}...")
        print(f"    总 tokens：{ctx.total_tokens}")
        
        # 4. 记录对话
        print("[4] 记录对话...")
        client.add_turn(
            session_id=session_id,
            user_message="我想学习 Python 异步编程",
            assistant_message="Python 异步编程使用 async/await 和 asyncio 库。这是一个异步编程的基础示例：\n\nimport asyncio\n\nasync def hello():\n    print('Hello')\n    await asyncio.sleep(1)\n    print('World')\n\nasyncio.run(hello())",
        )
        
        # 5. 保存重要信息
        print("[5] 保存重要信息...")
        client.save_memory(
            session_id=session_id,
            content="用户对异步编程感兴趣，需要提供详细代码示例",
            memory_type="long_term",
            importance="high"
        )
        
        # 6. 再次查询（会包含新记忆）
        print("[6] 再次查询，验证记忆更新...")
        ctx = client.query_memory(
            session_id=session_id,
            user_query="给我一个 asyncio 的例子"
        )
        print(f"    长期记忆：{ctx.long_term_relevant[:80]}...")
        print(f"    短期对话轮数：{ctx.short_term.count('User:')}")
        
        # 7. 查看统计
        print("[7] 查看会话统计...")
        stats = client.get_stats(session_id)
        print(f"    {json.dumps(stats, indent=2, ensure_ascii=False)}")
        
        print("\n✅ 演示完成！")
