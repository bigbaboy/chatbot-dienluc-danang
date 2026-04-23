from __future__ import annotations
import logging
import os
from typing import List, Optional, Tuple
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DB_DIR,
    EMBEDDING_MODEL,
    SEPARATORS,
)

logger = logging.getLogger(__name__)


_embeddings: Optional[HuggingFaceEmbeddings] = None


def get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


def split_documents(documents: List[Document]) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=SEPARATORS,
    )
    return splitter.split_documents(documents)


def build_faiss_db(documents: List[Document], db_dir: str = DB_DIR) -> Tuple[FAISS, int]:
    chunks = split_documents(documents)
    if not chunks:
        raise ValueError("Không có chunk nào để build FAISS DB.")

    logger.info("Building FAISS DB từ %d chunks...", len(chunks))
    db = FAISS.from_documents(chunks, get_embeddings())
    db.save_local(db_dir)
    logger.info("Đã lưu FAISS DB vào: %s", db_dir)
    return db, len(chunks)


def merge_into_existing_db(
    base_db: FAISS, new_documents: List[Document], db_dir: str = DB_DIR
) -> int:
    chunks = split_documents(new_documents)
    if not chunks:
        return 0

    new_db = FAISS.from_documents(chunks, get_embeddings())
    base_db.merge_from(new_db)
    base_db.save_local(db_dir)
    logger.info("Merged %d chunks vào FAISS DB.", len(chunks))
    return len(chunks)


def faiss_db_exists(db_dir: str = DB_DIR) -> bool:
    return os.path.isfile(os.path.join(db_dir, "index.faiss"))


def load_faiss_db(db_dir: str = DB_DIR) -> Optional[FAISS]:
    if not faiss_db_exists(db_dir):
        return None

    try:
        return FAISS.load_local(
            db_dir, get_embeddings(), allow_dangerous_deserialization=True
        )
    except Exception as exc:
        logger.error("Lỗi load FAISS DB từ %s: %s", db_dir, exc)
        raise
