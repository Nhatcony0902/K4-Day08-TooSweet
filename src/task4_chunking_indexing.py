"""
Task 4 — Chunking, embedding và indexing.

Hướng dẫn:
    1. Đọc toàn bộ Markdown trong data/standardized/.
    2. Chia văn bản bằng strategy đã chọn.
    3. Embed chunks bằng một provider duy nhất.
    4. Upsert vào ChromaDB với cosine distance.

Mỗi document/chunk phải theo docs/MODULE_CONTRACTS.md. ID cần ổn định để
chạy lại pipeline không tạo dữ liệu trùng. Task 5 phải dùng chung embed_texts().
"""

import os
import hashlib
import math
import re
import unicodedata
from pathlib import Path

from .contracts import validate_document
from .config import load_dotenv


STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

load_dotenv()

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "hashing").lower()
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
EMBEDDING_DIM = 384

COLLECTION_NAME = "rag_documents"
_EMBEDDING_CLIENT = None


def _batched(items: list[str], size: int = 64):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def _search_normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed text with one provider shared by indexing and querying."""
    global _EMBEDDING_CLIENT
    if not texts:
        return []
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("texts must contain non-empty strings")

    if EMBEDDING_PROVIDER == "hashing":
        dimensions = 1024
        vectors = []
        for text in texts:
            vector = [0.0] * dimensions
            normalized = _search_normalize(text)
            features = re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)
            features += [normalized[index:index + 3] for index in range(max(0, len(normalized) - 2))]
            for feature in features:
                digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
                value = int.from_bytes(digest, "big")
                vector[value % dimensions] += 1.0 if value & 1 else -1.0
            norm = math.sqrt(sum(item * item for item in vector)) or 1.0
            vectors.append([item / norm for item in vector])
        return vectors

    if EMBEDDING_PROVIDER == "sentence_transformers":
        from sentence_transformers import SentenceTransformer

        if _EMBEDDING_CLIENT is None:
            _EMBEDDING_CLIENT = SentenceTransformer(EMBEDDING_MODEL)
        return _EMBEDDING_CLIENT.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        ).tolist()

    if EMBEDDING_PROVIDER == "openai":
        from openai import OpenAI

        if _EMBEDDING_CLIENT is None:
            _EMBEDDING_CLIENT = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        vectors: list[list[float]] = []
        for batch in _batched(texts):
            response = _EMBEDDING_CLIENT.embeddings.create(model=EMBEDDING_MODEL, input=batch)
            vectors.extend(item.embedding for item in response.data)
        return vectors

    if EMBEDDING_PROVIDER == "gemini":
        from google import genai

        if _EMBEDDING_CLIENT is None:
            _EMBEDDING_CLIENT = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        vectors = []
        for text in texts:
            response = _EMBEDDING_CLIENT.models.embed_content(
                model=EMBEDDING_MODEL, contents=text
            )
            vectors.append(list(response.embeddings[0].values))
        return vectors

    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {EMBEDDING_PROVIDER}")


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    try:
        import chromadb

        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        return client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    except ImportError:
        from .local_vectorstore import SimplePersistentCollection

        return SimplePersistentCollection(CHROMA_DIR, COLLECTION_NAME)


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    metadata = {}
    for line in text[4:end].splitlines():
        key, separator, value = line.partition(":")
        if separator:
            metadata[key.strip()] = value.strip()
    return metadata, text[end + 5:].strip()


def load_documents() -> list[dict]:
    """Đọc Markdown và trả về danh sách Document."""
    documents = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        raw = path.read_text(encoding="utf-8")
        frontmatter, content = _parse_frontmatter(raw)
        doc_type = frontmatter.get("doc_type") or (
            "legal" if "legal" in path.relative_to(STANDARDIZED_DIR).parts else "news"
        )
        document = {
            "id": path.relative_to(STANDARDIZED_DIR).with_suffix("").as_posix(),
            "content": content,
            "metadata": {
                "source": frontmatter.get("source", path.name),
                "title": frontmatter.get("title", path.stem.replace("_", " ").title()),
                "doc_type": doc_type,
                "url": frontmatter.get("url") or None,
            },
        }
        validate_document(document)
        documents.append(document)
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    def split_text(content: str) -> list[str]:
        pieces = re.split(r"(?<=\n\n)|(?<=[.!?])\s+", content.strip())
        output: list[str] = []
        current = ""
        for piece in pieces:
            piece = piece.strip()
            while len(piece) > CHUNK_SIZE:
                cut = piece.rfind(" ", 0, CHUNK_SIZE + 1)
                cut = cut if cut > 0 else CHUNK_SIZE
                prefix = piece[:cut].strip()
                if current:
                    output.append(current)
                    current = ""
                output.append(prefix)
                piece = piece[max(0, cut - CHUNK_OVERLAP):].strip()
            candidate = f"{current} {piece}".strip()
            if len(candidate) <= CHUNK_SIZE:
                current = candidate
            else:
                output.append(current)
                overlap = current[-CHUNK_OVERLAP:].lstrip() if current else ""
                current = f"{overlap} {piece}".strip()
        if current:
            output.append(current)
        return output
    chunks = []
    seen_ids = set()
    for document in documents:
        validate_document(document)
        for index, text in enumerate(split_text(document["content"])):
            text = text.strip()
            if not text:
                continue
            chunk = {
                "id": f"{document['id']}::chunk-{index:04d}",
                "content": text,
                "metadata": {**document["metadata"], "chunk_index": index},
            }
            if chunk["id"] in seen_ids:
                raise ValueError(f"Duplicate chunk ID: {chunk['id']}")
            validate_document(chunk, require_chunk=True)
            seen_ids.add(chunk["id"])
            chunks.append(chunk)
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    for chunk in chunks:
        validate_document(chunk, require_chunk=True)
    vectors = embed_texts([chunk["content"] for chunk in chunks])
    if len(vectors) != len(chunks):
        raise ValueError("Embedding provider returned an unexpected number of vectors")
    return [{**chunk, "embedding": vector} for chunk, vector in zip(chunks, vectors)]


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB."""
    if not chunks:
        return
    collection = get_collection()
    incoming_ids = {chunk["id"] for chunk in chunks}
    existing_ids = set(collection.get()["ids"])
    stale_ids = sorted(existing_ids - incoming_ids)
    if stale_ids:
        collection.delete(ids=stale_ids)
    batch_size = 100
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["content"] for chunk in batch],
            embeddings=[chunk["embedding"] for chunk in batch],
            metadatas=[
                {key: ("" if value is None else value) for key, value in chunk["metadata"].items()}
                for chunk in batch
            ],
        )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    chunks = chunk_documents(documents)
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks")


if __name__ == "__main__":
    run_pipeline()
