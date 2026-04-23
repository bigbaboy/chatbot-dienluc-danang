from __future__ import annotations

import html
from datetime import datetime

import streamlit as st

from config import CONFIDENCE_HIGH, CONFIDENCE_MED
from rag_pipeline import tra_loi_rag

QUICK_QUESTIONS = [
    "Giấy tờ cần thiết để cấp điện sinh hoạt?",
    "Thủ tục đăng ký tăng công suất?",
    "Quy định về hợp đồng mua bán điện?",
    "Cách tính tiền điện bậc thang?",
    "Xử lý khi bị cắt điện đột xuất?",
    "Hướng dẫn đăng ký điện mặt trời mái nhà?",
]

# Ngưỡng % confidence để chọn màu badge (nhân 100 từ ngưỡng trong config)
CONFIDENCE_HIGH_PCT = int(CONFIDENCE_HIGH * 100)
CONFIDENCE_MED_PCT = int(CONFIDENCE_MED * 100)


def _render_confidence_badge(conf: float) -> None:
    pct = int(conf * 100)
    if conf >= CONFIDENCE_HIGH:
        color, bg, label = "#15803d", "#dcfce7", f"Độ tin cậy cao ({pct}%)"
    elif conf >= CONFIDENCE_MED:
        color, bg, label = "#b45309", "#fef9c3", f"Độ tin cậy trung bình ({pct}%)"
    else:
        color, bg, label = "#b91c1c", "#fee2e2", f"Thông tin hạn chế ({pct}%)"

    st.markdown(
        f'<span style="display:inline-flex;align-items:center;gap:5px;'
        f'background:{bg};color:{color};font-size:11px;font-weight:600;'
        f'padding:2px 10px;border-radius:999px;margin-top:4px">● {label}</span>',
        unsafe_allow_html=True,
    )


def _render_citations(citations: list) -> None:
    if not citations:
        return
    with st.expander(f"Nguồn tham khảo ({len(citations)} tài liệu)"):
        for c in citations:
            sc = c.get("score", 0)
            if sc >= CONFIDENCE_HIGH_PCT:
                score_color, score_bg = "#15803d", "#dcfce7"
            elif sc >= CONFIDENCE_MED_PCT:
                score_color, score_bg = "#b45309", "#fef9c3"
            else:
                score_color, score_bg = "#b91c1c", "#fee2e2"

            # Escape HTML trong data do user/PDF cung cấp
            src_safe = html.escape(str(c["src"]))
            page_safe = html.escape(str(c["page"]))
            snippet_safe = html.escape(str(c["snippet"]))
            idx_safe = html.escape(str(c["i"]))

            st.markdown(
                f'<div class="citation-card">'
                f'<strong>[{idx_safe}] {src_safe}</strong> — Trang {page_safe}'
                f'&nbsp;&nbsp;<span style="display:inline-block;background:{score_bg};'
                f'color:{score_color};font-size:11px;font-weight:600;'
                f'padding:1px 8px;border-radius:999px">{sc}%</span><br>'
                f'<span style="color:#475569;font-size:12px">{snippet_safe}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


def render(vector_db, llm) -> None:
    st.markdown("""
    <div style="background:linear-gradient(135deg,#0ea5a0,#0369a1);
                border-radius:12px;padding:16px 20px;margin-bottom:16px;
                display:flex;align-items:center;gap:12px">
        <span style="font-size:28px">⚡</span>
        <div>
            <div style="color:white;font-size:17px;font-weight:700;line-height:1.2">
                Trợ lý Hỗ trợ Khách hàng
            </div>
            <div style="color:#bae6fd;font-size:12px">
                Hỏi đáp quy định · Điện lực Đà Nẵng
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if vector_db is None or llm is None:
        st.warning(
            "Hệ thống RAG chưa sẵn sàng. Kiểm tra:\n"
            "- Vector Database (`faiss_dienluc_db/`) đã được tạo chưa? "
            "Nếu chưa, chạy: `python tao_vector_db.py`\n"
            "- API key Groq đã được cấu hình trong file `.env` chưa?"
        )

    # Câu hỏi gợi ý — chỉ hiện khi chưa có tin nhắn nào
    if not st.session_state.messages:
        st.markdown(
            '<div style="color:#64748b;font-size:13px;margin-bottom:6px">'
            'Bạn có thể hỏi về:</div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(3)
        for idx, q in enumerate(QUICK_QUESTIONS):
            if cols[idx % 3].button(q, key=f"chip_{idx}", use_container_width=True):
                st.session_state["_pending_question"] = q
                st.rerun()

    # Hiển thị toàn bộ lịch sử chat
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                conf = msg.get("confidence")
                if conf is not None:
                    _render_confidence_badge(conf)
                _render_citations(msg.get("citations", []))

    # Xử lý câu hỏi mới
    cau_hoi = st.chat_input("Nhập câu hỏi của bạn...")
    if st.session_state.get("_pending_question"):
        cau_hoi = st.session_state.pop("_pending_question")

    if cau_hoi:
        st.session_state.messages.append({
            "role": "user",
            "content": cau_hoi,
            "citations": [],
            "time": datetime.now().strftime("%H:%M"),
        })

        lich_su_truoc = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
        ]

        # Đính kèm hồ sơ khách hàng nếu đã lưu
        p = st.session_state
        if p.profile_so_nguoi or p.profile_loai_nha:
            ten_prefix = f"Khách hàng: {p.profile_ten}. " if p.profile_ten else ""
            cau_hoi_day_du = (
                f"{ten_prefix}[Hộ {p.profile_so_nguoi} người, {p.profile_loai_nha}, "
                f"khu vực {p.profile_khu_vuc}] {cau_hoi}"
            )
        else:
            cau_hoi_day_du = cau_hoi

        with st.spinner("Đang tìm kiếm trong cơ sở dữ liệu..."):
            tra_loi, citations, confidence = tra_loi_rag(
                vector_db, llm, cau_hoi_day_du, lich_su_truoc
            )

        st.session_state.messages.append({
            "role": "assistant",
            "content": tra_loi,
            "citations": citations,
            "confidence": float(confidence),
            "time": datetime.now().strftime("%H:%M"),
        })
        st.rerun()
