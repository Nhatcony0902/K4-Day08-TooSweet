# Individual contribution report — Lê Thanh Tình

**Nhóm:** TooSweet

## Thông tin

- Họ và tên: Lê Thanh Tình
- Mã học viên: 2A202602449
- Vai trò: Trưởng nhóm (Lead)
- Nhóm: RAG Pipeline — Dịch vụ sinh viên HUST
- Repository/branch: `K4-DAY08-TooSweet`, `main`

## Phần việc đã thực hiện

| Module/deliverable | Phạm vi phụ trách | File/bằng chứng | Trạng thái |
|---|---|---|---|
| Kiến trúc và tích hợp | Chốt contract, dependency order và review các module | `docs/`, `src/contracts.py`, commit `39e07c8` | Done |
| Chatbot | Tích hợp generation, session state và hiển thị nguồn | `app.py`, commit `39e07c8` | Done |
| Evaluation | Golden dataset, threshold calibration và A/B report | `src/evaluate.py`, `src/calibrate_threshold.py`, `group_project/evaluation/`, commit `39e07c8` | Done |
| QA và bàn giao | Test, README, secret scan và demo checklist | `tests/`, `README.md`, `reports/`, commit `39e07c8` | Done |

## Quyết định kỹ thuật cần có khả năng giải thích

1. Giữ offline baseline để demo tái lập được, đồng thời tách Chroma, provider API và Ragas thành optional extras.
2. So sánh dense-only và hybrid + RRF trên cùng golden dataset, generator, evaluator và `top_k`.

## Kiểm thử và kết quả chung

- Contract và acceptance tests: 20/20 pass.
- Streamlit smoke test: không có exception.
- Threshold hiện tại: 0.4115; hybrid + RRF tốt hơn dense-only trong evaluation offline gần nhất.

## Xác nhận

Các module trên được đối chiếu trong commit tích hợp chung `39e07c8`. Trưởng nhóm xác nhận phân công, kết quả tích hợp và khả năng chạy lại trong buổi demo.

- Ngày: 25/09/2026
- Chữ ký/xác nhận: Lê Thanh Tình
