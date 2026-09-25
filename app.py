import streamlit as st

from src.config import load_dotenv
from src.task10_generation import generate_with_citation


load_dotenv()

st.set_page_config(
    page_title="Trợ lý sinh viên HUST",
    page_icon="🎓",
    layout="wide",
)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("Trợ lý sinh viên HUST")
    st.caption("Tra cứu quy chế đào tạo, học phí, học bổng và dịch vụ sinh viên.")
    top_k = st.slider("Số chunks", 3, 10, 5)
    if st.button("Xóa hội thoại"):
        st.session_state.messages = []
        st.rerun()

st.title("🎓 Trợ lý dịch vụ sinh viên HUST")
st.caption("Câu trả lời chỉ dựa trên nguồn công khai đã thu thập. Hãy kiểm tra nguồn trước khi quyết định.")


def render_sources(sources: list[dict], retrieval_source: str) -> None:
    if not sources:
        return
    with st.expander(f"Nguồn tham khảo · {retrieval_source}"):
        for index, source in enumerate(sources, 1):
            metadata = source["metadata"]
            title = metadata.get("title") or metadata.get("source")
            url = metadata.get("url")
            st.markdown(f"**S{index}. {title}**")
            if url:
                st.markdown(f"[Mở nguồn gốc]({url})")
            st.caption(f"Phương thức: {source['retrieval_method']} · Score: {source['score']:.4f}")
            st.text(source["content"][:500] + ("…" if len(source["content"]) > 500 else ""))

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        render_sources(message.get("sources", []), message.get("retrieval_source", "none"))

query = st.chat_input("Nhập câu hỏi...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm trong tài liệu…"):
            result = generate_with_citation(query, top_k)
        st.markdown(result["answer"])
        render_sources(result["sources"], result["retrieval_source"])

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"],
        "retrieval_source": result["retrieval_source"],
    })
