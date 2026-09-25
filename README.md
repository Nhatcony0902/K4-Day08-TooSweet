# Trợ lý dịch vụ sinh viên HUST — RAG Pipeline

**Tên nhóm:** TooSweet

**Repository:** `K4-DAY08-TooSweet`

## Mục tiêu

Chatbot RAG trả lời câu hỏi về quy chế đào tạo, học phí, học bổng, thủ tục và dịch vụ sinh viên Đại học Bách khoa Hà Nội. Pipeline có dense retrieval, BM25, RRF, PageIndex fallback, citation, giao diện Streamlit và evaluation A/B.

## Thành viên

- Lê Thanh Tình — `2A202602449` — Trưởng nhóm (Lead)
- Nguyễn Tiến Lượng — `2A202602378`
- Trần Xuân Đức — `2A202602768`
- Phạm Long Nhật — `2A202602844`

Phân công ownership và báo cáo cá nhân nằm trong thư mục `reports/`.

Nhóm tự chọn bài toán và thu thập dữ liệu phù hợp; repo không cung cấp dữ liệu mẫu.

## Sản phẩm phải nộp

- Repository nhóm chạy được.
- Tối thiểu 3 tài liệu chính sách và 5 bài viết/page do nhóm tự thu thập.
- Pipeline: convert → chunk → index → dense + BM25 → RRF → fallback → generation có citation.
- Chatbot Streamlit hiển thị câu trả lời và nguồn đã dùng.
- Golden dataset tối thiểu 15 câu; đánh giá 4 metric và so sánh A/B.
- `group_project/evaluation/RESULT.md`.
- Mỗi thành viên nộp báo cáo cá nhân theo template trong `reports/INDIVIDUAL_REPORT.md`.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
cp .env.example .env            # Windows PowerShell: Copy-Item .env.example .env
```

Mặc định project dùng embedding hashing và extractive generation để chạy offline. Muốn dùng câu trả lời tự nhiên hơn, đổi `LLM_PROVIDER` sang `gemini`, `openai` hoặc `anthropic` và điền API key tương ứng. Không commit `.env`.

Các backend nặng được tách thành extras để setup cơ bản không phải tải browser/model không dùng đến:

```bash
pip install -e ".[providers,vector,local-embedding,conversion,evaluation,crawl]"
```

```bash
# 1. Thu thập và chuẩn hoá
python -m src.task1_collect_legal_docs
python -m src.task2_crawl_news
python -m src.task3_convert_markdown

# 2. Index và kiểm tra contract
python -m src.task4_chunking_indexing
pytest -q

# 3. Chạy sản phẩm
streamlit run app.py

# 4. Chạy lại A/B evaluation và sinh báo cáo
python -m src.calibrate_threshold
python -m src.evaluate

# 5. Bonus: BGE reranker vs RRF và conversation memory (cần extra local-embedding)
python -m src.evaluate_bonus
```

Bonus đã triển khai:

- **BGE-M3 reranker** (`src/bge_reranking.py`): RRF lấy top-10 rồi chấm lại bằng cosine embedding `BAAI/bge-m3` (đa ngôn ngữ). Bật trong chatbot bằng `RERANKER=bge`.
- **Conversation memory** (`src/conversation_memory.py`): viết lại câu follow-up thành câu hỏi độc lập (LLM khi dùng provider API, heuristic khi offline). Bật/tắt trong sidebar Streamlit.

Kết quả đo của cả hai nằm ở mục *Bonus experiments* trong `group_project/evaluation/RESULT.md`.

`src.evaluate` là evaluator offline, deterministic. Để chạy bốn metric bằng Ragas + Gemini (có phát sinh API calls), cài `.[evaluation,providers]`, cấu hình `GEMINI_API_KEY`, rồi chạy `python -m src.evaluate_ragas`.

Nếu host nguồn tạm thời không truy cập được, Task 1–2 tạo source snapshot có URL gốc để pipeline và bài demo vẫn tái lập được. Khi có mạng, chạy lại hai task để làm mới dữ liệu.

## Kiến trúc

1. Task 1–3 thu thập PDF/page và chuẩn hóa về Markdown có frontmatter.
2. Task 4 chunk, embedding và upsert. ChromaDB được dùng khi đã cài; JSON cosine store là backend offline dự phòng.
3. Task 5–7 chạy dense, BM25 và Reciprocal Rank Fusion trên cùng corpus.
4. Task 8–9 thử PageIndex khi dense score dưới threshold; lỗi provider tự hạ cấp về hybrid.
5. Task 10 reorder context, gọi provider đã chọn và trả `GenerationResult` có nguồn.
6. `src.evaluate` so sánh dense-only với hybrid + RRF trên 15 golden cases.

## Lộ trình 3 giờ

| Mốc                  | Thời gian | Kết quả cần có                           |
| -------------------- | --------: | ---------------------------------------- |
| 0. Setup             |   10 phút | Môi trường và `.env` sẵn sàng            |
| 1. Data              |   25 phút | ≥3 legal, ≥5 news, Markdown đã chuẩn hoá |
| 2. Index & search    |   30 phút | ChromaDB, dense search và BM25 chạy được |
| 3. Fusion & fallback |   25 phút | RRF và fallback tuân thủ contract        |
| 4. Generation & UI   |   30 phút | Chatbot trả lời có citation              |
| 5. Evaluation        |   30 phút | 15+ Q&A, 4 metric, A/B comparison        |
| 6. Demo & handoff    |   30 phút | Test, report, demo và push repository    |

## Lưu ý quy tắc để có code quality tốt:

- Dense và BM25 nên cùng trả về `SearchResult` theo một schema.
- RRF chỉ nên dùng để gộp thứ hạng và chỉ chạy một lần.
- Fallback dùng cosine score gốc của dense retrieval.
- Threshold phải được hiệu chỉnh trên query in domain và out of domain, không có một con số đúng cho mọi corpus.

## Tài liệu

- [Module contracts](docs/MODULE_CONTRACTS.md): schema, interface và invariant mà code/test nên tuân theo.
- [Step-by-step guide](docs/STEP_BY_STEP.md): thứ tự triển khai và tiêu chí hoàn thành từng bước.
- [Grading rubric](docs/GRADING_RUBRIC.md): Rubric thang điểm.
- [Individual report](reports/INDIVIDUAL_REPORT.md): template báo cáo cá nhân.
- [Evaluation result](group_project/evaluation/RESULT.md): kết quả A/B đã chạy.
- [Data sources](data/SOURCES.md): nguồn gốc và phạm vi corpus.
- [Suggested topics](docs/SUGGESTED_TOPICS.md): danh sách chủ đề tham khảo, không bắt buộc.

## Kiểm tra

```bash
# Contract tests
pytest tests/test_contracts.py -q

# Acceptance tests
pytest tests/test_acceptance.py -q

# Toàn bộ
pytest -q
```
