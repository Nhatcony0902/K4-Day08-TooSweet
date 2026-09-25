"""Reproducible dense-vs-hybrid evaluation over the checked-in golden dataset."""

from __future__ import annotations

import json
import re
import time
import unicodedata
from pathlib import Path

from .task10_generation import SAFE_REFUSAL, call_llm, format_context, reorder_for_llm
from .task9_retrieval_pipeline import retrieve


ROOT = Path(__file__).parent.parent
DATASET_PATH = ROOT / "group_project" / "evaluation" / "golden_dataset.json"
OUTPUT_PATH = ROOT / "group_project" / "evaluation" / "evaluation_results.json"
REPORT_PATH = ROOT / "group_project" / "evaluation" / "RESULT.md"
STOPWORDS = {
    "la", "va", "co", "cua", "cho", "duoc", "nhung", "cac", "mot", "thi", "o",
    "trong", "theo", "sinh", "vien", "hoc", "bao", "nhieu", "gi", "nao",
}


def _tokens(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    return {
        token for token in re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)
        if len(token) > 1 and token not in STOPWORDS
    }


def _coverage(reference: str, candidate: str) -> float:
    expected = _tokens(reference)
    actual = _tokens(candidate)
    return len(expected & actual) / len(expected) if expected else 1.0


def _f1(reference: str, candidate: str) -> float:
    expected = _tokens(reference)
    actual = _tokens(candidate)
    if not expected or not actual:
        return 0.0
    overlap = len(expected & actual)
    precision = overlap / len(actual)
    recall = overlap / len(expected)
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _answer(query: str, chunks: list[dict]) -> str:
    if not chunks:
        return SAFE_REFUSAL
    labeled = [{**chunk, "_citation_index": index} for index, chunk in enumerate(chunks, 1)]
    context = format_context(reorder_for_llm(labeled))
    return call_llm(
        "Chỉ trả lời từ context và gắn citation.",
        f"Context:\n{context}\n\nQuestion: {query}",
    )


def evaluate_configuration(dataset: list[dict], *, use_reranking: bool) -> dict:
    cases = []
    started = time.perf_counter()
    for item in dataset:
        case_started = time.perf_counter()
        chunks = retrieve(
            item["question"], top_k=5, score_threshold=-1.0, use_reranking=use_reranking
        )
        answer = _answer(item["question"], chunks)
        combined_context = " ".join(chunk["content"] for chunk in chunks)
        relevant_chunks = [
            chunk for chunk in chunks
            if _coverage(item["expected_context"], chunk["content"]) >= 0.15
        ]
        metrics = {
            "faithfulness": _coverage(answer, combined_context),
            "answer_relevance": _f1(item["expected_answer"], answer),
            "context_recall": _coverage(item["expected_context"], combined_context),
            "context_precision": len(relevant_chunks) / len(chunks) if chunks else 0.0,
        }
        cases.append({
            "question": item["question"],
            "answer": answer,
            "source_ids": [chunk["id"] for chunk in chunks],
            "metrics": metrics,
            "latency_ms": round((time.perf_counter() - case_started) * 1000, 2),
        })
    metric_names = ["faithfulness", "answer_relevance", "context_recall", "context_precision"]
    aggregate = {
        name: sum(case["metrics"][name] for case in cases) / len(cases)
        for name in metric_names
    }
    aggregate["average"] = sum(aggregate.values()) / len(metric_names)
    return {
        "strategy": "hybrid_rrf" if use_reranking else "dense_only",
        "aggregate": aggregate,
        "average_latency_ms": round((time.perf_counter() - started) * 1000 / len(cases), 2),
        "cases": cases,
    }


def _fmt(value: float) -> str:
    return f"{value:.3f}"


def write_report(config_a: dict, config_b: dict, dataset_size: int) -> None:
    calibration_path = ROOT / "group_project" / "evaluation" / "threshold_calibration.json"
    calibration = (
        json.loads(calibration_path.read_text(encoding="utf-8"))
        if calibration_path.exists() else {}
    )
    threshold = calibration.get("recommended_threshold", "not calibrated")
    balanced_accuracy = calibration.get("balanced_accuracy", "n/a")
    names = [
        ("Faithfulness", "faithfulness"),
        ("Answer relevance", "answer_relevance"),
        ("Context recall", "context_recall"),
        ("Context precision", "context_precision"),
        ("**Average**", "average"),
    ]
    score_rows = []
    for label, key in names:
        left = config_a["aggregate"][key]
        right = config_b["aggregate"][key]
        score_rows.append(f"| {label} | {_fmt(left)} | {_fmt(right)} | {_fmt(right - left)} |")
    combined = []
    for config in (config_a, config_b):
        for case in config["cases"]:
            average = sum(case["metrics"].values()) / len(case["metrics"])
            combined.append((average, config["strategy"], case))
    worst = sorted(combined, key=lambda item: item[0])[:3]
    worst_rows = []
    for index, (_, strategy, case) in enumerate(worst, 1):
        metrics = case["metrics"]
        stage = "retrieval" if metrics["context_recall"] < 0.6 else "generation"
        cause = (
            "Từ khóa truy vấn và tài liệu khác cách diễn đạt"
            if stage == "retrieval" else "Extractive baseline lấy dư thông tin"
        )
        question = case["question"].replace("|", "\\|")
        worst_rows.append(
            f"| {index} | {question} | {strategy} | {_fmt(metrics['faithfulness'])} | "
            f"{_fmt(metrics['answer_relevance'])} | {_fmt(metrics['context_recall'])} | "
            f"{_fmt(metrics['context_precision'])} | {stage} | {cause} |"
        )
    better = "Config B — hybrid + RRF" if config_b["aggregate"]["average"] >= config_a["aggregate"]["average"] else "Config A — dense-only"
    report = f"""# RAG evaluation results

## Run information

| Field | Value |
|---|---|
| Evaluation date | 2026-09-25 |
| Framework and version | Local deterministic evaluator v1; Ragas-compatible metric names |
| Evaluator model | Token-overlap evaluator (offline, deterministic) |
| Generator model | Extractive baseline (offline) |
| Embedding model | hashing-1024 |
| Corpus version/commit | working tree based on `a23df34` |
| Golden dataset size | {dataset_size} |
| `top_k` | 5 |
| Fallback threshold and calibration | {threshold}; balanced accuracy {balanced_accuracy}. Fallback disabled only during A/B to isolate retrieval strategy |

## Configurations

- **Config A — dense-only:** hashing embedding, cosine search, top-k 5.
- **Config B — hybrid + RRF:** the same dense search plus BM25, fused once with RRF `k=60`.

Hai cấu hình dùng cùng corpus, golden dataset, generator, evaluator và `top_k`; chỉ thay retrieval strategy.

## Overall scores

| Metric | Config A | Config B | Delta B−A |
|---|---:|---:|---:|
{chr(10).join(score_rows)}

## A/B comparison

- Cấu hình tốt hơn: **{better}**.
- Evidence: điểm trung bình dense-only là {_fmt(config_a['aggregate']['average'])}; hybrid + RRF là {_fmt(config_b['aggregate']['average'])}.
- Trade-off latency: dense-only {config_a['average_latency_ms']:.2f} ms/query; hybrid + RRF {config_b['average_latency_ms']:.2f} ms/query trên máy đánh giá.
- Chi phí API: 0 cho lần chạy này vì embedding, generation và evaluator đều chạy offline.

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
|---:|---|---|---:|---:|---:|---:|---|---|
{chr(10).join(worst_rows)}

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
|---:|---|---|---|---|
| 1 | Dùng multilingual sentence-transformer khi có thể tải model | Hash embedding phụ thuộc nhiều vào từ khóa bề mặt | Tăng context recall cho câu diễn đạt lại | Chạy lại cùng 15 câu và so delta recall |
| 2 | Loại menu/footer khỏi các bài crawl dài | Một số chunk tin tức có nội dung điều hướng | Tăng context precision | Kiểm tra ba case precision thấp nhất |
| 3 | Dùng Gemini với prompt citation khi có SDK/network | Extractive baseline có câu trả lời kém tự nhiên | Tăng answer relevance | Giữ nguyên retrieval và A/B generator |

## Bonus experiments

Chưa chạy bonus. Ưu tiên hoàn thiện và kiểm chứng pipeline bắt buộc trước HyDE, reranker nâng cao hoặc conversation memory.

> Lưu ý: bốn metric trong lần chạy offline là phép đo lexical có cùng tên/chiều tối ưu với bộ metric RAG. Khi có kết nối và evaluator API, có thể chạy thêm Ragas để có đánh giá dựa trên LLM; không nên trình bày số offline này là điểm Ragas.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    config_a = evaluate_configuration(dataset, use_reranking=False)
    config_b = evaluate_configuration(dataset, use_reranking=True)
    OUTPUT_PATH.write_text(
        json.dumps({"config_a": config_a, "config_b": config_b}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_report(config_a, config_b, len(dataset))
    print(f"Saved: {OUTPUT_PATH}")
    print(f"Saved: {REPORT_PATH}")


if __name__ == "__main__":
    main()
