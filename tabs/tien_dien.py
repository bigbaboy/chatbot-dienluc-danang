"""Tab 2 — Tính tiền điện bậc thang."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import BIEU_GIA_DIEN
from hoa_don import tao_hoa_don_html
from rag_pipeline import goi_ai_voi_xu_ly_loi
from utils import dinh_dang_tien, tinh_tiet_kiem_tach_ho, tinh_tien_dien

# Số hộ tối đa khi so sánh tách hộ
MAX_COMPARE_HO = 10
# Ngưỡng kWh còn lại để cảnh báo "sắp vượt bậc"
NGUONG_CANH_BAO_VUOT_BAC = 20


def _render_df_gia_bieu() -> pd.DataFrame:
    """Bảng biểu giá hiển thị trong UI."""
    return pd.DataFrame([
        {
            "Bậc": f"Bậc {bg['bac']}",
            "Khoảng": (
                f"{bg['tu']}–{bg['den']} kWh" if bg["den"] else f"Trên {bg['tu']} kWh"
            ),
            "Đơn giá": f"{bg['don_gia']:,} đ/kWh",
        }
        for bg in BIEU_GIA_DIEN
    ])


def _render_waterfall(
    bacs: list, tien_vat: float, tong_per_ho: float,
    kwh_per_ho: float, so_ho: int, tong_all: float,
) -> None:
    """Waterfall chart hiển thị cách tiền cộng dồn qua các bậc."""
    nhan = [
        (
            f"Bậc {b['bac']} ({b['tu']}–{b['den']} kWh)"
            if b["den"] != "trở lên"
            else f"Bậc {b['bac']} (trên {b['tu']} kWh)"
        )
        for b in bacs
    ] + ["VAT 8%", "Tổng/hộ"]
    gtri = [b["tt"] for b in bacs] + [tien_vat, tong_per_ho]
    do_do = ["relative"] * (len(bacs) + 1) + ["total"]

    title = (
        f"Chi tiết 1 hộ — {kwh_per_ho:.1f} kWh"
        + (f" (×{so_ho} hộ = {dinh_dang_tien(tong_all)})" if so_ho > 1 else "")
    )
    fig = go.Figure(go.Waterfall(
        orientation="v", measure=do_do, x=nhan, y=gtri,
        text=[dinh_dang_tien(v) for v in gtri], textposition="outside",
        connector={"line": {"color": "#cbd5e1"}},
        increasing={"marker": {"color": "#f97316"}},
        totals={"marker": {"color": "#0ea5a0"}},
    ))
    fig.update_layout(
        title=title, yaxis_title="Số tiền (đồng)", showlegend=False,
        height=350, plot_bgcolor="white", paper_bgcolor="white",
        margin={"t": 50, "b": 20, "l": 20, "r": 20},
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_canh_bao_vuot_bac(bacs: list) -> None:
    """Cảnh báo nếu còn ít kWh nữa là vượt sang bậc cao hơn."""
    if not bacs:
        return
    bac_hien = bacs[-1]
    bac_num = bac_hien["bac"]
    if bac_hien["den"] == "trở lên":
        st.info(
            f"📊 Đang ở **Bậc {bac_num}** (bậc cao nhất) — "
            f"{bac_hien['don_gia']:,} đ/kWh."
        )
        return

    con_lai = round(
        (bac_hien["den"] - bac_hien["tu"] + (0 if bac_hien["tu"] == 0 else 1))
        - bac_hien["sl"], 1
    )
    bac_tiep = next(
        (bg for bg in BIEU_GIA_DIEN if bg["bac"] == bac_num + 1), None
    )
    if bac_tiep and con_lai > 0:
        if con_lai <= NGUONG_CANH_BAO_VUOT_BAC:
            st.warning(
                f"⚠️ **Sắp vượt bậc!** Chỉ còn **{con_lai:.0f} kWh** nữa là sang "
                f"Bậc {bac_tiep['bac']} — giá tăng lên **{bac_tiep['don_gia']:,} đ/kWh**."
            )
        else:
            st.info(
                f"📊 Đang ở **Bậc {bac_num}** ({bac_hien['don_gia']:,} đ/kWh) "
                f"— còn **{con_lai:.0f} kWh** trước khi sang Bậc {bac_tiep['bac']} "
                f"({bac_tiep['don_gia']:,} đ/kWh)."
            )


def render(llm) -> None:
    """Vẽ toàn bộ Tab Tính tiền điện."""
    st.markdown("#### Tính tiền điện sinh hoạt bậc thang — Biểu giá 2025")
    col_l, col_r = st.columns([1, 1.5], gap="large")

    with col_l:
        kwh_input = st.number_input(
            "Tổng sản lượng điện tiêu thụ (kWh)",
            min_value=0.0, max_value=10000.0, value=250.0, step=10.0,
        )
        so_ho = st.number_input(
            "Số hộ gia đình",
            min_value=1, max_value=20, value=1, step=1,
            help=(
                "Mỗi hộ được tính bậc thang riêng biệt.\n"
                "Phòng trọ hoặc cơ sở kinh doanh có thể đăng ký nhiều hộ "
                "để giảm tiền điện (mỗi hộ tối đa 4 người theo quy định EVN)."
            ),
        )
        btn_calc = st.button("Tính tiền điện", type="primary")
        st.markdown("---")
        st.markdown("**Biểu giá bậc thang 2025** (theo QĐ 1279/QĐ-BCT)")
        st.table(_render_df_gia_bieu())

    with col_r:
        if not (btn_calc or kwh_input > 0):
            return

        kwh_per_ho = kwh_input / so_ho
        chi_tiet, truoc_vat_ho, tien_vat_ho, tong_per_ho = tinh_tien_dien(kwh_per_ho)
        tong_neu_1ho, tong_all, tiet_kiem, pct = tinh_tiet_kiem_tach_ho(kwh_input, so_ho)

        if so_ho > 1:
            pct_display = round(pct, 1)
            st.success(
                f"Tách **{so_ho} hộ** ({kwh_per_ho:.1f} kWh/hộ) tiết kiệm được "
                f"**{dinh_dang_tien(tiet_kiem)}** so với tính 1 hộ (giảm {pct_display}%)"
            )
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Tổng sản lượng", f"{kwh_input:.0f} kWh")
            c2.metric("Mỗi hộ", f"{kwh_per_ho:.1f} kWh",
                      delta=dinh_dang_tien(tong_per_ho))
            c3.metric(f"Tổng {so_ho} hộ", dinh_dang_tien(tong_all))
            c4.metric("Tiết kiệm vs 1 hộ", dinh_dang_tien(tiet_kiem),
                      delta=f"-{pct_display}%", delta_color="normal")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Sản lượng", f"{kwh_input:.0f} kWh")
            c2.metric("Trước VAT", dinh_dang_tien(truoc_vat_ho))
            c3.metric("Thanh toán", dinh_dang_tien(tong_per_ho),
                      delta=f"VAT: {dinh_dang_tien(tien_vat_ho)}")

        bacs = [b for b in chi_tiet if b["sl"] > 0]
        _render_waterfall(bacs, tien_vat_ho, tong_per_ho, kwh_per_ho, so_ho, tong_all)

        # So sánh theo số hộ
        if so_ho > 1 and kwh_input > 0:
            with st.expander("So sánh tiền điện theo số hộ"):
                max_ho = min(so_ho + 2, MAX_COMPARE_HO)
                compare_rows = []
                for h in range(1, max_ho + 1):
                    _, _, _, t_h = tinh_tien_dien(kwh_input / h)
                    tong_h = t_h * h
                    compare_rows.append({
                        "Số hộ": h,
                        "kWh/hộ": f"{kwh_input / h:.1f}",
                        "Tiền/hộ": dinh_dang_tien(t_h),
                        "Tổng thanh toán": dinh_dang_tien(tong_h),
                        "Tiết kiệm vs 1 hộ": (
                            dinh_dang_tien(tong_neu_1ho - tong_h) if h > 1 else "—"
                        ),
                    })
                st.table(pd.DataFrame(compare_rows))

        # Bảng chi tiết từng bậc
        with st.expander("Bảng chi tiết từng bậc (1 hộ)"):
            rows = [
                {
                    "Bậc": f"Bậc {b['bac']}",
                    "Khoảng (kWh)": f"{b['tu']} – {b['den']}",
                    "Đơn giá": f"{b['don_gia']:,} đ/kWh",
                    "Sản lượng": f"{b['sl']:.1f} kWh",
                    "Thành tiền": dinh_dang_tien(b["tt"]),
                }
                for b in bacs
            ]
            rows.append({
                "Bậc": "VAT (8%)", "Khoảng (kWh)": "—", "Đơn giá": "—",
                "Sản lượng": "—", "Thành tiền": dinh_dang_tien(tien_vat_ho),
            })
            rows.append({
                "Bậc": "Tổng 1 hộ", "Khoảng (kWh)": "—", "Đơn giá": "—",
                "Sản lượng": f"{kwh_per_ho:.1f} kWh",
                "Thành tiền": dinh_dang_tien(tong_per_ho),
            })
            if so_ho > 1:
                rows.append({
                    "Bậc": f"× {so_ho} hộ", "Khoảng (kWh)": "—", "Đơn giá": "—",
                    "Sản lượng": f"{kwh_input:.0f} kWh",
                    "Thành tiền": dinh_dang_tien(tong_all),
                })
            st.table(pd.DataFrame(rows))

        _render_canh_bao_vuot_bac(bacs)

        # Xuất hóa đơn HTML
        hoa_don_html = tao_hoa_don_html(
            kwh_input, so_ho, kwh_per_ho, chi_tiet,
            tong_per_ho, tien_vat_ho, tong_all,
        )
        ten_file = (
            f"hoadon_{kwh_input:.0f}kwh_{so_ho}ho_"
            f"{datetime.now().strftime('%Y%m%d')}.html"
        )
        st.download_button(
            label="Xuất hóa đơn (HTML → in PDF)",
            data=hoa_don_html.encode("utf-8"),
            file_name=ten_file,
            mime="text/html",
            help=(
                "Tải file HTML về, mở bằng trình duyệt rồi nhấn Ctrl+P "
                "để in hoặc lưu thành PDF."
            ),
        )

        # AI tư vấn — cache vào session_state để không mất khi rerun
        if st.button("AI tư vấn tiết kiệm điện", disabled=(llm is None),
                     key="btn_ai_tien_dien"):
            with st.spinner("Đang phân tích..."):
                ho_info = (
                    f"{so_ho} hộ, mỗi hộ {kwh_per_ho:.1f} kWh, "
                    f"tổng {dinh_dang_tien(tong_all)}"
                    if so_ho > 1
                    else f"1 hộ dùng {kwh_input:.0f} kWh, "
                         f"tiền {dinh_dang_tien(tong_per_ho)}"
                )
                prompt = (
                    f"Khách hàng: {ho_info}/tháng.\n"
                    "Hãy nhận xét mức tiêu thụ và đưa ra 3 lời khuyên để giảm tiền điện.\n"
                    "Trả lời ngắn gọn bằng tiếng Việt."
                )
                st.session_state["ai_tuvan_tab_tien_dien"] = goi_ai_voi_xu_ly_loi(
                    llm, prompt
                )

        if st.session_state.get("ai_tuvan_tab_tien_dien"):
            st.info(st.session_state["ai_tuvan_tab_tien_dien"])
