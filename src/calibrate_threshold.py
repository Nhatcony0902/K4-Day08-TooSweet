"""Calibrate the dense fallback threshold with in- and out-of-domain queries."""

import json
from pathlib import Path

from .task5_semantic_search import semantic_search


ROOT = Path(__file__).parent.parent
OUTPUT = ROOT / "group_project" / "evaluation" / "threshold_calibration.json"
IN_DOMAIN = [
    "Học phí được tính theo tín chỉ như thế nào?",
    "Điều kiện nhận học bổng tài năng là gì?",
    "Thời gian nghỉ học dài hạn tối đa bao lâu?",
    "Xin giấy chứng nhận sinh viên ở đâu?",
    "Cách đăng ký ký túc xá an toàn?",
    "Sinh viên có bắt buộc mua bảo hiểm y tế không?",
    "CPA để duy trì học bổng hỗ trợ là bao nhiêu?",
    "Tra cứu công nợ học phí ở đâu?",
]
OUT_OF_DOMAIN = [
    "Dự báo thời tiết ngày mai ở Đà Nẵng",
    "Giá Bitcoin hôm nay là bao nhiêu",
    "Cách nấu phở bò",
    "Ai là tổng thống Pháp",
    "Viết chương trình sắp xếp bằng Rust",
    "Tư vấn mua cổ phiếu ngân hàng",
    "Lịch thi đấu bóng đá Ngoại hạng Anh",
    "Triệu chứng đau ngực cần dùng thuốc gì",
]


def _best_score(query: str) -> float:
    results = semantic_search(query, top_k=1)
    return float(results[0]["score"]) if results else 0.0


def main() -> None:
    in_scores = [{"query": query, "score": _best_score(query)} for query in IN_DOMAIN]
    out_scores = [{"query": query, "score": _best_score(query)} for query in OUT_OF_DOMAIN]
    values = sorted({item["score"] for item in in_scores + out_scores})
    candidates = [0.0] + [(left + right) / 2 for left, right in zip(values, values[1:])] + [1.0]
    trials = []
    for threshold in candidates:
        true_positive = sum(item["score"] >= threshold for item in in_scores)
        true_negative = sum(item["score"] < threshold for item in out_scores)
        balanced_accuracy = (
            true_positive / len(in_scores) + true_negative / len(out_scores)
        ) / 2
        trials.append((balanced_accuracy, threshold))
    balanced_accuracy, threshold = max(trials, key=lambda item: (item[0], -item[1]))
    payload = {
        "embedding": "hashing-1024",
        "recommended_threshold": round(threshold, 4),
        "balanced_accuracy": round(balanced_accuracy, 4),
        "in_domain": in_scores,
        "out_of_domain": out_scores,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
