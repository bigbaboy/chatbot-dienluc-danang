from __future__ import annotations
import logging
from typing import List, Optional, Tuple
from config import (
    CONFIDENCE_MIN_RELEVANCE,
    HISTORY_TEMPLATE,
    SEARCH_FETCH_K,
    SEARCH_TOP_K,
    SYSTEM_PROMPT,
)
from utils import dinh_dang_tien, tinh_confidence, tinh_tien_dien, trich_kwh_tu_cau_hoi

logger = logging.getLogger(__name__)

# Constants — đặt tên cho magic numbers
MAX_HISTORY_MESSAGES = 6      # Số tin nhắn gần nhất đưa vào context của LLM
SNIPPET_LENGTH = 150          # Số ký tự hiển thị trong citation card
EMPTY_ANSWER_FALLBACK = (
    "Hệ thống không nhận được câu trả lời từ AI. "
    "Vui lòng thử lại hoặc đặt câu hỏi rõ ràng hơn."
)
RATE_LIMIT_MESSAGE = (
    "⏱️ Đã hết lượt gọi AI miễn phí tạm thời. Vui lòng thử lại sau 1 phút."
)


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "rate limit" in msg or "429" in msg


def _format_cau_tra_loi_tinh_tien(kwh: float) -> str:
    chi_tiet, truoc_vat, vat, tong = tinh_tien_dien(kwh)

    bac_lines = []
    for b in chi_tiet:
        if b["sl"] <= 0:
            continue
        khoang = (
            f"trên {b['tu']} kWh" if b["den"] == "trở lên"
            else f"{b['tu']}–{b['den']} kWh"
        )
        bac_lines.append(
            f"- **Bậc {b['bac']}** ({khoang}): "
            f"{b['sl']:.0f} kWh × {b['don_gia']:,} đ = {int(b['tt']):,} đ"
        )

    return (
        f"**Tiền điện cho {kwh:.0f} kWh** _(theo QĐ 1279/QĐ-BCT ngày 09/05/2025)_:\n\n"
        + "\n".join(bac_lines)
        + f"\n\n- Cộng (trước VAT): {dinh_dang_tien(truoc_vat)}"
        + f"\n- VAT 8%: {dinh_dang_tien(vat)}"
        + f"\n- **Tổng phải trả: {dinh_dang_tien(tong)}**"
        + "\n\n💡 _Để xem biểu đồ, so sánh tách hộ và xuất hóa đơn HTML, "
        "hãy chuyển sang tab **'Tính tiền điện'** ở phía trên._"
    )


def _build_context(docs) -> str:
    return "\n\n".join(
        f"[Nguồn: {d.metadata.get('source_file', '?')} - "
        f"Trang {d.metadata.get('page', '?')}]\n{d.page_content}"
        for d in docs
    )


def _build_history_section(lich_su: Optional[list]) -> str:
    if not lich_su:
        return ""
    recent = lich_su[-MAX_HISTORY_MESSAGES:]
    lines = [
        f"{'Khách hàng' if m['role'] == 'user' else 'Trợ lý'}: {m['content']}"
        for m in recent
    ]
    return HISTORY_TEMPLATE.format(history="\n".join(lines))


def _build_citations(top_docs: List[Tuple]) -> List[dict]:
    citations = []
    for i, (doc, score) in enumerate(top_docs, 1):
        snippet = (
            (doc.page_content[:SNIPPET_LENGTH] + "...")
            if doc.page_content
            else "Không có nội dung."
        )
        citations.append({
            "i": i,
            "src": doc.metadata.get("source_file", "Tài liệu EVN"),
            "page": doc.metadata.get("page", "?"),
            "snippet": snippet,
            "score": int(round(score * 100)),
        })
    return citations


def tra_loi_rag(
    vector_db,
    llm,
    cau_hoi: str,
    lich_su: Optional[list] = None,
) -> Tuple[str, List[dict], float]:

    if vector_db is None or llm is None:
        return (
            "Hệ thống RAG chưa sẵn sàng. Vui lòng kiểm tra Vector Database và API key.",
            [],
            0.0,
        )

    # Fast-path: câu hỏi tính tiền điện
    kwh_phat_hien = trich_kwh_tu_cau_hoi(cau_hoi)
    if kwh_phat_hien is not None:
        logger.info("Fast-path tính tiền: %s kWh", kwh_phat_hien)
        return _format_cau_tra_loi_tinh_tien(kwh_phat_hien), [], 1.0

    try:
        # Bước 1: Retrieve
        raw = vector_db.similarity_search_with_score(cau_hoi, k=SEARCH_FETCH_K)

        # Bước 2-3: Chuyển điểm, lọc, sắp xếp lại
        ranked = [
            (doc, tinh_confidence(l2_sq))
            for doc, l2_sq in raw
            if tinh_confidence(l2_sq) >= CONFIDENCE_MIN_RELEVANCE
        ]
        ranked.sort(key=lambda x: x[1], reverse=True)

        # Bước 4: Giữ top-k
        top_docs = ranked[:SEARCH_TOP_K]
        if not top_docs:
            top_docs = [
                (doc, tinh_confidence(l2_sq)) for doc, l2_sq in raw[:SEARCH_TOP_K]
            ]

        # Bước 5: Confidence tổng thể
        confidence = (
            sum(s for _, s in top_docs) / len(top_docs) if top_docs else 0.0
        )

        # Build prompt
        docs = [doc for doc, _ in top_docs]
        prompt = SYSTEM_PROMPT.format(
            context=_build_context(docs),
            history_section=_build_history_section(lich_su),
            question=cau_hoi,
        )

        # Gọi LLM
        ket_qua = llm.invoke(prompt)
        answer_text = (ket_qua.content or "").strip() or EMPTY_ANSWER_FALLBACK

        return answer_text, _build_citations(top_docs), confidence

    except Exception as exc:
        logger.exception("Lỗi xử lý RAG cho câu hỏi: %s", cau_hoi[:100])
        if _is_rate_limit_error(exc):
            return RATE_LIMIT_MESSAGE, [], 0.0
        return f"Lỗi khi xử lý câu hỏi: {exc}", [], 0.0


def goi_ai_voi_xu_ly_loi(llm, prompt: str) -> str:
    if llm is None:
        return "Chưa kết nối được với AI. Vui lòng kiểm tra API key trong file .env."
    try:
        res = llm.invoke(prompt)
        return (res.content or "").strip() or EMPTY_ANSWER_FALLBACK
    except Exception as exc:
        logger.exception("Lỗi gọi AI tư vấn")
        if _is_rate_limit_error(exc):
            return RATE_LIMIT_MESSAGE
        return f"Lỗi kết nối AI: {exc}"
