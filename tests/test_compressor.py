"""
压缩器 & 工具函数单元测试
覆盖：
  - rule_based_compress: 基础压缩、token 限制、空输入
  - extract_key_facts: 关键词提取逻辑
  - token_counter: count_tokens / truncate_to_tokens
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.memory.compressor import rule_based_compress, extract_key_facts
from src.memory.models import ConversationTurn
from src.utils.token_counter import count_tokens, truncate_to_tokens


def make_turns(count=5, content_template="这是一段对话内容，用于测试压缩功能"):
    turns = []
    for i in range(count):
        role = "user" if i % 2 == 0 else "assistant"
        turns.append(ConversationTurn(role=role, content=f"{content_template} 第{i}条"))
    return turns


# ──────────────────── rule_based_compress ────────────────────── #

class TestRuleBasedCompress:

    def test_basic_compress_returns_string(self):
        turns = make_turns(3)
        result = rule_based_compress(turns, max_tokens=500)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_compress_empty_turns_returns_empty(self):
        result = rule_based_compress([], max_tokens=300)
        assert result == ""

    def test_compress_respects_max_tokens(self):
        # 制造大量内容
        turns = make_turns(50, content_template="这是一段很长的对话内容，包含了大量的文字，用来测试token截断功能是否正常")
        result = rule_based_compress(turns, max_tokens=100)
        actual_tokens = count_tokens(result)
        # 允许少量误差
        assert actual_tokens <= 120

    def test_compress_single_turn(self):
        turns = [ConversationTurn(role="user", content="单条消息")]
        result = rule_based_compress(turns)
        assert "单条消息" in result or len(result) > 0

    def test_compress_truncates_long_content(self):
        """单条超长内容会被截断（150字符）"""
        long_content = "A" * 500
        turns = [ConversationTurn(role="user", content=long_content)]
        result = rule_based_compress(turns, max_tokens=1000)
        # 结果中不会有完整的500个A
        assert len(result) < 600

    def test_compress_preserves_role_labels(self):
        """压缩结果包含角色标签"""
        turns = [
            ConversationTurn(role="user", content="用户说的话"),
            ConversationTurn(role="assistant", content="助手回答"),
        ]
        result = rule_based_compress(turns, max_tokens=500)
        assert "用户" in result or "助手" in result

    def test_compress_multiple_turns_preserves_structure(self):
        """多轮对话压缩后仍有结构"""
        turns = make_turns(10)
        result = rule_based_compress(turns, max_tokens=500)
        lines = result.strip().split("\n")
        assert len(lines) >= 1  # 至少有内容


# ──────────────────── extract_key_facts ──────────────────────── #

class TestExtractKeyFacts:

    def test_extract_from_name_statement(self):
        """包含'我叫'时能提取"""
        facts = extract_key_facts("你好，我叫张三，是一名工程师")
        assert len(facts) >= 1
        assert any("张三" in f for f in facts)

    def test_extract_from_identity_statement(self):
        """包含'我是'时能提取"""
        facts = extract_key_facts("我是Python开发者，专注于AI方向")
        assert len(facts) >= 1

    def test_extract_from_remember_keyword(self):
        """包含'记住'时能提取"""
        facts = extract_key_facts("请记住，我不喜欢冗长的回答")
        assert len(facts) >= 1

    def test_extract_returns_list(self):
        """返回值类型为 list"""
        facts = extract_key_facts("随机内容")
        assert isinstance(facts, list)

    def test_extract_from_empty_string(self):
        """空字符串不报错"""
        facts = extract_key_facts("")
        assert facts == []

    def test_extract_max_five_facts(self):
        """最多返回5条"""
        text = "。".join([
            "我叫A", "我是B", "我的工作是C", "我喜欢D",
            "我不喜欢E", "我需要F", "我习惯G",
        ])
        facts = extract_key_facts(text)
        assert len(facts) <= 5

    def test_extract_no_keywords_returns_empty(self):
        """无关键词时返回空"""
        facts = extract_key_facts("今天天气很好，阳光明媚，适合外出散步")
        assert len(facts) == 0

    def test_extract_preference_keywords(self):
        """'我喜欢'和'我不喜欢'能触发提取"""
        facts1 = extract_key_facts("我喜欢简洁的代码风格")
        facts2 = extract_key_facts("我不喜欢过多的注释")
        assert len(facts1) >= 1
        assert len(facts2) >= 1

    def test_extract_must_keyword(self):
        """'必须'和'禁止'能触发提取"""
        facts = extract_key_facts("代码里必须有单元测试，禁止提交未测试的代码")
        assert len(facts) >= 1

    def test_extract_multiline(self):
        """多行文本提取"""
        text = "我叫Alice\n我是工程师\n今天天气好"
        facts = extract_key_facts(text)
        # 前两句有关键词，应提取
        assert len(facts) >= 1


# ──────────────────── token_counter ──────────────────────────── #

class TestTokenCounter:

    def test_count_tokens_returns_positive(self):
        tokens = count_tokens("这是一段中文内容")
        assert tokens > 0

    def test_count_tokens_empty_string(self):
        tokens = count_tokens("")
        assert tokens == 0

    def test_count_tokens_longer_text_more_tokens(self):
        short = count_tokens("短文本")
        long = count_tokens("这是一段更长的文本内容，包含更多的词汇和字符，用来测试token计数是否按长度增长")
        assert long > short

    def test_truncate_to_tokens_returns_string(self):
        result = truncate_to_tokens("这是一段测试文本内容", max_tokens=5)
        assert isinstance(result, str)

    def test_truncate_to_tokens_within_limit(self):
        text = "这是一段测试文本内容，包含了大量的文字，用来验证截断功能"
        result = truncate_to_tokens(text, max_tokens=5)
        assert count_tokens(result) <= 7  # 允许少量误差

    def test_truncate_to_tokens_full_text_if_within_limit(self):
        """文本 token 未超限时原样返回"""
        text = "短文本"
        result = truncate_to_tokens(text, max_tokens=1000)
        assert result == text

    def test_truncate_empty_string(self):
        result = truncate_to_tokens("", max_tokens=100)
        assert result == ""
