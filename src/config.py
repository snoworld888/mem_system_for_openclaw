"""
应用配置
"""
from __future__ import annotations
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── 服务器 ──────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8765
    debug: bool = False

    # ── 数据存储 ────────────────────────────────────
    data_dir: str = "./data"

    # ── 嵌入模型（本地，无需API）────────────────────
    # 推荐轻量模型，首次使用自动下载
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_device: str = "cpu"  # 或 "cuda"

    # ── LLM（可选，用于高质量摘要压缩）────────────────
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    compress_model: str = "gpt-4o-mini"  # 用最便宜的模型做摘要

    # ── 短期记忆 ────────────────────────────────────
    stm_max_turns: int = 20          # session最多保留轮数
    stm_max_tokens: int = 1500       # 超过则触发压缩
    stm_compress_tokens: int = 300   # 压缩摘要的token限制
    stm_keep_last: int = 6           # 压缩时保留最近N轮

    # ── 长期记忆 ────────────────────────────────────
    ltm_top_k: int = 5               # 默认检索数量
    ltm_threshold: float = 0.25      # 相似度阈值

    # ── 上下文组装 ──────────────────────────────────
    default_max_tokens: int = 2000   # 默认上下文token预算
    auto_extract_facts: bool = True  # 自动从对话中提取关键事实


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        os.makedirs(_settings.data_dir, exist_ok=True)
    return _settings
