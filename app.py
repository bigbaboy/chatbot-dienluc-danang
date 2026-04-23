"""
Chatbot Điện lực Đà Nẵng — Entry point Streamlit.

File này chỉ làm nhiệm vụ điều phối (orchestration):
  1. Cấu hình Streamlit, load CSS
  2. Khởi tạo Vector DB và LLM (có cache)
  3. Khởi tạo session state
  4. Vẽ sidebar + header + 6 tabs

Logic chi tiết của từng tab đã được tách ra module riêng trong thư mục `tabs/`.
Logic tính toán đã được tách ra `utils.py` (có 45 unit test).

Kiến trúc:
    app.py                  ← orchestrator (file này)
    config.py               ← hằng số tập trung (biểu giá, prompts, ...)
    utils.py                ← hàm tính toán thuần (pure functions)
    doc_pdf_smart.py        ← đọc PDF (PyMuPDF + LlamaParse fallback)
    db_manager.py           ← build / load FAISS
    rag_pipeline.py         ← retrieve → re-rank → LLM generate
    hoa_don.py              ← tạo hóa đơn HTML
    ui_helpers.py           ← load CSS, init session state
    sidebar.py              ← sidebar (hồ sơ, lịch sử, trạng thái)
    tabs/                   ← mỗi tab 1 file:
        chat.py             ← Tab 1: RAG chatbot
        tien_dien.py        ← Tab 2: Tính tiền điện bậc thang
        tieu_thu.py         ← Tab 3: Phân tích tiêu thụ
        solar.py            ← Tab 4: Điện mặt trời
        roi.py              ← Tab 5: ROI thay thiết bị
        docs.py             ← Tab 6: Quản lý tài liệu
    test_tinh_toan.py       ← pytest (55+ tests)
    tao_vector_db.py        ← CLI build FAISS từ data/
"""

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
from tabs import chat, docs, roi, solar, tieu_thu, tien_dien
from ui_helpers import init_session_state, load_css

# ─── Logging cấu hình ở cấp app ─────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s · %(name)s · %(levelname)s · %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# CẤU HÌNH TRANG STREAMLIT
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Chatbot Điện lực Đà Nẵng",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)
load_css("styles.css")


# ══════════════════════════════════════════════════════════════════
# KHỞI TẠO HỆ THỐNG RAG (chỉ 1 lần, cache)
# ══════════════════════════════════════════════════════════════════
@st.cache_resource
def init_system():
    """
    Load Vector DB và khởi tạo LLM. Phân biệt 3 trường hợp:
      - Vector DB chưa build: return (None, None), im lặng
      - Lỗi thực sự (import fail, model lỗi...): show st.error
      - OK: return (db, llm) — llm có thể là None nếu GROQ_API_KEY thiếu
    """
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


# ══════════════════════════════════════════════════════════════════
# INIT SESSION STATE + SIDEBAR
# ══════════════════════════════════════════════════════════════════
init_session_state()
render_sidebar(vector_db, llm)


# ══════════════════════════════════════════════════════════════════
# HEADER + TABS
# ══════════════════════════════════════════════════════════════════
st.title("Chatbot Hỗ trợ Khách hàng — Điện lực Đà Nẵng")
st.markdown(
    '<p style="color:#64748b;font-size:14px;margin-top:-0.5rem;">'
    'Tra cứu quy định · Tính tiền điện · Phân tích tiêu thụ · '
    'Điện mặt trời · ROI thiết bị</p>',
    unsafe_allow_html=True,
)
st.divider()

tab_chat, tab_electric, tab_analytic, tab_solar, tab_roi, tab_docs = st.tabs([
    "Trợ lý Pháp lý (RAG)",
    "Tính tiền điện",
    "Phân tích Tiêu thụ",
    "Điện Mặt Trời",
    "Tư vấn Thiết bị",
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

with tab_roi:
    roi.render()

with tab_docs:
    docs.render(vector_db, init_system)
