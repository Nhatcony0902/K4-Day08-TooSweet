"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""

import re
import math
import unicodedata

from .task4_chunking_indexing import chunk_documents, load_documents


CORPUS: list[dict] = []


def _tokenize(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    return re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)


def _get_corpus() -> list[dict]:
    return CORPUS if CORPUS else chunk_documents(load_documents())


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    if not corpus:
        return None
    return _BM25([_tokenize(item["content"]) for item in corpus])


class _BM25:
    def __init__(self, documents: list[list[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.average_length = sum(map(len, documents)) / len(documents)
        self.document_frequency: dict[str, int] = {}
        for document in documents:
            for token in set(document):
                self.document_frequency[token] = self.document_frequency.get(token, 0) + 1

    def get_scores(self, query: list[str]) -> list[float]:
        size = len(self.documents)
        scores = []
        for document in self.documents:
            frequencies: dict[str, int] = {}
            for token in document:
                frequencies[token] = frequencies.get(token, 0) + 1
            score = 0.0
            for token in query:
                frequency = frequencies.get(token, 0)
                if not frequency:
                    continue
                document_frequency = self.document_frequency.get(token, 0)
                inverse_frequency = math.log(1 + (size - document_frequency + 0.5) / (document_frequency + 0.5))
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * len(document) / max(self.average_length, 1)
                )
                score += inverse_frequency * frequency * (self.k1 + 1) / denominator
            scores.append(score)
        return scores


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    if top_k <= 0 or not query.strip():
        return []
    corpus = _get_corpus()
    bm25 = build_bm25_index(corpus)
    if bm25 is None:
        return []
    scores = bm25.get_scores(_tokenize(query))
    indices = sorted(range(len(corpus)), key=lambda index: (-float(scores[index]), corpus[index]["id"]))
    results = []
    seen = set()
    for index in indices:
        score = float(scores[index])
        item = corpus[index]
        if score <= 0 or item["id"] in seen:
            continue
        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": score,
            "metadata": item["metadata"],
            "retrieval_method": "bm25",
        })
        seen.add(item["id"])
        if len(results) >= top_k:
            break
    return results


if __name__ == "__main__":
    for result in lexical_search("test query", top_k=3):
        print(result)
