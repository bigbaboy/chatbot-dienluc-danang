from __future__ import annotations
import logging
import os
import sys
import time
from typing import List
from langchain_core.documents import Document
from config import CHUNK_OVERLAP, CHUNK_SIZE, DATA_DIR, DB_DIR
from db_manager import build_faiss_db
from doc_pdf_smart import doc_pdf_thong_minh

logger = logging.getLogger(__name__)


def lay_danh_sach_pdf() -> List[str]:
    if not os.path.isdir(DATA_DIR):
        print(f"[LỖI] Không tìm thấy thư mục: {DATA_DIR}")
        print("      Hãy tạo thư mục 'data/' và đặt file PDF vào.")
        sys.exit(1)
    pdf_files = sorted(
        f for f in os.listdir(DATA_DIR) if f.lower().endswith(".pdf")
    )
    if not pdf_files:
        print(f"[LỖI] Không có file PDF nào trong: {DATA_DIR}")
        sys.exit(1)

    return pdf_files


def doc_tat_ca_pdf(pdf_files: List[str]) -> List[Document]:
    all_docs: List[Document] = []
    for pdf_file in pdf_files:
        file_path = os.path.join(DATA_DIR, pdf_file)
        try:
            docs = doc_pdf_thong_minh(file_path, pdf_file)
            all_docs.extend(docs)
            print(f"    → OK: {len(docs)} trang từ {pdf_file}")
        except Exception as exc:
            print(f"    → [LỖI] {pdf_file}: {exc}")
    return all_docs


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 60)
    print("  TẠO VECTOR DATABASE — CHATBOT ĐIỆN LỰC ĐÀ NẴNG")
    print("=" * 60)
    start = time.time()

    pdf_files = lay_danh_sach_pdf()
    print(f"\n[1/3] Tìm thấy {len(pdf_files)} file PDF:")
    for f in pdf_files:
        print(f"      - {f}")

    print("\n[2/3] Đọc các file PDF...")
    all_docs = doc_tat_ca_pdf(pdf_files)
    print(f"\n      Tổng cộng: {len(all_docs)} trang từ {len(pdf_files)} file")

    if not all_docs:
        print("[LỖI] Không đọc được trang nào. Kiểm tra lại file PDF.")
        sys.exit(1)

    print(f"\n[3/3] Build Vector DB (chunk_size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
    _, so_chunks = build_faiss_db(all_docs, db_dir=DB_DIR)

    elapsed = time.time() - start
    print(f"\n{'=' * 60}")
    print(f"  HOÀN THÀNH! ({elapsed:.1f} giây)")
    print(f"  - {len(pdf_files)} file PDF")
    print(f"  - {len(all_docs)} trang")
    print(f"  - {so_chunks} đoạn văn bản")
    print(f"  - Lưu tại: {DB_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
