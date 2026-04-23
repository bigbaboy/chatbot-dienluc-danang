from __future__ import annotations
from pathlib import Path
import streamlit as st
ASSETS_DIR = Path(__file__).parent / "assets"


def load_css(filename: str = "styles.css") -> None:
    css_path = ASSETS_DIR / filename
    if not css_path.is_file():
        st.warning(f"Không tìm thấy file CSS: {css_path}")
        return
    css = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def init_session_state() -> None:
    defaults = {
        "messages": [],
        "custom_devices": [],
        "lich_su_tieu_thu": [],
        "profile_ten": "",
        "profile_so_nguoi": 4,
        "profile_loai_nha": "Chung cư",
        "profile_khu_vuc": "Đà Nẵng và Trung Bộ",
        # Cache kết quả AI tư vấn — tránh mất khi Streamlit rerun
        "ai_tuvan_tab_tien_dien": "",
        "ai_tuvan_tab_tieu_thu": "",
        # Flag để tab Solar chỉ hiển thị kết quả khi user đã nhấn nút
        "_solar_computed": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
