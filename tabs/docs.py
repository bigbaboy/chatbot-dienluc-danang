from __future__ import annotations

import logging
import os
from datetime import datetime

import streamlit as st

from config import DATA_DIR, DB_DIR
from db_manager import build_faiss_db, merge_into_existing_db
from doc_pdf_smart import doc_pdf_thong_minh

logger = logging.getLogger(__name__)


def _render_upload_section(vector_db, init_system_fn) -> None:
    st.markdown("**Tải lên tài liệu mới**")
    uploaded_files = st.file_uploader(
        "Chọn file PDF", type=["pdf"], accept_multiple_files=True,
        label_visibility="collapsed",
    )
    if uploaded_files:
        st.success(
            f"Đã chọn {len(uploaded_files)} file: "
            f"{', '.join(f.name for f in uploaded_files)}"
        )

    btn_upload = st.button(
        "Xử lý và tích hợp vào hệ thống", type="primary",
        disabled=(not uploaded_files or vector_db is None),
    )

    if not (btn_upload and uploaded_files):
        return

    progress_bar = st.progress(0, text="Đang xử lý...")
    logs: list = []
    log_area = st.empty()

    try:
        total = len(uploaded_files)
        all_new_docs = []

        for idx, f in enumerate(uploaded_files):
            save_path = os.path.join(DATA_DIR, f.name)
            with open(save_path, "wb") as fp:
                fp.write(f.getbuffer())
            logs.append(f"Đã lưu: **{f.name}**")
            log_area.markdown("\n\n".join(logs))
            progress_bar.progress(
                (idx + 1) / (total * 3),
                text=f"Lưu file {idx+1}/{total}...",
            )

            docs = doc_pdf_thong_minh(save_path, f.name)
            if not docs:
                logs.append(f"**{f.name}**: Không đọc được nội dung, bỏ qua.")
                log_area.markdown("\n\n".join(logs))
                continue

            all_new_docs.extend(docs)
            logs.append(f"**{f.name}**: {len(docs)} trang")
            log_area.markdown("\n\n".join(logs))
            progress_bar.progress(
                (idx + 1) / (total * 1.5),
                text=f"Đã xử lý {idx+1}/{total}...",
            )

        if not all_new_docs:
            progress_bar.empty()
            st.warning("Không trích xuất được văn bản. Kiểm tra lại file PDF.")
            return

        progress_bar.progress(0.85, text="Đang tích hợp vào Vector DB...")
        so_chunks = merge_into_existing_db(vector_db, all_new_docs, DB_DIR)
        progress_bar.progress(1.0, text="Hoàn tất!")
        logs.append(
            f"Hoàn tất! Đã thêm **{so_chunks} đoạn** từ **{total} file**."
        )
        log_area.markdown("\n\n".join(logs))
        st.success(f"Tích hợp thành công {total} tài liệu!")

        # Xóa cache để lần rerun tiếp theo load lại DB mới
        init_system_fn.clear()
        st.rerun()

    except Exception as exc:
        logger.exception("Lỗi upload & xử lý file PDF")
        progress_bar.empty()
        st.error(f"Lỗi khi xử lý: {exc}")


def _render_delete_file(filename: str, filepath: str) -> None:
    col_info, col_del = st.columns([5, 1])
    size_kb = os.path.getsize(filepath) / 1024
    mod_str = datetime.fromtimestamp(
        os.path.getmtime(filepath)
    ).strftime("%d/%m/%Y %H:%M")
    col_info.markdown(f"**{filename}**  \n{size_kb:.1f} KB · {mod_str}")

    if col_del.button("Xóa", key=f"del_pdf_{filename[:20]}"):
        st.session_state[f"_confirm_{filename}"] = True
        st.rerun()

    if st.session_state.get(f"_confirm_{filename}"):
        st.warning(f"Xác nhận xóa **{filename}**?")
        cc1, cc2 = st.columns(2)
        if cc1.button("Xác nhận", key=f"yes_{filename}"):
            try:
                os.remove(filepath)
                del st.session_state[f"_confirm_{filename}"]
                st.info(f"Đã xóa {filename}. Nhấn Rebuild DB để cập nhật.")
                st.rerun()
            except FileNotFoundError:
                # File đã bị xóa bởi process khác — clean state và tiếp tục
                del st.session_state[f"_confirm_{filename}"]
                st.warning(f"File {filename} không còn tồn tại.")
                st.rerun()
            except PermissionError:
                st.error(
                    f"Không có quyền xóa {filename}. "
                    "Kiểm tra permission của thư mục data/."
                )
            except OSError as exc:
                logger.exception("Lỗi xóa file %s", filename)
                st.error(f"Không thể xóa file: {exc}")
        if cc2.button("Hủy", key=f"no_{filename}"):
            del st.session_state[f"_confirm_{filename}"]
            st.rerun()


def _render_rebuild_button(pdf_files: list, init_system_fn) -> None:
    st.markdown("---")
    st.markdown("**Đồng bộ hóa Vector DB**")
    st.caption("Dùng khi đã xóa tài liệu hoặc muốn xây lại DB từ đầu.")

    if not st.button("Rebuild Vector DB từ tất cả tài liệu"):
        return

    with st.spinner(f"Đang rebuild từ {len(pdf_files)} file..."):
        try:
            all_docs = []
            for fname in pdf_files:
                all_docs.extend(
                    doc_pdf_thong_minh(os.path.join(DATA_DIR, fname), fname)
                )
            _, so_chunks = build_faiss_db(all_docs, db_dir=DB_DIR)
            init_system_fn.clear()
            st.success(
                f"Rebuild thành công! {so_chunks} đoạn từ {len(pdf_files)} file."
            )
            st.rerun()
        except Exception as exc:
            logger.exception("Lỗi rebuild Vector DB")
            st.error(f"Lỗi rebuild: {exc}")


def render(vector_db, init_system_fn) -> None:
    st.markdown("#### Quản lý Tài liệu RAG")
    st.markdown("Tải lên file PDF mới để mở rộng cơ sở kiến thức cho chatbot.")

    col_upload, col_list = st.columns([1, 1.3], gap="large")

    with col_upload:
        _render_upload_section(vector_db, init_system_fn)
        st.markdown("---")
        st.caption(
            "File PDF cần có thể trích xuất văn bản. "
            "Tài liệu lớn có thể mất 1-2 phút."
        )

    with col_list:
        st.markdown("**Tài liệu trong hệ thống**")
        os.makedirs(DATA_DIR, exist_ok=True)

        pdf_files = sorted(
            f for f in os.listdir(DATA_DIR) if f.lower().endswith(".pdf")
        )

        if not pdf_files:
            st.info("Chưa có tài liệu nào. Hãy tải lên PDF ở bên trái.")
            return

        tong_mb = sum(
            os.path.getsize(os.path.join(DATA_DIR, f)) for f in pdf_files
        ) / (1024 * 1024)
        c1, c2 = st.columns(2)
        c1.metric("Số tài liệu", f"{len(pdf_files)} file")
        c2.metric("Dung lượng", f"{tong_mb:.1f} MB")
        st.markdown("---")

        for filename in pdf_files:
            filepath = os.path.join(DATA_DIR, filename)
            _render_delete_file(filename, filepath)

        _render_rebuild_button(pdf_files, init_system_fn)
