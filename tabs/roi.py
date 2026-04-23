"""Tab 5 — Tư vấn ROI thay thiết bị."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import LOAI_THIET_BI_ROI
from utils import DAYS_PER_MONTH, dinh_dang_tien, tinh_tien_dien

MONTHS_PER_YEAR = 12


def _tinh_kwh_thang(loai_tinh: str, cong_suat: float, gio: float, so_luong: int) -> float:
    """Tính kWh/tháng theo loại (kw hoặc kwh_ngay)."""
    if loai_tinh == "kw":
        return cong_suat * gio * so_luong * DAYS_PER_MONTH
    # loai_tinh == "kwh_ngay"
    return cong_suat * so_luong * DAYS_PER_MONTH


def render() -> None:
    """Vẽ toàn bộ Tab Tư vấn ROI."""
    st.markdown("#### Tư vấn Thay Thiết Bị Tiết Kiệm Điện")
    st.markdown(
        "So sánh chi phí điện thiết bị cũ vs mới và tính thời gian hoàn vốn "
        "khi đầu tư thiết bị tiết kiệm điện."
    )

    roi_left, roi_right = st.columns([1, 1.4], gap="large")

    with roi_left:
        st.markdown("**Thông tin thiết bị hiện tại**")
        with st.container(border=True):
            ten_loai = st.selectbox(
                "Loại thiết bị:", list(LOAI_THIET_BI_ROI.keys()), key="roi_loai"
            )
            loai = LOAI_THIET_BI_ROI[ten_loai]
            st.caption(f"_{loai['mo_ta_cu']}_")

            sao_cu = st.select_slider(
                "Số sao / hiệu suất thiết bị cũ:",
                options=[1, 2, 3, 4, 5],
                value=2, key="roi_sao",
                help="1 sao = kém nhất, 5 sao = tiết kiệm điện nhất.",
            )
            so_luong_roi = st.number_input(
                "Số lượng thiết bị:", min_value=1, max_value=20, value=1, key="roi_sl"
            )
            gio_roi = st.number_input(
                "Giờ sử dụng / ngày:",
                min_value=0.5, max_value=24.0,
                value=float(loai["gio_mac_dinh"]),
                step=0.5, key="roi_gio",
            )

        btn_roi = st.button("Tính ROI", type="primary")

    with roi_right:
        if not btn_roi:
            st.info("Chọn thiết bị và nhấn **Tính ROI** để xem phân tích.")
            return

        cs_cu = loai["cong_suat_theo_sao"][sao_cu]
        kwh_thang_cu = _tinh_kwh_thang(loai["loai_tinh"], cs_cu, gio_roi, so_luong_roi)
        _, _, _, tien_thang_cu = tinh_tien_dien(kwh_thang_cu)

        st.markdown(
            f"**Thiết bị hiện tại:** {so_luong_roi} × {ten_loai} "
            f"({sao_cu}★) — **{kwh_thang_cu:.1f} kWh/tháng** "
            f"— **{dinh_dang_tien(tien_thang_cu)}/tháng**"
        )
        st.markdown("---")

        rows_roi = []
        options_names = []
        options_tiet_kiem = []
        options_hoan_von = []

        for opt in loai["thay_the"]:
            cs_moi = opt.get("cong_suat") if loai["loai_tinh"] == "kw" else opt.get("kwh_ngay")
            kwh_thang_moi = _tinh_kwh_thang(
                loai["loai_tinh"], cs_moi, gio_roi, so_luong_roi
            )
            _, _, _, tien_thang_moi = tinh_tien_dien(kwh_thang_moi)
            tiet_kiem_thang = tien_thang_cu - tien_thang_moi
            tiet_kiem_nam = tiet_kiem_thang * MONTHS_PER_YEAR
            chi_phi_opt = opt["gia"] * so_luong_roi
            hoan_von_opt = chi_phi_opt / tiet_kiem_nam if tiet_kiem_nam > 0 else None

            rows_roi.append({
                "Thiết bị mới": opt["ten"],
                "kWh/tháng": f"{kwh_thang_moi:.1f}",
                "Tiền điện/tháng": dinh_dang_tien(tien_thang_moi),
                "Tiết kiệm/tháng": dinh_dang_tien(tiet_kiem_thang),
                "Chi phí mua": dinh_dang_tien(chi_phi_opt),
                "Hoàn vốn": f"{hoan_von_opt:.1f} năm" if hoan_von_opt else "—",
            })
            options_names.append(opt["ten"])
            options_tiet_kiem.append(tiet_kiem_thang)
            options_hoan_von.append(hoan_von_opt or 0)

        st.table(pd.DataFrame(rows_roi))

        # Chart
        fig_roi = go.Figure()
        fig_roi.add_trace(go.Bar(
            x=options_names, y=options_tiet_kiem,
            marker_color="#0ea5a0",
            text=[dinh_dang_tien(v) for v in options_tiet_kiem],
            textposition="outside",
            name="Tiết kiệm/tháng",
        ))
        fig_roi.update_layout(
            title=f"Tiết kiệm tiền điện / tháng khi thay {ten_loai}",
            yaxis_title="Tiết kiệm (đ/tháng)", showlegend=False,
            height=280, plot_bgcolor="white", paper_bgcolor="white",
            margin={"t": 50, "b": 20, "l": 20, "r": 20},
        )
        st.plotly_chart(fig_roi, use_container_width=True)

        # Gợi ý option tốt nhất
        if options_hoan_von:
            valid = [(i, hv) for i, hv in enumerate(options_hoan_von) if hv > 0]
            if valid:
                best_idx, best_hv = min(valid, key=lambda x: x[1])
                best = loai["thay_the"][best_idx]
                st.success(
                    f"**Gợi ý tốt nhất:** {best['ten']} — hoàn vốn trong "
                    f"**{best_hv:.1f} năm**, tiết kiệm "
                    f"**{dinh_dang_tien(options_tiet_kiem[best_idx])}/tháng**."
                )
