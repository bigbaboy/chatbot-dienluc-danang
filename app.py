from __future__ import annotations
import logging
import streamlit as st
from config import (
    GROQ_KEY_OK,
    LLM_FREQUENCY_PENALTY,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_TEMPERATURE,
)
from db_manager import faiss_db_exists, load_faiss_db
from sidebar import render as render_sidebar
from tabs import chat, docs, solar, tieu_thu, tien_dien
from ui_helpers import init_session_state, load_css


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s · %(name)s · %(levelname)s · %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


st.set_page_config(
    page_title="Chatbot Điện lực Đà Nẵng",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)
load_css("styles.css")

@st.cache_resource
def init_system():

    if not faiss_db_exists():
        return None, None

    try:
        db = load_faiss_db()
        if not GROQ_KEY_OK:
            return db, None

        from langchain_groq import ChatGroq
        llm = ChatGroq(
            model_name=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            model_kwargs={"frequency_penalty": LLM_FREQUENCY_PENALTY},
        )
        return db, llm
    except Exception as exc:
        logger.exception("Lỗi khởi tạo hệ thống")
        st.error(f"Lỗi khởi tạo hệ thống: {exc}")
        return None, None


vector_db, llm = init_system()

init_session_state()
render_sidebar(vector_db, llm)

st.title("Chatbot Hỗ trợ Khách hàng — Điện lực Đà Nẵng")
st.markdown(
    '<p style="color:#64748b;font-size:14px;margin-top:-0.5rem;">'
    'Tra cứu quy định · Tính tiền điện · Phân tích tiêu thụ · '
    'Điện mặt trời</p>',
    unsafe_allow_html=True,
)
st.divider()

tab_chat, tab_electric, tab_analytic, tab_solar, tab_docs = st.tabs([
    "Trợ lý Pháp lý (RAG)",
    "Tính tiền điện",
    "Phân tích Tiêu thụ",
    "Điện Mặt Trời",
    "Quản lý Tài liệu",
])

with tab_chat:
    chat.render(vector_db, llm)

with tab_electric:
    tien_dien.render(llm)

with tab_analytic:
    tieu_thu.render(llm)

with tab_solar:
    solar.render()

with tab_docs:
    docs.render(vector_db, init_system)
