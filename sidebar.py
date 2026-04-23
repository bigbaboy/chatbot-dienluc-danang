from __future__ import annotations
import json
from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

from config import LOAI_NHA_OPTIONS, SOLAR_PSH
from utils import thang_hop_le, tinh_tien_dien


MAX_LICH_SU_HIEN_THI = 6


def _render_ho_so() -> None:
    with st.expander(
        "👤 Hồ sơ của bạn",
        expanded=(not st.session_state.profile_ten),
    ):
        ten_nhap = st.text_input(
            "Tên (tùy chọn)", value=st.session_state.profile_ten,
            placeholder="Ví dụ: Anh Minh", key="sidebar_ten",
        )
        so_nguoi_nhap = st.selectbox(
            "Số người trong nhà", [1, 2, 3, 4, 5, 6],
            index=[1, 2, 3, 4, 5, 6].index(st.session_state.profile_so_nguoi),
            key="sidebar_nguoi",
        )
        loai_nha_nhap = st.selectbox(
            "Loại nhà", LOAI_NHA_OPTIONS,
            index=LOAI_NHA_OPTIONS.index(st.session_state.profile_loai_nha),
            key="sidebar_nha",
        )
        khu_vuc_nhap = st.selectbox(
            "Khu vực", list(SOLAR_PSH.keys()),
            index=list(SOLAR_PSH.keys()).index(st.session_state.profile_khu_vuc),
            key="sidebar_kv",
        )
        if st.button("Lưu hồ sơ", type="primary"):
            st.session_state.profile_ten = ten_nhap
            st.session_state.profile_so_nguoi = so_nguoi_nhap
            st.session_state.profile_loai_nha = loai_nha_nhap
            st.session_state.profile_khu_vuc = khu_vuc_nhap
            st.success("Đã lưu!")
            st.rerun()

    if st.session_state.profile_ten:
        st.markdown(
            f"Xin chào, **{st.session_state.profile_ten}**!  \n"
            f"{st.session_state.profile_so_nguoi} người · "
            f"{st.session_state.profile_loai_nha} · "
            f"{st.session_state.profile_khu_vuc}"
        )


def _render_lich_su_tieu_thu() -> None:
    with st.expander("📅 Lịch sử tiêu thụ"):
        st.caption("Nhập tiêu thụ hàng tháng để theo dõi xu hướng.")
        lh_col1, lh_col2 = st.columns(2)
        lh_thang = lh_col1.text_input("Tháng", placeholder="03/2025", key="lh_thang")
        lh_kwh = lh_col2.number_input("kWh", min_value=1, value=200, key="lh_kwh")

        if st.button("Thêm tháng"):
            ten_thang = lh_thang.strip()
            if not ten_thang:
                st.warning("Vui lòng nhập tháng.")
            elif not thang_hop_le(ten_thang):
                st.warning(
                    "Định dạng tháng không đúng. Ví dụ hợp lệ: "
                    "`03/2025`, `12/2024`."
                )
            else:
                _, _, _, lh_tong = tinh_tien_dien(lh_kwh)
                st.session_state.lich_su_tieu_thu.append({
                    "thang": ten_thang,
                    "kwh": lh_kwh,
                    "tien": int(lh_tong),
                })
                st.rerun()

        if not st.session_state.lich_su_tieu_thu:
            return

        lh_data = st.session_state.lich_su_tieu_thu[-MAX_LICH_SU_HIEN_THI:]
        fig = go.Figure(go.Scatter(
            x=[r["thang"] for r in lh_data],
            y=[r["kwh"] for r in lh_data],
            mode="lines+markers+text",
            text=[str(r["kwh"]) for r in lh_data],
            textposition="top center",
            line={"color": "#0ea5a0"},
            marker={"size": 8},
        ))
        fig.update_layout(
            height=180, margin={"t": 10, "b": 30, "l": 10, "r": 10},
            yaxis_title="kWh", plot_bgcolor="white", paper_bgcolor="white",
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

        if st.button("Xóa lịch sử", key="xoa_lh"):
            st.session_state.lich_su_tieu_thu = []
            st.rerun()


def _render_trang_thai_he_thong(vector_db, llm) -> None:
    st.caption(
        f"Vector DB: {'✅' if vector_db else '❌'}  |  "
        f"LLM: {'✅' if llm else '❌'}"
    )
    st.markdown(f"Phiên: **{len(st.session_state.messages)}** tin nhắn")

    if st.button("Xóa lịch sử chat"):
        st.session_state.messages = []
        st.rerun()

    if st.session_state.messages:
        data_export = {
            "xuat_luc": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "so_tin_nhan": len(st.session_state.messages),
            "hoi_thoai": st.session_state.messages,
        }
        ten_file = f"lichsu_chat_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        st.download_button(
            label="Tải lịch sử chat",
            data=json.dumps(data_export, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=ten_file,
            mime="application/json",
        )


def render(vector_db, llm) -> None:
    with st.sidebar:
        st.markdown("### ⚡ Điện lực Đà Nẵng")
        _render_ho_so()
        st.divider()
        _render_lich_su_tieu_thu()
        st.divider()
        _render_trang_thai_he_thong(vector_db, llm)
        st.caption("Phát triển bởi Sinh viên K29 · Khoa TMĐT")
