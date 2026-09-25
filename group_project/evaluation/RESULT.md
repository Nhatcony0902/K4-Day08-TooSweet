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
- Trade-off latency: dense-only 74.08 ms/query; hybrid + RRF 14.54 ms/query trên máy đánh giá.
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
| 3 | Chatbot dùng Gemini thay extractive (đã triển khai, xem Bonus mục 3); chạy `python -m src.evaluate_ragas` khi có quota | Extractive baseline lấy dư câu, lexical metric phạt câu LLM diễn đạt lại | Answer relevance phản ánh đúng chất lượng | So thứ hạng A/B giữa lexical và Ragas |

## Bonus experiments

### 1. Rerank BGE-M3 so với RRF

- **Config B — hybrid + RRF** so với **Config C — hybrid + RRF lấy top-10 rồi chấm lại bằng cosine embedding `BAAI/bge-m3`**; cùng generator, evaluator và 15 golden cases.
- Latency trung bình (CPU, gồm generation): RRF 15 ms/query; RRF + BGE 7660 ms/query.

| Metric | RRF | RRF + BGE | Delta |
|---|---:|---:|---:|
| Faithfulness | 0.944 | 0.947 | 0.004 |
| Answer relevance | 0.327 | 0.259 | -0.068 |
| Context recall | 0.948 | 0.945 | -0.003 |
| Context precision | 0.920 | 0.907 | -0.013 |
| **Average** | 0.785 | 0.765 | -0.020 |

Kết luận: BGE-M3 rerank giảm điểm trung bình (-0.020) và chậm hơn nhiều trên CPU; giữ RRF làm mặc định. So với RRF, BGE-M3 loại 22 chunk legal và 6 chunk news khỏi top-5, thêm 5 chunk legal và 23 chunk news. Nguyên nhân: Markdown của ba tài liệu legal không có dấu tiếng Việt, nên embedding ngữ nghĩa ưu tiên các bài news có dấu; BM25 trong RRF không bị ảnh hưởng vì so khớp theo token. Cần convert lại PDF gốc có dấu rồi đo lại.

### 2. Conversation memory cho câu hỏi follow-up

- 6 hội thoại hai lượt trong `group_project/evaluation/followup_dataset.json`; lượt hai thiếu chủ đề (vd. "Còn hồ sơ thì cần giấy tờ gì?").
- Đo retrieval của lượt hai (hybrid + RRF, top-5): context recall so với expected context và tỉ lệ top-5 chứa đúng tài liệu nguồn.

| Cách xử lý câu follow-up | Context recall | Source hit rate |
|---|---:|---:|
| Không memory (câu gốc) | 0.928 | 1.000 |
| Memory heuristic (ghép câu trước) | 0.943 | 1.000 |
| Memory LLM rewrite (gemini / gemini-2.5-flash-lite) | 0.964 | 1.000 |

Kết luận: Memory LLM rewrite (gemini / gemini-2.5-flash-lite) tăng context recall +0.036 và source hit rate +0.000 so với không dùng memory. Không memory vẫn tìm đúng tài liệu nguồn ở mọi case vì corpus chỉ có 24 chunks; memory cải thiện việc lấy đúng đoạn trong tài liệu.

Demo: trong Streamlit, câu follow-up được viết lại bằng `src/conversation_memory.py`; câu hỏi độc lập hiển thị dưới câu trả lời.

### 3. Generator: extractive so với gemini / gemini-3-flash-preview

- Cùng retrieval hybrid + RRF top-5 và 15 golden cases; chỉ đổi generator. Lần chạy tốn 15 lượt gọi API.
- Chatbot dùng `LLM_PROVIDER=gemini`; free tier giới hạn 20 request/ngày cho mỗi model, nên A/B retrieval ở trên giữ generator extractive.

| Metric | Extractive | gemini / gemini-3-flash-preview | Delta |
|---|---:|---:|---:|
| Faithfulness | 0.944 | 0.859 | -0.084 |
| Answer relevance | 0.327 | 0.512 | 0.185 |
| Context recall | 0.948 | 0.948 | 0.000 |
| Context precision | 0.920 | 0.920 | 0.000 |
| **Average** | 0.785 | 0.810 | 0.025 |

Kết luận: gemini / gemini-3-flash-preview thay đổi điểm trung bình +0.025 và answer relevance +0.185 so với extractive trên cùng retrieval hybrid + RRF.

> Lưu ý: bốn metric trong lần chạy offline là phép đo lexical có cùng tên/chiều tối ưu với bộ metric RAG. Khi có kết nối và evaluator API, có thể chạy thêm Ragas để có đánh giá dựa trên LLM; không nên trình bày số offline này là điểm Ragas.
