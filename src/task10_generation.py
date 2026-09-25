"""
Task 10 — Generation có citation.

Hướng dẫn:
    1. Retrieve top-k chunks.
    2. Reorder để giảm lost-in-the-middle.
    3. Format context kèm title và source.
    4. Gọi provider được chọn trong .env.
    5. Trả answer, sources và retrieval_source.

Nếu context không đủ hoặc provider lỗi, trả safe refusal; không bịa thông tin.
"""

import os
import re
import time
import unicodedata

from .task9_retrieval_pipeline import retrieve
from .contracts import validate_generation_result
from .config import load_dotenv


load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "extractive")
LLM_MODEL = os.getenv("LLM_MODEL", "")

SYSTEM_PROMPT = """Bạn là trợ lý thông tin sinh viên Đại học Bách khoa Hà Nội.
Chỉ trả lời bằng thông tin trong context. Gắn citation [S1], [S2] ngay sau mỗi
khẳng định có thể kiểm chứng. Không dùng kiến thức bên ngoài. Nếu context không
đủ bằng chứng, trả lời: \"Tôi không thể xác minh thông tin này từ nguồn hiện có.\""""

SAFE_REFUSAL = "Tôi không thể xác minh thông tin này từ nguồn hiện có."


def _normalized_terms(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    stopwords = {
        "ai", "bao", "bi", "cac", "cho", "co", "cua", "duoc", "gi", "la", "mot",
        "nao", "nhung", "o", "ra", "the", "thi", "toi", "trong", "va", "ve",
    }
    return {
        token for token in re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)
        if len(token) > 1 and token not in stopwords
    }


def _has_grounded_evidence(query: str, chunks: list[dict]) -> bool:
    query_terms = _normalized_terms(query)
    if not query_terms:
        return False
    domain_terms = {
        "bhyt", "bao", "bong", "cong", "cpa", "dao", "diem", "dang", "giay", "hiem", "hoc",
        "ky", "nghi", "phi", "ren", "sinh", "the", "thi", "tin", "tot", "truong",
        "tuc", "vien", "xa",
    }
    if not query_terms & domain_terms:
        return False
    context_terms = _normalized_terms(" ".join(chunk["content"] for chunk in chunks))
    overlap = len(query_terms & context_terms)
    if len(query_terms) == 1:
        return overlap == 1
    return overlap >= 2 and overlap / len(query_terms) >= 0.45


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context."""
    if len(chunks) <= 2:
        return list(chunks)
    return list(chunks[::2]) + list(reversed(chunks[1::2]))


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk["metadata"]
        citation_index = chunk.get("_citation_index", index)
        parts.append(
            f"[S{citation_index}] Title: {metadata['title']} | Source: {metadata['source']} | "
            f"URL: {metadata.get('url') or 'local document'}\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def _extractive_answer(user_message: str) -> str:
    context, _, question = user_message.partition("\n\nQuestion:")
    query_terms = _normalized_terms(question)
    stopwords = {"là", "và", "có", "của", "cho", "được", "như", "thế", "nào", "gì"}
    query_terms -= stopwords
    candidates = []
    current_source = "S1"
    for line in context.splitlines():
        source_match = re.match(r"\[(S\d+)\]", line)
        if source_match:
            current_source = source_match.group(1)
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            sentence_terms = _normalized_terms(sentence)
            overlap = len(query_terms & sentence_terms)
            if overlap and len(sentence) >= 30:
                candidates.append((overlap, len(sentence), sentence.strip(), current_source))
    if not candidates:
        return SAFE_REFUSAL
    candidates.sort(key=lambda item: (-item[0], item[1]))
    selected = []
    seen = set()
    for _, _, sentence, source in candidates:
        normalized = sentence.lower()
        if normalized in seen:
            continue
        selected.append(f"{sentence} [{source}]")
        seen.add(normalized)
        if len(selected) == 3:
            break
    return " ".join(selected)


RATE_LIMIT_RETRIES = 4
RATE_LIMIT_BACKOFF_SECONDS = 15


def call_llm(system_prompt: str, user_message: str, model: str | None = None) -> str:
    """Gọi provider; retry có backoff khi bị rate limit theo phút (HTTP 429).

    `model` ghi đè LLM_MODEL (cùng provider). Hết quota theo ngày thì raise ngay.
    """
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        try:
            return _call_provider(system_prompt, user_message, model or LLM_MODEL)
        except Exception as error:
            message = str(error)
            is_rate_limited = "429" in message or "RESOURCE_EXHAUSTED" in message
            is_daily_quota = "PerDay" in message
            if not is_rate_limited or is_daily_quota or attempt == RATE_LIMIT_RETRIES:
                raise
            wait = RATE_LIMIT_BACKOFF_SECONDS * (attempt + 1)
            print(f"Rate limited by {LLM_PROVIDER}; retry in {wait}s")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def _call_provider(system_prompt: str, user_message: str, model: str) -> str:
    provider = LLM_PROVIDER.lower()
    if provider == "extractive":
        return _extractive_answer(user_message)
    if not model:
        raise ValueError("LLM_MODEL is not configured")
    if provider == "openai":
        from openai import OpenAI

        response = OpenAI(api_key=os.getenv("OPENAI_API_KEY")).responses.create(
            model=model,
            instructions=system_prompt,
            input=user_message,
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return response.output_text.strip()
    if provider == "gemini":
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model=model,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=TEMPERATURE,
                top_p=TOP_P,
            ),
        )
        return (response.text or "").strip()
    if provider == "anthropic":
        from anthropic import Anthropic

        response = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY")).messages.create(
            model=model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=1000,
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return "".join(block.text for block in response.content if hasattr(block, "text")).strip()
    raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    if not query.strip() or top_k <= 0:
        result = {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}
        validate_generation_result(result)
        return result
    chunks = retrieve(query, top_k=top_k)
    if not chunks or not _has_grounded_evidence(query, chunks):
        result = {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}
        validate_generation_result(result)
        return result
    labeled_chunks = [
        {**chunk, "_citation_index": index} for index, chunk in enumerate(chunks, 1)
    ]
    reordered = reorder_for_llm(labeled_chunks)
    context = format_context(reordered)
    user_message = f"Context:\n{context}\n\nQuestion: {query}"
    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception:
        answer = SAFE_REFUSAL
    if not answer:
        answer = SAFE_REFUSAL
    citation_numbers = [int(value) for value in re.findall(r"\[S(\d+)\]", answer)]
    if answer != SAFE_REFUSAL and (
        not citation_numbers or any(number < 1 or number > len(chunks) for number in citation_numbers)
    ):
        answer = SAFE_REFUSAL
    retrieval_method = chunks[0]["retrieval_method"]
    retrieval_source = "pageindex" if retrieval_method == "pageindex" else "hybrid"
    result = {"answer": answer, "sources": chunks, "retrieval_source": retrieval_source}
    validate_generation_result(result)
    return result


if __name__ == "__main__":
    print(generate_with_citation("test query"))
