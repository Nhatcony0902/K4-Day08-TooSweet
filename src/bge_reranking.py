"""
Bonus — Rerank bằng BGE-M3 sau RRF.

RRF chỉ gộp thứ hạng. Bước này lấy top candidates của RRF rồi chấm lại bằng
cosine giữa embedding BGE-M3 (đa ngôn ngữ, hỗ trợ tiếng Việt) của query và của
từng chunk, thay cho hashing embedding dùng ở dense retrieval.
Bật trong pipeline bằng `RERANKER=bge` trong .env; mặc định `none`.
"""

import os
import warnings
from functools import lru_cache

from .config import load_dotenv


load_dotenv()

RERANKER = os.getenv("RERANKER", "none").lower()
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-m3")


@lru_cache(maxsize=1)
def _load_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(RERANKER_MODEL)


def rerank_bge(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """Chấm lại candidates bằng cosine BGE-M3; score nằm trong khoảng -1..1."""
    if top_k <= 0 or not candidates or not query.strip():
        return []
    try:
        model = _load_model()
    except ImportError:
        warnings.warn("sentence-transformers chưa được cài; bỏ qua BGE reranking.")
        return candidates[:top_k]
    vectors = model.encode(
        [query] + [item["content"] for item in candidates], normalize_embeddings=True
    )
    query_vector, chunk_vectors = vectors[0], vectors[1:]
    scored = [
        {**item, "score": float(query_vector @ chunk_vector)}
        for item, chunk_vector in zip(candidates, chunk_vectors)
    ]
    scored.sort(key=lambda item: -item["score"])
    return scored[:top_k]


if __name__ == "__main__":
    from .task9_retrieval_pipeline import retrieve

    question = "Thời gian nghỉ học dài hạn tối đa là bao nhiêu học kỳ?"
    for item in rerank_bge(question, retrieve(question, top_k=10), top_k=3):
        print(round(item["score"], 4), item["id"])
