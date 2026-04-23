"""Tab 4 — Điện mặt trời mái nhà."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from config import (
    SOLAR_COST_PER_WP,
    SOLAR_FEED_IN,
    SOLAR_PANEL_M2,
    SOLAR_PANEL_W,
    SOLAR_PSH,
    SOLAR_SELF_USE_RATE,
    SOLAR_SYSTEM_EFF,
)
from utils import (
    dinh_dang_tien,
    tinh_dien_mat_troi,
    tinh_tien_dien,
    tinh_tu_dung_va_ban_lai,
)

# Tỷ lệ tối thiểu (so với tien_truoc) để cột "sau ĐMT" vẫn hiển thị được khi = 0
SOLAR_MIN_BAR_RATIO = 0.015


def render() -> None:
    """Vẽ toàn bộ Tab Điện mặt trời."""
    st.markdown("#### Máy tính điện mặt trời mái nhà")
    st.markdown(
        "Ước tính sản lượng, tiết kiệm điện và thời gian hoàn vốn khi lắp điện mặt trời."
    )

    s_left, s_right = st.columns([1, 1.3], gap="large")

    with s_left:
        st.markdown("**Thông tin hệ thống**")
        with st.container(border=True):
            kv_list = list(SOLAR_PSH.keys())
            kv_idx = (
                kv_list.index(st.session_state.profile_khu_vuc)
                if st.session_state.profile_khu_vuc in kv_list
                else 0
            )
            khu_vuc = st.selectbox(
                "Khu vực lắp đặt:", kv_list, index=kv_idx, key="solar_khu_vuc"
            )
            dien_tich = st.number_input(
                "Diện tích mái khả dụng (m²)",
                min_value=5.0, max_value=500.0, value=30.0, step=5.0, key="solar_dt",
                help="Diện tích mái có thể lắp pin (tránh bóng râm). "
                     "Mỗi tấm 400Wp chiếm ~2m².",
            )
            tieu_thu = st.number_input(
                "Tiêu thụ điện hiện tại (kWh/tháng)",
                min_value=10.0, max_value=5000.0, value=250.0,
                step=10.0, key="solar_kwh",
            )
            tu_dung_rate = st.slider(
                "Tỷ lệ tiêu thụ ban ngày (%)",
                min_value=30, max_value=100,
                value=int(SOLAR_SELF_USE_RATE * 100), step=5, key="solar_tudung",
                help=(
                    "Phần trăm điện bạn dùng vào BAN NGÀY (khi ĐMT đang sản xuất). "
                    "Ví dụ 70%: trong tổng tiêu thụ, 70% rơi vào ban ngày nên có thể "
                    "được ĐMT phủ, 30% còn lại vào ban đêm phải mua từ EVN. "
                    "Hộ đi làm ban ngày → rate thấp (~40%), hộ có người ở nhà → cao (~80%)."
                ),
            ) / 100

        btn_solar = st.button("Tính toán điện mặt trời", type="primary")

        st.markdown("---")
        st.caption(
            f"**Thông số hệ thống:** Tấm pin {SOLAR_PANEL_W}Wp · "
            f"Hiệu suất hệ thống {int(SOLAR_SYSTEM_EFF*100)}% · "
            f"Chi phí ~{SOLAR_COST_PER_WP:,} đ/Wp · "
            f"Giá bán điện dư: {SOLAR_FEED_IN} đ/kWh."
        )

    with s_right:
        if btn_solar:
            st.session_state["_solar_computed"] = True

        if not st.session_state.get("_solar_computed"):
            st.info("Nhập thông tin và nhấn **Tính toán điện mặt trời** để xem kết quả.")
            return

        # ── Tính toán ──────────────────────────────────────────
        psh = SOLAR_PSH[khu_vuc]
        dmt = tinh_dien_mat_troi(
            dien_tich_m2=dien_tich, psh=psh,
            panel_w=SOLAR_PANEL_W, panel_m2=SOLAR_PANEL_M2,
            system_eff=SOLAR_SYSTEM_EFF,
        )
        so_tam = dmt["so_tam"]
        cong_suat_kwp = dmt["cong_suat_kwp"]
        san_luong_ngay = dmt["san_luong_ngay_kwh"]
        san_luong_thang = dmt["san_luong_thang_kwh"]

        # Mái quá nhỏ không đủ lắp 1 tấm pin → cảnh báo sớm, không tính tiếp
        if so_tam == 0:
            st.warning(
                f"Mái {dien_tich:.1f}m² nhỏ hơn diện tích 1 tấm pin "
                f"({SOLAR_PANEL_M2}m²). Vui lòng tăng diện tích mái."
            )
            return

        kwh_tu_dung, kwh_ban_lai = tinh_tu_dung_va_ban_lai(
            san_luong_thang, tu_dung_rate, tieu_thu
        )

        _, _, _, tien_truoc = tinh_tien_dien(tieu_thu)
        _, _, _, tien_sau = tinh_tien_dien(max(0, tieu_thu - kwh_tu_dung))
        tiet_kiem_thang = tien_truoc - tien_sau
        doanh_thu_ban = kwh_ban_lai * SOLAR_FEED_IN
        loi_ich_thang = tiet_kiem_thang + doanh_thu_ban
        loi_ich_nam = loi_ich_thang * 12

        chi_phi = cong_suat_kwp * 1000 * SOLAR_COST_PER_WP
        hoan_von = chi_phi / loi_ich_nam if loi_ich_nam > 0 else None

        # ── Metrics ────────────────────────────────────────────
        r1c1, r1c2, r1c3 = st.columns(3)
        r1c1.metric("Số tấm pin", f"{so_tam} tấm")
        r1c2.metric("Công suất hệ thống", f"{cong_suat_kwp:.1f} kWp")
        r1c3.metric("Sản lượng / tháng", f"{san_luong_thang:.0f} kWh")

        r2c1, r2c2, r2c3 = st.columns(3)
        r2c1.metric("Tiết kiệm tiền điện",
                    dinh_dang_tien(tiet_kiem_thang), delta="/tháng")
        r2c2.metric("Doanh thu bán điện dư",
                    dinh_dang_tien(doanh_thu_ban), delta="/tháng")
        r2c3.metric("Tổng lợi ích",
                    dinh_dang_tien(loi_ich_thang), delta="/tháng")

        st.markdown("---")
        ic1, ic2 = st.columns(2)
        ic1.metric("Chi phí đầu tư", dinh_dang_tien(chi_phi))
        ic2.metric(
            "Thời gian hoàn vốn",
            f"{hoan_von:.1f} năm" if hoan_von else "Không xác định",
        )

        # ── Chart ──────────────────────────────────────────────
        # Khi tien_sau == 0 (ĐMT đủ 100%), cho cột một chiều cao tối thiểu
        # để vẫn hiển thị được trên biểu đồ.
        y_sau_display = (
            max(tien_sau, tien_truoc * SOLAR_MIN_BAR_RATIO)
            if tien_sau == 0 else tien_sau
        )
        label_sau_display = (
            "0 đ ✅ ĐMT đủ 100%" if tien_sau == 0 else dinh_dang_tien(tien_sau)
        )
        fig = go.Figure(go.Bar(
            x=["Tiền điện hiện tại", "Còn phải trả sau ĐMT", "Tiết kiệm / tháng"],
            y=[tien_truoc, y_sau_display, tiet_kiem_thang],
            marker_color=[
                "#f97316",
                "#0ea5a0" if tien_sau > 0 else "#86efac",
                "#22c55e",
            ],
            text=[
                dinh_dang_tien(tien_truoc),
                label_sau_display,
                dinh_dang_tien(tiet_kiem_thang),
            ],
            textposition="outside",
        ))
        fig.update_layout(
            title="So sánh tiền điện trước/sau khi lắp điện mặt trời",
            yaxis_title="Tiền điện (đ/tháng)", showlegend=False,
            height=320, plot_bgcolor="white", paper_bgcolor="white",
            margin={"t": 50, "b": 20, "l": 20, "r": 20},
        )
        st.plotly_chart(fig, use_container_width=True)

        # ── Bảng chi tiết ──────────────────────────────────────
        with st.expander("Chi tiết tính toán"):
            st.markdown(f"""
| Thông số | Giá trị |
|---|---|
| Khu vực | {khu_vuc} |
| Giờ nắng đỉnh (PSH) | {psh} h/ngày |
| Số tấm pin ({SOLAR_PANEL_W}Wp) | {so_tam} tấm |
| Công suất hệ thống | {cong_suat_kwp:.2f} kWp |
| Sản lượng / ngày | {san_luong_ngay:.1f} kWh |
| Sản lượng / tháng | {san_luong_thang:.0f} kWh |
| kWh tự dùng / tháng | {kwh_tu_dung:.0f} kWh (tiêu thụ ban ngày {int(tu_dung_rate*100)}%) |
| kWh bán lại EVN / tháng | {kwh_ban_lai:.0f} kWh |
| Tiết kiệm tiền điện / tháng | {dinh_dang_tien(tiet_kiem_thang)} |
| Doanh thu bán điện dư / tháng | {dinh_dang_tien(doanh_thu_ban)} |
| Tổng lợi ích / năm | {dinh_dang_tien(loi_ich_nam)} |
| Chi phí đầu tư | {dinh_dang_tien(chi_phi)} |
| Thời gian hoàn vốn | {f'{hoan_von:.1f} năm' if hoan_von else '—'} |
            """)
