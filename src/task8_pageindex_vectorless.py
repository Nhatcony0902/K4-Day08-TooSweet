"""
Task 8 — PageIndex vectorless fallback.

Hướng dẫn:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu ở định dạng PageIndex hỗ trợ.
    3. Cache document IDs để không upload lại.
    4. Parse kết quả thành SearchResult có method pageindex.

PageIndex là dịch vụ ngoài: cần timeout và xử lý lỗi để pipeline không crash.
"""

import os
import json
from pathlib import Path

from .config import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
LANDING_LEGAL_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"
CACHE_PATH = Path(__file__).parent.parent / "pageindex_doc_ids.json"
API_BASE = "https://api.pageindex.ai"


def _headers() -> dict[str, str]:
    if not PAGEINDEX_API_KEY:
        raise RuntimeError("PAGEINDEX_API_KEY is not configured")
    return {"api_key": PAGEINDEX_API_KEY}


def _load_cache() -> dict[str, dict]:
    if not CACHE_PATH.exists():
        return {}
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    import requests

    cache = _load_cache()
    for path in sorted(LANDING_LEGAL_DIR.glob("*.pdf")):
        stat = path.stat()
        cached = cache.get(path.name)
        if cached and cached.get("size") == stat.st_size:
            continue
        with path.open("rb") as file_handle:
            response = requests.post(
                f"{API_BASE}/doc/",
                headers=_headers(),
                files={"file": (path.name, file_handle, "application/pdf")},
                timeout=120,
            )
        response.raise_for_status()
        payload = response.json()
        doc_id = payload.get("doc_id") or payload.get("id")
        if not doc_id:
            raise ValueError(f"PageIndex response has no document ID: {payload}")
        cache[path.name] = {"doc_id": doc_id, "size": stat.st_size}
        CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Uploaded: {path.name} -> {doc_id}")


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    if top_k <= 0 or not query.strip() or not PAGEINDEX_API_KEY:
        return []

    import requests

    cache = _load_cache()
    doc_ids = [item["doc_id"] for item in cache.values() if item.get("doc_id")]
    if not doc_ids:
        return []
    response = requests.post(
        f"{API_BASE}/chat/completions",
        headers={**_headers(), "Content-Type": "application/json"},
        json={
            "messages": [{"role": "user", "content": query}],
            "doc_id": doc_ids,
            "temperature": 0,
            "enable_citations": True,
            "stream": False,
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    citations = payload.get("citations", [])
    results = []
    seen = set()
    reverse_cache = {item["doc_id"]: name for name, item in cache.items()}
    for rank, citation in enumerate(citations, 1):
        doc_id = citation.get("doc_id") or citation.get("document_id")
        block_id = citation.get("block_id") or citation.get("block")
        page = citation.get("page") or citation.get("page_index")
        identity = f"{doc_id}:{block_id or page or rank}"
        if identity in seen:
            continue
        content = citation.get("text") or citation.get("content") or citation.get("markdown")
        if not content and doc_id and block_id:
            block_response = requests.get(
                f"{API_BASE}/doc/{doc_id}/block/{block_id}/",
                headers=_headers(),
                timeout=30,
            )
            block_response.raise_for_status()
            block = block_response.json()
            content = block.get("text") or block.get("content")
        if not content:
            continue
        source = reverse_cache.get(doc_id, citation.get("document_name", "PageIndex"))
        results.append({
            "id": identity,
            "content": str(content),
            "score": 1.0 / rank,
            "metadata": {
                "source": source,
                "title": citation.get("title") or source,
                "doc_type": "legal",
                "url": None,
                "chunk_index": max(int(page or rank) - 1, 0),
            },
            "retrieval_method": "pageindex",
        })
        seen.add(identity)
        if len(results) >= top_k:
            break
    return results


if __name__ == "__main__":
    upload_documents()
