# PDF 문서를 FAISS 벡터 스토어에 인덱싱하고 리트리버를 반환한다.

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

PDF_SOURCES = [
    Path("data/2026년 붉은등우단털파리(러브버그)대발생 대비 선제방역 및 대응계획.pdf"),
    Path("도시복합재난조기경보/docs/1._예·경보_단계별_건강취약계층_미세먼지_행동매뉴얼.pdf"),
]
FAISS_INDEX_PATH = Path("data/processed/faiss_index")

_retriever_cache: Any = None


def _load_documents() -> list:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = []
    for pdf_path in PDF_SOURCES:
        if pdf_path.exists():
            loader = PyPDFLoader(str(pdf_path))
            docs.extend(splitter.split_documents(loader.load()))
    return docs


def build_retriever():
    """PDF를 로드해 FAISS 인덱스를 빌드하고 저장한다."""
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    docs = _load_documents()
    vectorstore = FAISS.from_documents(docs, embeddings)
    FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(FAISS_INDEX_PATH))
    return vectorstore.as_retriever(search_kwargs={"k": 4})


def get_retriever():
    """캐시된 리트리버를 반환한다. 없으면 인덱스에서 로드한다."""
    global _retriever_cache
    if _retriever_cache is not None:
        return _retriever_cache

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    if FAISS_INDEX_PATH.exists():
        vectorstore = FAISS.load_local(
            str(FAISS_INDEX_PATH), embeddings, allow_dangerous_deserialization=True
        )
    else:
        vectorstore = FAISS.from_documents(_load_documents(), embeddings)
        vectorstore.save_local(str(FAISS_INDEX_PATH))

    _retriever_cache = vectorstore.as_retriever(search_kwargs={"k": 4})
    return _retriever_cache
