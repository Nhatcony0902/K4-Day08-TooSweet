"""Reproducible dense-vs-hybrid evaluation over the checked-in golden dataset."""

from __future__ import annotations

import json
import re
import time
import unicodedata
from pathlib import Path

from .bge_reranking import RERANKER_MODEL, rerank_bge
from .task10_generation import (
    LLM_MODEL, LLM_PROVIDER, SAFE_REFUSAL, SYSTEM_PROMPT, _extractive_answer, call_llm,
    format_context, reorder_for_llm,
)
from .task9_retrieval_pipeline import retrieve


ROOT = Path(__file__).parent.parent
DATASET_PATH = ROOT / "group_project" / "evaluation" / "golden_dataset.json"
OUTPUT_PATH = ROOT / "group_project" / "evaluation" / "evaluation_results.json"
REPORT_PATH = ROOT / "group_project" / "evaluation" / "RESULT.md"
BONUS_PATH = ROOT / "group_project" / "evaluation" / "bonus_results.json"
CANDIDATE_K = 10
EXTRACTIVE = "extractive"
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


def _answer(query: str, chunks: list[dict], llm_model: str | None = None) -> str:
    """llm_model: None = provider/model trong .env; EXTRACTIVE = baseline offline."""
    if not chunks:
        return SAFE_REFUSAL
    labeled = [{**chunk, "_citation_index": index} for index, chunk in enumerate(chunks, 1)]
    user_message = f"Context:\n{format_context(reorder_for_llm(labeled))}\n\nQuestion: {query}"
    if llm_model == EXTRACTIVE:
        return _extractive_answer(user_message)
    return call_llm(SYSTEM_PROMPT, user_message, model=llm_model)


def generator_label(llm_model: str | None = None) -> str:
    if llm_model == EXTRACTIVE or (llm_model is None and LLM_PROVIDER.lower() == EXTRACTIVE):
        return "Extractive baseline (offline)"
    return f"{LLM_PROVIDER} / {llm_model or LLM_MODEL}"


def _retrieve_for_eval(question: str, *, use_reranking: bool, bge_rerank: bool) -> list[dict]:
    if not bge_rerank:
        return retrieve(question, top_k=5, score_threshold=-1.0, use_reranking=use_reranking)
    candidates = retrieve(question, top_k=CANDIDATE_K, score_threshold=-1.0, use_reranking=True)
    return rerank_bge(question, candidates, top_k=5)


def evaluate_configuration(
    dataset: list[dict],
    *,
    use_reranking: bool,
    bge_rerank: bool = False,
    llm_model: str | None = EXTRACTIVE,
) -> dict:
    """Mặc định generator extractive để A/B retrieval cố định generator, không tốn API quota."""
    cases = []
    started = time.perf_counter()
    for item in dataset:
        case_started = time.perf_counter()
        chunks = _retrieve_for_eval(
            item["question"], use_reranking=use_reranking, bge_rerank=bge_rerank
        )
        answer = _answer(item["question"], chunks, llm_model)
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
    strategy = "dense_only"
    if use_reranking:
        strategy = "hybrid_rrf_bge" if bge_rerank else "hybrid_rrf"
    return {
        "strategy": strategy,
        "generator": generator_label(llm_model),
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
    generator = config_b.get("generator", "Extractive baseline (offline)")
    is_offline = generator.startswith("Extractive")
    generation_cause = (
        "Extractive baseline lấy dư thông tin" if is_offline
        else "LLM diễn đạt khác đáp án chuẩn; lexical metric phạt paraphrase"
    )
    cost_line = (
        "0 cho lần chạy này vì embedding, generation và evaluator đều chạy offline."
        if is_offline else
        f"{2 * dataset_size} lần gọi {generator} cho generation A/B; "
        "embedding và evaluator chạy offline."
    )
    generation_recommendation = (
        "| 3 | Chatbot dùng Gemini thay extractive (đã triển khai, xem Bonus mục 3); chạy "
        "`python -m src.evaluate_ragas` khi có quota | Extractive baseline lấy dư câu, lexical "
        "metric phạt câu LLM diễn đạt lại | Answer relevance phản ánh đúng chất lượng | "
        "So thứ hạng A/B giữa lexical và Ragas |"
    )
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
            if stage == "retrieval" else generation_cause
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
| Generator model | {generator} |
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
- Chi phí API: {cost_line}

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
|---:|---|---|---:|---:|---:|---:|---|---|
{chr(10).join(worst_rows)}

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
|---:|---|---|---|---|
| 1 | Dùng multilingual sentence-transformer khi có thể tải model | Hash embedding phụ thuộc nhiều vào từ khóa bề mặt | Tăng context recall cho câu diễn đạt lại | Chạy lại cùng 15 câu và so delta recall |
| 2 | Loại menu/footer khỏi các bài crawl dài | Một số chunk tin tức có nội dung điều hướng | Tăng context precision | Kiểm tra ba case precision thấp nhất |
{generation_recommendation}

## Bonus experiments

{render_bonus_section()}

> Lưu ý: bốn metric trong lần chạy offline là phép đo lexical có cùng tên/chiều tối ưu với bộ metric RAG. Khi có kết nối và evaluator API, có thể chạy thêm Ragas để có đánh giá dựa trên LLM; không nên trình bày số offline này là điểm Ragas.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def render_bonus_section() -> str:
    if not BONUS_PATH.exists():
        return "Chưa chạy bonus. Chạy `python -m src.evaluate_bonus` sau `python -m src.evaluate`."
    bonus = json.loads(BONUS_PATH.read_text(encoding="utf-8"))
    rerank = bonus["reranker"]
    rows = []
    for label, key in [
        ("Faithfulness", "faithfulness"), ("Answer relevance", "answer_relevance"),
        ("Context recall", "context_recall"), ("Context precision", "context_precision"),
        ("**Average**", "average"),
    ]:
        left = rerank["rrf"][key]
        right = rerank["rrf_bge"][key]
        rows.append(f"| {label} | {_fmt(left)} | {_fmt(right)} | {_fmt(right - left)} |")
    memory = bonus["memory"]
    generator_section = ""
    generator = bonus.get("generator")
    if generator:
        generator_rows = [
            f"| {label} | {_fmt(generator['extractive']['aggregate'][key])} | "
            f"{_fmt(generator['llm']['aggregate'][key])} | "
            f"{_fmt(generator['llm']['aggregate'][key] - generator['extractive']['aggregate'][key])} |"
            for label, key in [
                ("Faithfulness", "faithfulness"), ("Answer relevance", "answer_relevance"),
                ("Context recall", "context_recall"), ("Context precision", "context_precision"),
                ("**Average**", "average"),
            ]
        ]
        generator_section = f"""

### 3. Generator: extractive so với {generator['llm']['generator']}

- Cùng retrieval hybrid + RRF top-5 và 15 golden cases; chỉ đổi generator. Lần chạy tốn {len(generator['llm']['cases'])} lượt gọi API.
- Chatbot dùng `LLM_PROVIDER=gemini`; free tier giới hạn 20 request/ngày cho mỗi model, nên A/B retrieval ở trên giữ generator extractive.

| Metric | Extractive | {generator['llm']['generator']} | Delta |
|---|---:|---:|---:|
{chr(10).join(generator_rows)}

Kết luận: {generator['conclusion']}"""
    memory_rows = [
        f"| {name} | {_fmt(result['context_recall'])} | {_fmt(result['source_hit_rate'])} |"
        for name, result in memory["aggregate"].items()
    ]
    return f"""### 1. Rerank BGE-M3 so với RRF

- **Config B — hybrid + RRF** so với **Config C — hybrid + RRF lấy top-{CANDIDATE_K} rồi chấm lại bằng cosine embedding `{RERANKER_MODEL}`**; cùng generator, evaluator và {rerank['size']} golden cases.
- Latency trung bình (CPU, gồm generation): RRF {rerank['latency_ms']['rrf']:.0f} ms/query; RRF + BGE {rerank['latency_ms']['rrf_bge']:.0f} ms/query.

| Metric | RRF | RRF + BGE | Delta |
|---|---:|---:|---:|
{chr(10).join(rows)}

Kết luận: {rerank['conclusion']}

### 2. Conversation memory cho câu hỏi follow-up

- {memory['size']} hội thoại hai lượt trong `group_project/evaluation/followup_dataset.json`; lượt hai thiếu chủ đề (vd. "Còn hồ sơ thì cần giấy tờ gì?").
- Đo retrieval của lượt hai (hybrid + RRF, top-5): context recall so với expected context và tỉ lệ top-5 chứa đúng tài liệu nguồn.

| Cách xử lý câu follow-up | Context recall | Source hit rate |
|---|---:|---:|
{chr(10).join(memory_rows)}

Kết luận: {memory['conclusion']}

Demo: trong Streamlit, câu follow-up được viết lại bằng `src/conversation_memory.py`; câu hỏi độc lập hiển thị dưới câu trả lời.{generator_section}"""


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
