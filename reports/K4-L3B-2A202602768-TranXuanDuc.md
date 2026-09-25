# Individual contribution report — Trần Xuân Đức

**Nhóm:** TooSweet

## Thông tin

- Họ và tên: Trần Xuân Đức
- Mã học viên: 2A202602768
- Nhóm: RAG Pipeline — Dịch vụ sinh viên HUST
- Repository/branch: `K4-DAY08-TooSweet`, `main`

## Phần việc đã thực hiện

| Module/deliverable | Phạm vi phụ trách | File/bằng chứng | Trạng thái |
|---|---|---|---|
| Contract dữ liệu | Document, SearchResult và validation | `src/contracts.py`, commit `39e07c8` | Done |
| Chunking/indexing | Stable ID, embedding, persistent upsert | `src/task4_chunking_indexing.py`, commit `39e07c8` | Done |
| Dense retrieval | Cosine similarity và output contract | `src/task5_semantic_search.py`, commit `39e07c8` | Done |
| BM25 retrieval | Tokenization và cùng corpus với dense | `src/task6_lexical_search.py`, commit `39e07c8` | Done |

## Quyết định kỹ thuật cần có khả năng giải thích

1. Dense và BM25 phải sử dụng cùng tập chunk và stable ID để RRF hợp nhất chính xác.
2. Có backend hashing/JSON offline; Chroma và SentenceTransformer được hỗ trợ qua optional extras.

## Kiểm thử liên quan

- Kiểm tra chunk không rỗng, ID duy nhất và metadata được giữ nguyên.
- Kiểm tra dense/BM25 trả kết quả đúng schema, không trùng và sắp xếp giảm dần.

## Xác nhận

Các module trên được đối chiếu trong commit tích hợp chung `39e07c8`. Thành viên xác nhận nội dung phản ánh đúng phần việc phụ trách và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 25/09/2026
- Chữ ký/xác nhận: Trần Xuân Đức
