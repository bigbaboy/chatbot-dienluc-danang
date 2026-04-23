"""
Đọc PDF thông minh với cơ chế fallback PyMuPDF → LlamaParse OCR.

Quy trình:
  1. Kiểm tra PDF có text layer hay là ảnh scan
  2. PDF có text → dùng PyMuPDF (nhanh, miễn phí)
  3. PDF ảnh/scan → dùng LlamaParse OCR (cần API key)
  4. Mọi trường hợp lỗi → fallback về PyMuPDF
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

import fitz  # PyMuPDF
from langchain_core.documents import Document

from config import LLAMA_CLOUD_API_KEY

logger = logging.getLogger(__name__)

# Ngưỡng số ký tự tối thiểu để coi 1 trang là "có nội dung"
MIN_TEXT_CHARS = 30
# Tỷ lệ trang có text tối thiểu để coi PDF là PDF text (vs scan)
TEXT_PDF_RATIO = 0.5
# Ngưỡng ký tự để tính 1 trang là "có text"
PAGE_TEXT_THRESHOLD = 50


def doc_pdf_text(path: str, source_name: str) -> List[Document]:
    """Đọc PDF có text layer bằng PyMuPDF."""
    pages: List[Document] = []
    try:
        pdf = fitz.open(path)
        for num in range(len(pdf)):
            page = pdf[num]
            text = page.get_text("text").strip()

            # Nếu ít text, thử đọc từ blocks
            if len(text) < MIN_TEXT_CHARS:
                text = "\n".join(
                    b[4] for b in page.get_text("blocks") if b[6] == 0
                ).strip()

            if len(text) > MIN_TEXT_CHARS:
                pages.append(Document(
                    page_content=text,
                    metadata={
                        "source": path,
                        "page": num,
                        "source_file": source_name,
                        "parse_method": "pymupdf",
                    },
                ))
        pdf.close()
    except Exception as exc:
        logger.error("PyMuPDF không đọc được %s: %s", source_name, exc)

    return pages


def doc_pdf_llamaparse(path: str, source_name: str) -> List[Document]:
    """Đọc PDF ảnh/scan bằng LlamaParse OCR. Fallback PyMuPDF nếu lỗi."""
    if not LLAMA_CLOUD_API_KEY or LLAMA_CLOUD_API_KEY.startswith("llx-xxx"):
        logger.warning("Chưa có LLAMA_CLOUD_API_KEY → dùng PyMuPDF")
        return doc_pdf_text(path, source_name)

    try:
        from llama_parse import LlamaParse

        parser = LlamaParse(
            api_key=LLAMA_CLOUD_API_KEY,
            result_type="text",
            language="vi",
            verbose=False,
        )
        documents = parser.load_data(path)
        pages: List[Document] = []
        for i, doc in enumerate(documents):
            text = doc.text.strip()
            if len(text) > MIN_TEXT_CHARS:
                pages.append(Document(
                    page_content=text,
                    metadata={
                        "source": path,
                        "page": i,
                        "source_file": source_name,
                        "parse_method": "llamaparse",
                    },
                ))
        return pages

    except ImportError:
        logger.warning("Chưa cài llama-parse, chạy: pip install llama-parse")
        return doc_pdf_text(path, source_name)
    except Exception as exc:
        logger.warning("Lỗi LlamaParse: %s — fallback PyMuPDF", exc)
        return doc_pdf_text(path, source_name)


def kiem_tra_pdf_co_text(path: str) -> bool:
    """Kiểm tra PDF có text hay là ảnh scan."""
    try:
        pdf = fitz.open(path)
        total = len(pdf)
        if total == 0:
            pdf.close()
            return False

        so_trang_co_text = sum(
            1 for num in range(total)
            if len(pdf[num].get_text("text").strip()) > PAGE_TEXT_THRESHOLD
        )
        pdf.close()
        return (so_trang_co_text / total) >= TEXT_PDF_RATIO

    except Exception:
        return False


def doc_pdf_thong_minh(
    path: str, source_name: Optional[str] = None
) -> List[Document]:
    """Đọc PDF thông minh, tự chọn PyMuPDF hay LlamaParse."""
    if source_name is None:
        source_name = os.path.basename(path)

    logger.info("Đang đọc: %s", source_name)

    if kiem_tra_pdf_co_text(path):
        logger.info("→ PDF text → dùng PyMuPDF")
        pages = doc_pdf_text(path, source_name)
    else:
        logger.info("→ PDF ảnh/scan → dùng LlamaParse OCR")
        pages = doc_pdf_llamaparse(path, source_name)

    logger.info("→ Đọc được %d trang", len(pages))
    return pages


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if len(sys.argv) < 2:
        print("Cách dùng: python doc_pdf_smart.py <file.pdf>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Không tìm thấy file: {file_path}")
        sys.exit(1)

    pages = doc_pdf_thong_minh(file_path)
    if pages:
        print(f"\n{'=' * 50}")
        print(f"TỔNG CỘNG: {len(pages)} trang")
        print(f"Phương pháp: {pages[0].metadata['parse_method']}")
        print(f"{'=' * 50}\n--- Nội dung trang đầu ---")
        print(pages[0].page_content[:500])
    else:
        print("Không đọc được nội dung nào.")
