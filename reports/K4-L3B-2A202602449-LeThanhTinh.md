# Individual contribution report — Lê Thanh Tình

**Nhóm:** TooSweet

## Thông tin

- Họ và tên: Lê Thanh Tình
- Mã học viên: 2A202602449
- Vai trò: Trưởng nhóm (Lead)
- Nhóm: RAG Pipeline — Dịch vụ sinh viên HUST
- Repository/branch: `K4-L3B-RAG-Pipeline`, `main`

## Ownership đề xuất

| Module/deliverable | Phạm vi phụ trách | File/bằng chứng cần xác nhận | Trạng thái |
|---|---|---|---|
| Kiến trúc và tích hợp | Chốt contract, dependency order và review các module | `docs/`, `src/contracts.py` | Cần xác nhận commit |
| Chatbot | Tích hợp generation, session state và hiển thị nguồn | `app.py` | Cần xác nhận commit |
| Evaluation | Golden dataset, threshold calibration và A/B report | `src/evaluate.py`, `src/calibrate_threshold.py`, `group_project/evaluation/` | Cần xác nhận commit |
| QA và bàn giao | Test, README, secret scan và demo checklist | `tests/`, `README.md`, `reports/` | Cần xác nhận commit |

## Quyết định kỹ thuật cần có khả năng giải thích

1. Giữ offline baseline để demo tái lập được, đồng thời tách Chroma, provider API và Ragas thành optional extras.
2. So sánh dense-only và hybrid + RRF trên cùng golden dataset, generator, evaluator và `top_k`.

## Kiểm thử và kết quả chung

- Contract và acceptance tests: 20/20 pass.
- Streamlit smoke test: không có exception.
- Threshold hiện tại: 0.4115; hybrid + RRF tốt hơn dense-only trong evaluation offline gần nhất.

## Xác nhận

Trưởng nhóm cần cập nhật mã học viên, commit/PR thực tế và xác nhận phân công của cả nhóm trước khi nộp.

- Ngày: 25/09/2026
- Chữ ký/xác nhận: Lê Thanh Tình
