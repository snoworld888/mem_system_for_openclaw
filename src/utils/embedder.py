"""
向量嵌入管理器
- 优先使用本地sentence-transformers模型
- 若模型不可用，自动降级为TF-IDF关键词向量（完全离线）
- 接口统一，上层无感知
"""
from __future__ import annotations
import hashlib
import math
import re
from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.config import Settings


class TFIDFEmbedder:
    """
    基于TF-IDF的轻量嵌入器（完全离线，无需模型下载）
    适合中文文本的关键词匹配，速度极快
    """

    DIM = 512  # 伪向量维度（哈希桶数量）

    def __init__(self):
        self._corpus_tf: dict[str, Counter] = {}  # doc_id -> term freqs
        self._df: Counter = Counter()              # term -> doc count
        self._doc_count: int = 0

    def _tokenize(self, text: str) -> list[str]:
        """简单分词：中文按字/双字gram，英文按单词"""
        text = text.lower().strip()
        tokens = []
        # 英文单词
        eng = re.findall(r"[a-z0-9]+", text)
        tokens.extend(eng)
        # 中文字符 unigram + bigram
        chinese = re.findall(r"[\u4e00-\u9fff]", text)
        tokens.extend(chinese)
        for i in range(len(chinese) - 1):
            tokens.append(chinese[i] + chinese[i + 1])
        return tokens

    def _hash_term(self, term: str) -> int:
        """将词映射到桶编号"""
        return int(hashlib.md5(term.encode()).hexdigest(), 16) % self.DIM

    def encode(self, texts: list[str], **kwargs) -> list[list[float]]:
        """
        生成TF-IDF向量（批量）
        使用hash trick，固定维度，无需词典
        """
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
                # TF
                tf_val = cnt / total
                # 简化IDF（用逆频率估算，无需语料统计）
                idf = 1.0 + math.log(1 + 1 / (1 + self._df.get(term, 0)))
                bucket = self._hash_term(term)
                vec[bucket] += tf_val * idf
            # L2归一化
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vec = [v / norm for v in vec]
            result.append(vec)
        return result

    def update_idf(self, texts: list[str]):
        """用语料更新IDF统计（可选，提升准确性）"""
        for text in texts:
            tokens = set(self._tokenize(text))
            for t in tokens:
                self._df[t] += 1
            self._doc_count += 1


class EmbeddingManager:
    """统一嵌入接口，自动选择可用的嵌入器"""

    def __init__(self, settings: "Settings"):
        self.settings = settings
        self._model = None
        self._fallback = TFIDFEmbedder()
        self._use_fallback = False

    def _try_load_model(self):
        """尝试加载sentence-transformers，失败则用TF-IDF"""
        if self._use_fallback:
            return
        try:
            from sentence_transformers import SentenceTransformer
            import os
            model_path = self.settings.embedding_model
            # 检查是否是本地路径
            if not os.path.exists(model_path):
                # 尝试从HuggingFace cache加载
                cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
                # 转换为cache路径格式
                model_cache_name = "models--" + model_path.replace("/", "--")
                cache_path = os.path.join(cache_dir, model_cache_name)
                if not os.path.exists(cache_path):
                    raise FileNotFoundError(f"模型不在本地: {model_path}")
            self._model = SentenceTransformer(
                model_path,
                device=self.settings.embedding_device,
                local_files_only=True,  # 禁止网络下载
            )
            print(f"[EmbeddingManager] 使用本地模型: {model_path}")
        except Exception as e:
            print(f"[EmbeddingManager] 模型加载失败，降级为TF-IDF: {e}")
            self._use_fallback = True

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not self._use_fallback and self._model is None:
            self._try_load_model()

        if self._use_fallback or self._model is None:
            return self._fallback.encode(texts)

        return self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()

    @property
    def using_fallback(self) -> bool:
        return self._use_fallback

    @property
    def dim(self) -> int:
        if self._use_fallback or self._model is None:
            return TFIDFEmbedder.DIM
        return self._model.get_sentence_embedding_dimension()
