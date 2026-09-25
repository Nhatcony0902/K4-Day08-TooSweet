"""Tiny persistent cosine vector store used when ChromaDB is unavailable."""

import json
import math
from pathlib import Path


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


class SimplePersistentCollection:
    def __init__(self, directory: Path, name: str) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / f"{name}.json"

    def _load(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, records: dict[str, dict]) -> None:
        self.path.write_text(
            json.dumps(records, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )

    def count(self) -> int:
        return len(self._load())

    def get(self) -> dict:
        records = self._load()
        return {"ids": list(records)}

    def delete(self, *, ids) -> None:
        records = self._load()
        for item_id in ids:
            records.pop(item_id, None)
        self._save(records)

    def upsert(self, *, ids, documents, embeddings, metadatas) -> None:
        records = self._load()
        for item_id, document, embedding, metadata in zip(ids, documents, embeddings, metadatas):
            records[item_id] = {
                "document": document,
                "embedding": embedding,
                "metadata": metadata,
            }
        self._save(records)

    def query(self, *, query_embeddings, n_results, include=None) -> dict:
        records = self._load()
        query = query_embeddings[0]
        ranked = sorted(
            records.items(),
            key=lambda pair: (-_cosine(query, pair[1]["embedding"]), pair[0]),
        )[:n_results]
        return {
            "ids": [[item_id for item_id, _ in ranked]],
            "documents": [[record["document"] for _, record in ranked]],
            "metadatas": [[record["metadata"] for _, record in ranked]],
            "distances": [[1.0 - _cosine(query, record["embedding"]) for _, record in ranked]],
        }
