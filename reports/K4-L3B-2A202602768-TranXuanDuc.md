# Individual contribution report — Trần Xuân Đức

**Nhóm:** TooSweet

## Thông tin

- Họ và tên: Trần Xuân Đức
- Mã học viên: 2A202602768
- Nhóm: RAG Pipeline — Dịch vụ sinh viên HUST
- Repository/branch: `K4-DAY08-TooSweet`, `main`

## Ownership đề xuất

| Module/deliverable | Phạm vi phụ trách | File/bằng chứng cần xác nhận | Trạng thái |
|---|---|---|---|
| Contract dữ liệu | Document, SearchResult và validation | `src/contracts.py` | Cần xác nhận commit |
| Chunking/indexing | Stable ID, embedding, persistent upsert | `src/task4_chunking_indexing.py` | Cần xác nhận commit |
| Dense retrieval | Cosine similarity và output contract | `src/task5_semantic_search.py` | Cần xác nhận commit |
| BM25 retrieval | Tokenization và cùng corpus với dense | `src/task6_lexical_search.py` | Cần xác nhận commit |

## Quyết định kỹ thuật cần có khả năng giải thích

1. Dense và BM25 phải sử dụng cùng tập chunk và stable ID để RRF hợp nhất chính xác.
2. Có backend hashing/JSON offline; Chroma và SentenceTransformer được hỗ trợ qua optional extras.

## Kiểm thử liên quan

- Kiểm tra chunk không rỗng, ID duy nhất và metadata được giữ nguyên.
- Kiểm tra dense/BM25 trả kết quả đúng schema, không trùng và sắp xếp giảm dần.

## Xác nhận

Thành viên cần cập nhật mã học viên, commit/PR thực tế và xác nhận nội dung trước khi nộp.

- Ngày: 25/09/2026
- Chữ ký/xác nhận: Trần Xuân Đức
