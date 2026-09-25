# Individual contribution report — Nguyễn Tiến Lượng

**Nhóm:** TooSweet

## Thông tin

- Họ và tên: Nguyễn Tiến Lượng
- Mã học viên: 2A202602378
- Nhóm: RAG Pipeline — Dịch vụ sinh viên HUST
- Repository/branch: `K4-DAY08-TooSweet`, `main`

## Phần việc đã thực hiện

| Module/deliverable | Phạm vi phụ trách | File/bằng chứng | Trạng thái |
|---|---|---|---|
| Thu thập policy documents | Kiểm tra nguồn và lưu tài liệu gốc/snapshot | `src/task1_collect_legal_docs.py`, `data/landing/legal/`, commit `39e07c8` | Done |
| Crawl public pages | URL, metadata và source snapshot | `src/task2_crawl_news.py`, `data/landing/news/`, commit `39e07c8` | Done |
| Chuẩn hóa dữ liệu | Frontmatter, nội dung Markdown và chất lượng text | `src/task3_convert_markdown.py`, `data/standardized/`, commit `39e07c8` | Done |
| Quản lý nguồn | Ghi URL và phạm vi sử dụng | `data/SOURCES.md`, commit `39e07c8` | Done |

## Quyết định kỹ thuật cần có khả năng giải thích

1. Sử dụng source snapshot khi host không phản hồi để pipeline vẫn tái lập được, đồng thời giữ URL chính thức để đối chiếu.
2. Chuẩn hóa cả policy document và public page về cùng schema Markdown trước khi chunk.

## Kiểm thử liên quan

- Kiểm tra đủ 3 legal documents, 5 news JSON và 8 Markdown.
- Chạy `python -m src.task1_collect_legal_docs`, Task 2, Task 3 và acceptance tests.

## Xác nhận

Các module trên được đối chiếu trong commit tích hợp chung `39e07c8`. Thành viên xác nhận nội dung phản ánh đúng phần việc phụ trách và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 25/09/2026
- Chữ ký/xác nhận: Nguyễn Tiến Lượng
