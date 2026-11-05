"""
TF-IDF embedder over identifier sub-tokens.

A lexical-semantic proxy: vocabulary from sub_tokens, smoothed idf,
L2-normalised tf-idf, cosine as a dot product. Numpy only; no network.
"""

from __future__ import annotations

from collections import Counter
from typing import Sequence

import numpy as np

from .model import sub_tokens


class TfidfEmbedder:
    def __init__(self, corpus: Sequence[str]) -> None:
        docs = [sub_tokens(text) for text in corpus]
        n = len(docs)
        df: dict[str, int] = {}
        vocab: set[str] = set()
        for tokens in docs:
            vocab.update(tokens)
            for t in set(tokens):
                df[t] = df.get(t, 0) + 1
        self._index = {t: i for i, t in enumerate(sorted(vocab))}
        self._idf = np.zeros(len(self._index), dtype=float)
        for t, i in self._index.items():
            self._idf[i] = np.log((1 + n) / (1 + df[t])) + 1

    def vector(self, text: str) -> np.ndarray:
        dim = len(self._index)
        vec = np.zeros(dim, dtype=float)
        if dim == 0:
            return vec
        counts = Counter(t for t in sub_tokens(text) if t in self._index)
        for t, c in counts.items():
            vec[self._index[t]] = c * self._idf[self._index[t]]
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def similarity(self, a: str, b: str) -> float:
        va, vb = self.vector(a), self.vector(b)
        if not np.any(va) or not np.any(vb):
            return 0.0
        return float(np.dot(va, vb))
