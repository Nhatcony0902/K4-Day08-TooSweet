# Individual contribution report — Phạm Long Nhật

**Nhóm:** TooSweet

## Thông tin

- Họ và tên: Phạm Long Nhật
- Mã học viên: 2A202602844
- Nhóm: RAG Pipeline — Dịch vụ sinh viên HUST
- Repository/branch: `K4-DAY08-TooSweet`, `main`

## Phần việc đã thực hiện

| Module/deliverable | Phạm vi phụ trách | File/bằng chứng | Trạng thái |
|---|---|---|---|
| RRF | Hợp nhất dense và BM25 theo rank | `src/task7_reranking.py`, commit `39e07c8` | Done |
| PageIndex fallback | Upload cache, API parsing và graceful fallback | `src/task8_pageindex_vectorless.py`, commit `39e07c8` | Done |
| Retrieval pipeline | Threshold, fusion một lần và provider failure | `src/task9_retrieval_pipeline.py`, commit `39e07c8` | Done |
| Generation | Reorder, context, citation và safe refusal | `src/task10_generation.py`, commit `39e07c8` | Done |

## Quyết định kỹ thuật cần có khả năng giải thích

1. Fallback dùng dense cosine score gốc, không dùng RRF score vì hai thang điểm khác nhau.
2. Citation phải ánh xạ về đúng thứ tự `sources`; query ngoài domain phải safe-refuse.

## Kiểm thử liên quan

- Kiểm tra RRF chỉ chạy một lần và deduplicate theo ID.
- Kiểm tra provider lỗi không làm pipeline crash; câu ngoài domain không tạo câu trả lời không có bằng chứng.

## Xác nhận

Các module trên được đối chiếu trong commit tích hợp chung `39e07c8`. Thành viên xác nhận nội dung phản ánh đúng phần việc phụ trách và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 25/09/2026
- Chữ ký/xác nhận: Phạm Long Nhật
