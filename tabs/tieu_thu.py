"""Tab 3 — Phân tích tiêu thụ điện theo thiết bị."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import (
    BENCHMARK_HO_GIA_DINH,
    LOAI_NHA_OPTIONS,
    THIET_BI_MAC_DINH,
    THU_VIEN_THIET_BI,
    TU_LANH_KWH_NGAY,
)
from rag_pipeline import goi_ai_voi_xu_ly_loi
from utils import dinh_dang_tien, tinh_kwh_thang, tinh_tien_dien


def _render_thiet_bi_mac_dinh() -> None:
    """Danh sách thiết bị mặc định với input quantity/hours."""
    for ten, cong_suat, gio_md, ghi_chu in THIET_BI_MAC_DINH:
        st.markdown(f"**{ten}** — _{ghi_chu}_")
        c1, c2 = st.columns(2)
        key_q = f"qty_{ten}"
        key_h = f"hrs_{ten}"
        c1.number_input("Số lượng", min_value=0, value=1, step=1, key=key_q)
        c2.number_input(
            "Giờ/ngày", min_value=0, max_value=24,
            value=gio_md, key=key_h, disabled=(cong_suat is None),
        )


def _render_thu_vien_thiet_bi() -> None:
    """Dropdown chọn thiết bị từ thư viện và thêm vào custom_devices."""
    lib_names = ["— Chọn thiết bị từ thư viện —"] + list(THU_VIEN_THIET_BI.keys())
    selected = st.selectbox(
        "Thiết bị:", lib_names, key="lib_select", label_visibility="collapsed",
    )
    if selected == "— Chọn thiết bị từ thư viện —":
        return

    cs_lib, gio_lib, ghi_lib = THU_VIEN_THIET_BI[selected]
    st.caption(f"ℹ️ {f'{cs_lib*1000:.0f}W · ' if cs_lib else ''}{ghi_lib}")
    lc1, lc2, lc3 = st.columns([1, 1, 2])
    lib_qty = lc1.number_input("SL", 1, 20, 1, key="lib_qty")

    if cs_lib:
        lib_hrs = lc2.number_input("Giờ/ngày", 0, 24, gio_lib, key="lib_hrs")
    else:
        lib_hrs = 24
        lc2.caption(f"{ghi_lib.split(' kWh')[0]} kWh/ng")

    if lc3.button("➕ Thêm vào danh sách", key="lib_add"):
        if cs_lib:
            st.session_state.custom_devices.append({
                "name": selected, "power_kw": cs_lib,
                "qty": lib_qty, "hrs": lib_hrs,
            })
        else:
            kwh_nd = float(ghi_lib.split(" kWh")[0])
            st.session_state.custom_devices.append({
                "name": selected, "power_kw": None,
                "kwh_ngay": kwh_nd, "qty": lib_qty, "hrs": 24,
            })
        st.rerun()


def _render_them_thu_cong_va_danh_sach() -> None:
    """Form thêm thiết bị thủ công + danh sách các custom devices đã thêm."""
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    ten_tb = c1.text_input("Tên", placeholder="VD: Bình nóng lạnh",
                            key="new_name", label_visibility="collapsed")
    cong_suat_w = c2.number_input("W", min_value=1, value=2000,
                                    key="new_power", label_visibility="collapsed")
    so_luong_tb = c3.number_input("SL", min_value=1, value=1,
                                    key="new_qty", label_visibility="collapsed")
    gio_tb = c4.number_input("Giờ", min_value=1, max_value=24, value=2,
                              key="new_hrs", label_visibility="collapsed")

    if st.button("Thêm thiết bị"):
        if ten_tb.strip():
            st.session_state.custom_devices.append({
                "name": ten_tb.strip(), "power_kw": cong_suat_w / 1000,
                "qty": so_luong_tb, "hrs": gio_tb,
            })
            st.rerun()

    # Danh sách custom devices — key unique để tránh bug đổi index khi xóa
    devices_snapshot = list(st.session_state.custom_devices)
    to_delete = None
    for i, dev in enumerate(devices_snapshot):
        if dev.get("power_kw") is None:
            kwh_dev = tinh_kwh_thang(None, dev["qty"], 24, dev["kwh_ngay"])
            desc = (
                f"{dev['name']} — {dev['qty']} cái × "
                f"{dev['kwh_ngay']} kWh/ngày = **{kwh_dev} kWh/tháng**"
            )
        else:
            kwh_dev = tinh_kwh_thang(dev["power_kw"], dev["qty"], dev["hrs"])
            desc = (
                f"{dev['name']} — {dev['qty']} cái × "
                f"{dev['power_kw']*1000:.0f}W × {dev['hrs']}h = "
                f"**{kwh_dev} kWh/tháng**"
            )
        col_d, col_x = st.columns([4, 1])
        col_d.markdown(desc)
        unique_key = f"del_{i}_{dev['name'][:20]}"
        if col_x.button("Xóa", key=unique_key):
            to_delete = i

    if to_delete is not None:
        st.session_state.custom_devices.pop(to_delete)
        st.rerun()


def _tinh_tong_thiet_bi() -> dict:
    """Gom kWh của tất cả thiết bị (mặc định + custom) thành dict."""
    device_data = {}

    for ten, cong_suat, gio_md, _ in THIET_BI_MAC_DINH:
        qty = st.session_state.get(f"qty_{ten}", 0)
        hrs = st.session_state.get(f"hrs_{ten}", gio_md)
        if cong_suat is None:
            kwh = tinh_kwh_thang(None, qty, hrs, TU_LANH_KWH_NGAY)
        else:
            kwh = tinh_kwh_thang(cong_suat, qty, hrs)
        if kwh > 0:
            device_data[ten] = kwh

    for dev in st.session_state.custom_devices:
        if dev.get("power_kw") is None:
            kwh = tinh_kwh_thang(None, dev["qty"], 24, dev["kwh_ngay"])
        else:
            kwh = tinh_kwh_thang(dev["power_kw"], dev["qty"], dev["hrs"])
        if kwh > 0:
            device_data[dev["name"]] = kwh

    return device_data


def _render_so_sanh_benchmark(total_kwh: float) -> None:
    """So sánh với benchmark hộ gia đình tương tự."""
    with st.expander("📊 So sánh với hộ gia đình tương tự"):
        st.markdown("Chọn thông tin hộ để so sánh mức tiêu thụ với dữ liệu EVN.")
        bc1, bc2 = st.columns(2)

        default_nguoi = (
            st.session_state.profile_so_nguoi
            if st.session_state.profile_so_nguoi in [1, 2, 3, 4, 5, 6]
            else 3
        )
        default_nha = (
            st.session_state.profile_loai_nha
            if st.session_state.profile_loai_nha in LOAI_NHA_OPTIONS
            else "Nhà phố"
        )

        so_nguoi = bc1.selectbox(
            "Số người:", [1, 2, 3, 4, 5, 6],
            index=[1, 2, 3, 4, 5, 6].index(default_nguoi),
            key="bench_nguoi",
        )
        loai_nha_bench = bc2.selectbox(
            "Loại nhà:", LOAI_NHA_OPTIONS,
            index=LOAI_NHA_OPTIONS.index(default_nha),
            key="bench_nha",
        )

        bench = BENCHMARK_HO_GIA_DINH.get((so_nguoi, loai_nha_bench))
        if not bench:
            st.info("Chưa có dữ liệu benchmark cho loại hộ gia đình này.")
            return

        avg, lo, hi, mo_ta = bench
        pct = (total_kwh - avg) / avg * 100 if avg else 0

        if total_kwh < lo:
            nhan_xet = "✅ Tiêu thụ **thấp hơn mức bình thường** — rất tiết kiệm!"
        elif total_kwh <= avg:
            nhan_xet = "👍 Tiêu thụ **dưới mức trung bình** — tốt."
        elif total_kwh <= hi:
            nhan_xet = "⚠️ Tiêu thụ **trên mức trung bình** — có thể tiết kiệm hơn."
        else:
            nhan_xet = (
                "🔴 Tiêu thụ **cao hơn mức thông thường** — "
                "nên xem xét tiết kiệm điện."
            )

        st.markdown(f"_{mo_ta}_")
        st.markdown(nhan_xet)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Của bạn", f"{total_kwh} kWh")
        m2.metric("Trung bình", f"{avg} kWh",
                  delta=f"{pct:+.0f}%", delta_color="inverse")
        m3.metric("Thấp nhất", f"{lo} kWh")
        m4.metric("Cao nhất", f"{hi} kWh")
        progress_val = min(1.0, max(0.0, (total_kwh - lo) / max(1, hi - lo)))
        st.progress(
            progress_val,
            text=f"Vị trí trong khoảng [{lo}–{hi}] kWh/tháng",
        )


def render(llm) -> None:
    """Vẽ toàn bộ Tab Phân tích tiêu thụ."""
    st.markdown("#### Ước tính tiêu thụ điện của hộ gia đình")
    st.markdown("Nhập thông tin thiết bị để ước tính số kWh và tiền điện hàng tháng.")

    col_input, col_result = st.columns([1, 1.2], gap="large")

    with col_input:
        st.markdown("**Thiết bị trong nhà**")
        with st.container(border=True):
            _render_thiet_bi_mac_dinh()

        st.markdown("**Thư viện thiết bị — chọn nhanh**")
        with st.container(border=True):
            _render_thu_vien_thiet_bi()

        st.markdown("**Thêm thiết bị thủ công**")
        with st.container(border=True):
            _render_them_thu_cong_va_danh_sach()

        btn_analyze = st.button("Tính toán", type="primary")

    with col_result:
        if btn_analyze:
            device_data = _tinh_tong_thiet_bi()
            total_kwh = round(sum(device_data.values()), 1)

            if total_kwh == 0:
                st.warning("Chưa có thiết bị nào. Vui lòng nhập số lượng thiết bị.")
            else:
                _, _, _, total_money = tinh_tien_dien(total_kwh)
                st.metric(
                    "Tổng tiêu thụ / tháng", f"{total_kwh} kWh",
                    delta=f"Ước tính: {dinh_dang_tien(total_money)}",
                )

                top_device = max(device_data, key=device_data.get)
                pct_top = round(device_data[top_device] / total_kwh * 100, 1)
                st.info(
                    f"**{top_device}** chiếm nhiều nhất: {pct_top}% "
                    f"({device_data[top_device]} kWh)"
                )

                # Pie chart
                fig_pie = go.Figure(go.Pie(
                    labels=list(device_data.keys()),
                    values=list(device_data.values()),
                    hole=0.4, textinfo="label+percent",
                ))
                fig_pie.update_layout(
                    title="Tỷ trọng tiêu thụ theo thiết bị",
                    height=300, showlegend=False,
                    plot_bgcolor="white", paper_bgcolor="white",
                    margin={"t": 50, "b": 10, "l": 10, "r": 10},
                )
                st.plotly_chart(fig_pie, use_container_width=True)

                # Bảng xếp hạng
                sorted_dev = sorted(
                    device_data.items(), key=lambda x: x[1], reverse=True
                )
                rows = [
                    {
                        "Hạng": rank,
                        "Thiết bị": name,
                        "kWh/tháng": kwh,
                        "Tỷ lệ": f"{round(kwh / total_kwh * 100, 1)}%",
                    }
                    for rank, (name, kwh) in enumerate(sorted_dev, 1)
                ]
                st.table(pd.DataFrame(rows))

                # Lưu để nút AI dùng
                st.session_state["_last_analysis"] = {
                    "total_kwh": total_kwh,
                    "total_money": total_money,
                    "sorted_dev": sorted_dev,
                    "top_device": top_device,
                    "pct": pct_top,
                }

                _render_so_sanh_benchmark(total_kwh)
        else:
            st.info("Nhập thông tin thiết bị rồi nhấn 'Tính toán' để xem kết quả.")

        # AI khuyến nghị
        if st.session_state.get("_last_analysis"):
            last = st.session_state["_last_analysis"]
            if st.button("AI khuyến nghị tiết kiệm", disabled=(llm is None),
                         key="btn_ai_tieu_thu"):
                with st.spinner("Đang phân tích..."):
                    ds = ", ".join(f"{k}: {v}kWh" for k, v in last["sorted_dev"])
                    prompt = (
                        f"Hộ gia đình tiêu thụ {last['total_kwh']} kWh/tháng, "
                        f"ước tính {dinh_dang_tien(last['total_money'])}.\n"
                        f"Chi tiết: {ds}. Thiết bị tốn nhiều nhất: "
                        f"{last['top_device']} ({last['pct']}%).\n"
                        "Đưa ra 3 khuyến nghị cụ thể để giảm tiền điện. "
                        "Ngắn gọn, bằng tiếng Việt."
                    )
                    st.session_state["ai_tuvan_tab_tieu_thu"] = goi_ai_voi_xu_ly_loi(
                        llm, prompt
                    )

            if st.session_state.get("ai_tuvan_tab_tieu_thu"):
                st.markdown(st.session_state["ai_tuvan_tab_tieu_thu"])
