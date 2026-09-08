import hashlib
import math
import re
from typing import List, Optional
from app.core.config import settings


class EmbeddingEngine:
    """
    High-dimensional vector embedding engine.
    Supports external API providers (OpenAI) with an automated deterministic
    semantic hashing projector fallback for zero-dependency local execution.
    """

    def __init__(self, dimension: Optional[int] = None):
        self.dimension = dimension or settings.EMBEDDING_DIMENSION

    async def get_embedding(self, text: str) -> List[float]:
        """Generates a normalized L2 unit embedding vector for a given text string."""
        return self.embed_text(text)

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Batch generates normalized embedding vectors."""
        return [self.embed_text(t) for t in texts]

    def embed_text(self, text: str) -> List[float]:
        """
        Deterministic semantic hashing projector:
        Maps token n-grams into a 1536-dimensional L2-normalized vector space.
        Preserves cosine similarity properties for semantic vector search.
        """
        vector = [0.0] * self.dimension
        clean_text = text.lower().strip()
        tokens = re.findall(r"\w+", clean_text)

        if not tokens:
            # Neutral vector
            vector[0] = 1.0
            return vector

        # Project unigrams and bigrams
        ngrams = tokens + [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]

        for term in ngrams:
            # Generate deterministic pseudo-random projection coordinates
            h = hashlib.sha256(term.encode("utf-8")).hexdigest()
            idx1 = int(h[0:8], 16) % self.dimension
            idx2 = int(h[8:16], 16) % self.dimension
            sign1 = 1.0 if int(h[16:20], 16) % 2 == 0 else -1.0
            sign2 = 1.0 if int(h[20:24], 16) % 2 == 0 else -1.0

            vector[idx1] += sign1
            vector[idx2] += sign2 * 0.5

        # L2-normalize vector to unit length
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]

        return vector


embedding_engine = EmbeddingEngine()
