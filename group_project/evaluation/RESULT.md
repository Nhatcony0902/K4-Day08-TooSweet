# RAG evaluation results

## Run information

| Field | Value |
|---|---|
| Evaluation date | 2026-09-25 |
| Framework and version | Local deterministic evaluator v1; Ragas-compatible metric names |
| Evaluator model | Token-overlap evaluator (offline, deterministic) |
| Generator model | Extractive baseline (offline) |
| Embedding model | hashing-1024 |
| Corpus version/commit | working tree based on `a23df34` |
| Golden dataset size | 15 |
| `top_k` | 5 |
| Fallback threshold and calibration | 0.4115; balanced accuracy 0.9375. Fallback disabled only during A/B to isolate retrieval strategy |

## Configurations

- **Config A — dense-only:** hashing embedding, cosine search, top-k 5.
- **Config B — hybrid + RRF:** the same dense search plus BM25, fused once with RRF `k=60`.

Hai cấu hình dùng cùng corpus, golden dataset, generator, evaluator và `top_k`; chỉ thay retrieval strategy.

## Overall scores

| Metric | Config A | Config B | Delta B−A |
|---|---:|---:|---:|
| Faithfulness | 0.944 | 0.944 | -0.000 |
| Answer relevance | 0.325 | 0.327 | 0.002 |
| Context recall | 0.941 | 0.948 | 0.007 |
| Context precision | 0.893 | 0.920 | 0.027 |
| **Average** | 0.776 | 0.785 | 0.009 |

## A/B comparison

- Cấu hình tốt hơn: **Config B — hybrid + RRF**.
- Evidence: điểm trung bình dense-only là 0.776; hybrid + RRF là 0.785.
- Trade-off latency: dense-only 13.86 ms/query; hybrid + RRF 13.19 ms/query trên máy đánh giá.
- Chi phí API: 0 cho lần chạy này vì embedding, generation và evaluator đều chạy offline.

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
|---:|---|---|---:|---:|---:|---:|---|---|
| 1 | Tân sinh viên cần làm gì để tránh lừa đảo khi đăng ký ký túc xá? | dense_only | 0.968 | 0.238 | 0.741 | 0.800 | generation | Extractive baseline lấy dư thông tin |
| 2 | Thời gian nghỉ học dài hạn tối đa là bao nhiêu học kỳ? | dense_only | 0.933 | 0.296 | 1.000 | 0.600 | generation | Extractive baseline lấy dư thông tin |
| 3 | Thời gian nghỉ học dài hạn tối đa là bao nhiêu học kỳ? | hybrid_rrf | 0.932 | 0.302 | 1.000 | 0.600 | generation | Extractive baseline lấy dư thông tin |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
|---:|---|---|---|---|
| 1 | Dùng multilingual sentence-transformer khi có thể tải model | Hash embedding phụ thuộc nhiều vào từ khóa bề mặt | Tăng context recall cho câu diễn đạt lại | Chạy lại cùng 15 câu và so delta recall |
| 2 | Loại menu/footer khỏi các bài crawl dài | Một số chunk tin tức có nội dung điều hướng | Tăng context precision | Kiểm tra ba case precision thấp nhất |
| 3 | Dùng Gemini với prompt citation khi có SDK/network | Extractive baseline có câu trả lời kém tự nhiên | Tăng answer relevance | Giữ nguyên retrieval và A/B generator |

## Bonus experiments

Chưa chạy bonus. Ưu tiên hoàn thiện và kiểm chứng pipeline bắt buộc trước HyDE, reranker nâng cao hoặc conversation memory.

> Lưu ý: bốn metric trong lần chạy offline là phép đo lexical có cùng tên/chiều tối ưu với bộ metric RAG. Khi có kết nối và evaluator API, có thể chạy thêm Ragas để có đánh giá dựa trên LLM; không nên trình bày số offline này là điểm Ragas.
