"""Bonus experiments: BGE-M3 rerank vs RRF, conversation memory, generator A/B.

Chạy sau `python -m src.evaluate` (dùng lại Config B trong evaluation_results.json
làm baseline RRF + extractive), rồi render lại RESULT.md với mục Bonus experiments.

Các bước gọi LLM (memory rewrite, generator A/B) được cache trong bonus_results.json
theo tên model để chạy lại không tốn thêm quota API.
"""

from __future__ import annotations

import json
import os

from .conversation_memory import MEMORY_LLM_MODEL, _heuristic_condense, llm_condense
from .evaluate import (
    BONUS_PATH, DATASET_PATH, EXTRACTIVE, OUTPUT_PATH, ROOT, _coverage,
    evaluate_configuration, generator_label, write_report,
)
from .task10_generation import LLM_PROVIDER
from .task9_retrieval_pipeline import retrieve


FOLLOWUP_PATH = ROOT / "group_project" / "evaluation" / "followup_dataset.json"
GENERATOR_AB_MODEL = os.getenv("GENERATOR_AB_MODEL", "gemini-3-flash-preview")


def _compare_reranker(dataset: list[dict], baseline: dict) -> dict:
    reranked = evaluate_configuration(dataset, use_reranking=True, bge_rerank=True)
    delta = reranked["aggregate"]["average"] - baseline["aggregate"]["average"]
    dropped = {"legal": 0, "news": 0}
    added = {"legal": 0, "news": 0}
    for before, after in zip(baseline["cases"], reranked["cases"]):
        for chunk_id in set(before["source_ids"]) - set(after["source_ids"]):
            dropped[chunk_id.split("/")[0]] += 1
        for chunk_id in set(after["source_ids"]) - set(before["source_ids"]):
            added[chunk_id.split("/")[0]] += 1
    shift = (
        f"So với RRF, BGE-M3 loại {dropped['legal']} chunk legal và {dropped['news']} chunk news "
        f"khỏi top-5, thêm {added['legal']} chunk legal và {added['news']} chunk news."
    )
    if delta > 0:
        conclusion = f"BGE-M3 rerank tăng điểm trung bình {delta:+.3f} so với RRF. {shift}"
    else:
        conclusion = (
            f"BGE-M3 rerank giảm điểm trung bình ({delta:+.3f}) và chậm hơn nhiều trên CPU; "
            f"giữ RRF làm mặc định. {shift} Nguyên nhân: Markdown của ba tài liệu legal "
            "không có dấu tiếng Việt, nên embedding ngữ nghĩa ưu tiên các bài news có dấu; "
            "BM25 trong RRF không bị ảnh hưởng vì so khớp theo token. Cần convert lại PDF "
            "gốc có dấu rồi đo lại."
        )
    return {
        "size": len(dataset),
        "rrf": baseline["aggregate"],
        "rrf_bge": reranked["aggregate"],
        "latency_ms": {
            "rrf": baseline["average_latency_ms"],
            "rrf_bge": reranked["average_latency_ms"],
        },
        "conclusion": conclusion,
        "cases": reranked["cases"],
    }


def _retrieval_scores(query: str, item: dict) -> dict:
    chunks = retrieve(query, top_k=5, score_threshold=-1.0, use_reranking=True)
    context = " ".join(chunk["content"] for chunk in chunks)
    return {
        "query": query,
        "context_recall": _coverage(item["expected_context"], context),
        "source_hit": any(chunk["metadata"]["source"] == item["source"] for chunk in chunks),
    }


def _llm_rewrites(followups: list[dict], cached: dict) -> list[str]:
    if cached.get("model") == MEMORY_LLM_MODEL and len(cached.get("queries", [])) == len(followups):
        return cached["queries"]
    return [
        llm_condense(item["question"], [{"role": "user", "content": turn} for turn in item["history"]])
        or item["question"]
        for item in followups
    ]


def _compare_memory(followups: list[dict], cached: dict) -> dict:
    rewrites = {
        "Không memory (câu gốc)": [item["question"] for item in followups],
        "Memory heuristic (ghép câu trước)": [
            _heuristic_condense(item["question"], item["history"]) for item in followups
        ],
    }
    llm_cache = {}
    if LLM_PROVIDER.lower() != EXTRACTIVE:
        llm_queries = _llm_rewrites(followups, cached.get("llm_rewrite", {}))
        rewrites[f"Memory LLM rewrite ({LLM_PROVIDER} / {MEMORY_LLM_MODEL})"] = llm_queries
        llm_cache = {"model": MEMORY_LLM_MODEL, "queries": llm_queries}
    cases = {
        name: [_retrieval_scores(query, item) for query, item in zip(queries, followups)]
        for name, queries in rewrites.items()
    }
    aggregate = {
        name: {
            "context_recall": sum(case["context_recall"] for case in results) / len(results),
            "source_hit_rate": sum(case["source_hit"] for case in results) / len(results),
        }
        for name, results in cases.items()
    }
    baseline, *memory = aggregate.values()
    best_name, best = max(
        zip(list(aggregate)[1:], memory), key=lambda pair: pair[1]["context_recall"]
    )
    conclusion = (
        f"{best_name} tăng context recall {best['context_recall'] - baseline['context_recall']:+.3f} "
        f"và source hit rate {best['source_hit_rate'] - baseline['source_hit_rate']:+.3f} "
        "so với không dùng memory."
    )
    if baseline["source_hit_rate"] == 1.0:
        conclusion += (
            " Không memory vẫn tìm đúng tài liệu nguồn ở mọi case vì corpus chỉ có 24 chunks; "
            "memory cải thiện việc lấy đúng đoạn trong tài liệu."
        )
    return {
        "size": len(followups), "aggregate": aggregate, "conclusion": conclusion,
        "cases": cases, "llm_rewrite": llm_cache,
    }


def _compare_generator(dataset: list[dict], baseline: dict, cached: dict) -> dict | None:
    if LLM_PROVIDER.lower() == EXTRACTIVE:
        return None
    label = generator_label(GENERATOR_AB_MODEL)
    if cached.get("llm", {}).get("generator") == label:
        llm = cached["llm"]
    else:
        llm = evaluate_configuration(dataset, use_reranking=True, llm_model=GENERATOR_AB_MODEL)
    delta = llm["aggregate"]["average"] - baseline["aggregate"]["average"]
    relevance_delta = llm["aggregate"]["answer_relevance"] - baseline["aggregate"]["answer_relevance"]
    conclusion = (
        f"{label} thay đổi điểm trung bình {delta:+.3f} và answer relevance "
        f"{relevance_delta:+.3f} so với extractive trên cùng retrieval hybrid + RRF."
    )
    return {"extractive": baseline, "llm": llm, "conclusion": conclusion}


def main() -> None:
    if not OUTPUT_PATH.exists():
        raise FileNotFoundError("Chạy `python -m src.evaluate` trước để có Config A/B.")
    results = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    if results["config_b"].get("generator") != generator_label(EXTRACTIVE):
        raise ValueError("evaluation_results.json cũ; chạy lại `python -m src.evaluate`.")
    cached = json.loads(BONUS_PATH.read_text(encoding="utf-8")) if BONUS_PATH.exists() else {}
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    followups = json.loads(FOLLOWUP_PATH.read_text(encoding="utf-8"))
    bonus = {
        "reranker": _compare_reranker(dataset, results["config_b"]),
        "memory": _compare_memory(followups, cached.get("memory", {})),
    }
    BONUS_PATH.write_text(json.dumps(bonus, ensure_ascii=False, indent=2), encoding="utf-8")
    bonus["generator"] = _compare_generator(dataset, results["config_b"], cached.get("generator") or {})
    BONUS_PATH.write_text(json.dumps(bonus, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(results["config_a"], results["config_b"], len(dataset))
    print(f"Saved: {BONUS_PATH}")
    for section in bonus.values():
        if section:
            print(section["conclusion"])


if __name__ == "__main__":
    main()
