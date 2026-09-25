"""
Bonus — Conversation memory cho câu hỏi follow-up.

Câu follow-up như "Còn hồ sơ thì cần gì?" thiếu chủ đề nên retrieval trả sai
nguồn. `condense_query` viết lại câu hỏi thành câu độc lập dựa trên lịch sử:
- Provider API (gemini/openai/anthropic): LLM viết lại câu hỏi.
- Extractive/offline hoặc LLM lỗi: heuristic ghép câu hỏi trước vào câu follow-up.
"""

import os
import re
import unicodedata
import warnings

from .task10_generation import LLM_MODEL, LLM_PROVIDER, call_llm


# Model nhẹ riêng cho bước viết lại câu hỏi để không tiêu quota của model trả lời.
MEMORY_LLM_MODEL = os.getenv("MEMORY_LLM_MODEL") or LLM_MODEL


CONDENSE_PROMPT = """Viết lại câu hỏi cuối của người dùng thành một câu hỏi độc lập,
đầy đủ chủ đề, dựa trên lịch sử hội thoại. Chỉ trả về đúng một câu hỏi, không
giải thích. Nếu câu hỏi đã độc lập thì giữ nguyên."""

HISTORY_TURNS = 3
FOLLOW_UP_MAX_TOKENS = 5
# So khớp có dấu: bỏ dấu sẽ nhầm "nợ" với "nó", "đó" với "độ".
FOLLOW_UP_MARKERS = {"còn", "vậy", "đó", "này", "nó", "sao"}


def _tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFC", text.lower())
    return re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)


def looks_like_follow_up(query: str) -> bool:
    tokens = _tokens(query)
    return len(tokens) <= FOLLOW_UP_MAX_TOKENS or bool(FOLLOW_UP_MARKERS & set(tokens))


def _heuristic_condense(query: str, user_turns: list[str]) -> str:
    if not looks_like_follow_up(query):
        return query
    return f"{user_turns[-1]} {query}"


def condense_query(query: str, history: list[dict]) -> str:
    """Trả về câu hỏi độc lập; history là list {"role", "content"} theo thứ tự thời gian."""
    user_turns = [turn["content"] for turn in history if turn.get("role") == "user"]
    if not query.strip() or not user_turns:
        return query
    if LLM_PROVIDER.lower() == "extractive":
        return _heuristic_condense(query, user_turns)
    try:
        rewritten = llm_condense(query, history)
    except Exception as error:
        warnings.warn(f"LLM condense lỗi ({error}); dùng heuristic.")
        return _heuristic_condense(query, user_turns)
    return rewritten or _heuristic_condense(query, user_turns)


def llm_condense(query: str, history: list[dict]) -> str:
    """Viết lại bằng LLM, không fallback; trả chuỗi rỗng nếu LLM không trả gì."""
    transcript = "\n".join(
        f"{turn['role']}: {turn['content']}" for turn in history[-HISTORY_TURNS * 2:]
    )
    rewritten = call_llm(
        CONDENSE_PROMPT,
        f"Lịch sử:\n{transcript}\n\nCâu hỏi cuối: {query}",
        model=MEMORY_LLM_MODEL,
    )
    return rewritten.strip().splitlines()[0].strip() if rewritten.strip() else ""
