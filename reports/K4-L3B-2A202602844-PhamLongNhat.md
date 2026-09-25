# Individual contribution report — Phạm Long Nhật

**Tên nhóm:** TooSweet

**Repository:** `K4-DAY08-TooSweet`

## Thông tin

- Họ và tên: Phạm Long Nhật
- Mã học viên: 2A202602844
- Nhóm: TooSweet
- Repository/branch: `K4-DAY08-TooSweet`, `main`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| RRF (Task 7) | Cài đặt `rerank_rrf`: điểm `1/(k+rank)` với `k=60`, deduplicate theo ID trong từng list, tie-break theo best rank rồi ID, gắn `retrieval_method="hybrid"` | `src/task7_reranking.py`, commit `39e07c8` | Done |
| PageIndex fallback (Task 8) | Upload PDF lên PageIndex, cache `doc_id` theo kích thước file để không upload lại, parse citations thành `SearchResult` với `retrieval_method="pageindex"`, có timeout cho mọi request | `src/task8_pageindex_vectorless.py`, commit `39e07c8` | Partial — code xong nhưng chưa chạy live vì chưa có `PAGEINDEX_API_KEY` |
| Retrieval pipeline (Task 9) | Chạy dense + BM25, fuse RRF đúng một lần, so threshold với dense cosine gốc, gọi fallback và bắt lỗi provider để trả hybrid | `src/task9_retrieval_pipeline.py`, commit `39e07c8` | Done |
| Generation (Task 10) | Reorder chống lost-in-the-middle nhưng giữ citation index gốc, context có title/source/URL, dispatch OpenAI/Gemini/Anthropic/extractive, kiểm tra evidence và citation hợp lệ, safe refusal | `src/task10_generation.py`, commit `39e07c8` | Done |

| Generation bằng Gemini | Chatbot dùng `gemini-2.5-flash`; thêm override model và retry khi bị rate limit trong `call_llm`; A/B generator extractive vs Gemini trên 15 golden cases | `src/task10_generation.py`, `src/evaluate.py`, `RESULT.md` Bonus mục 3 | Done |
| Bonus: BGE-M3 rerank | Chấm lại top-10 của RRF bằng cosine `BAAI/bge-m3`, bật bằng `RERANKER=bge`; A/B với RRF | `src/bge_reranking.py`, `src/evaluate_bonus.py`, `RESULT.md` Bonus mục 1 | Done — kết quả âm, có phân tích |
| Bonus: conversation memory | Viết lại câu follow-up (LLM `gemini-2.5-flash-lite`, heuristic khi offline), tích hợp Streamlit; đo trên 6 hội thoại follow-up | `src/conversation_memory.py`, `app.py`, `followup_dataset.json`, `RESULT.md` Bonus mục 2 | Done |

Ghi chú: toàn bộ code nhóm được tích hợp và push trong một commit chung `39e07c8` (tài khoản Nguyễn Tiến Lượng), nên phần của tôi được đối chiếu theo file ownership ở trên và các test tương ứng bên dưới.

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Fallback PageIndex dựa trên dense cosine score gốc (`dense[0]["score"]`), không dùng RRF score.
   **Lý do/evidence:** RRF score chỉ phản ánh thứ hạng (tối đa ~2/61 ≈ 0.033), không cùng thang với cosine nên không thể so với threshold. Threshold `0.4115` được calibrate trên 8 query in-domain và 8 query out-of-domain (`group_project/evaluation/threshold_calibration.json`), balanced accuracy 0.9375. Test `test_retrieve_uses_dense_score_for_fallback` kiểm tra điều này.
   **Trade-off:** Dense dùng hashing embedding nên một số câu in-domain diễn đạt khác từ khóa vẫn rơi dưới threshold (vd. "Cách đăng ký ký túc xá an toàn?" = 0.378) và bị đẩy sang fallback không cần thiết.

2. **Quyết định:** Sau khi reorder, citation vẫn dùng số thứ tự gốc (`_citation_index`), và câu trả lời bị thay bằng safe refusal nếu không có citation hoặc citation `[Sn]` vượt quá số nguồn.
   **Lý do/evidence:** Reorder đầu–cuối làm đổi vị trí chunk; nếu đánh số theo vị trí mới thì `[S2]` trong answer sẽ không map đúng `sources[1]`. Test `test_reorder_is_non_mutating_and_context_contains_source` kiểm tra reorder không làm mất ID.
   **Trade-off:** Kiểm tra chặt làm tăng tỉ lệ từ chối khi LLM quên gắn citation, đổi lại không trả về khẳng định không có nguồn.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng:
  - `pytest tests/test_contracts.py -k "rrf or reorder or retrieve or generation"` → 6 passed (RRF, reorder, fallback theo dense score, fuse đúng một lần, sống sót khi provider lỗi, validator safe refusal). Toàn bộ suite: 20/20 pass.
  - Query đúng domain: "Thời gian nghỉ học dài hạn tối đa là bao nhiêu học kỳ?" → trả lời "tối đa bốn học kỳ [S1]", nguồn `quy_che_dao_tao_tin_chi_hust.pdf`, `retrieval_source="hybrid"`.
  - Query ngoài domain: "Giá vé máy bay đi Tokyo bao nhiêu?" → safe refusal, `sources=[]`.
- Kết quả trước/sau nếu có (`group_project/evaluation/RESULT.md`):
  - Hybrid + RRF đạt trung bình 0.785, dense-only 0.776; context precision 0.893 → 0.920.
  - Gemini so với extractive: answer relevance 0.327 → 0.512, faithfulness lexical 0.944 → 0.859 (Gemini diễn đạt lại nên bị metric lexical phạt).
  - BGE-M3 rerank so với RRF: trung bình 0.785 → 0.765. BGE-M3 loại 22 chunk legal khỏi top-5 vì Markdown legal không có dấu.
  - Memory: context recall của câu follow-up 0.928 → 0.964 (LLM rewrite), 0.943 (heuristic).
- Lỗi/rủi ro đã xử lý: reorder có thể làm citation lệch nguồn → gán `_citation_index` trước khi reorder. Provider fallback/LLM lỗi có thể làm crash pipeline → bọc `try/except`, trả hybrid results hoặc safe refusal.
- Lỗi phát hiện khi làm bonus: ChromaDB trên máy chưa được index nên dense search trả rỗng, hybrid thực chất chỉ chạy BM25 → chạy lại Task 4 (24 chunks), điểm offline khớp lại số đã commit. Heuristic memory bỏ dấu làm "nợ" bị nhận nhầm là "nó" → so khớp từ nối có dấu. Gemini free tier chỉ 20 request/ngày cho mỗi model → A/B retrieval giữ generator extractive, bước gọi LLM có cache và dừng ngay khi hết quota ngày.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: các metric vẫn đo bằng lexical overlap nên chưa đánh giá đúng câu trả lời Gemini diễn đạt lại; BGE-M3 rerank chưa có lợi khi dữ liệu legal không dấu và chậm (~8 s/query trên CPU); PageIndex fallback chưa được kiểm chứng với API thật.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: convert lại PDF gốc có dấu rồi đo lại BGE-M3 rerank, và chạy `src.evaluate_ragas` khi có quota Gemini.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 25/09/2026
- Tên thành viên: Phạm Long Nhật
