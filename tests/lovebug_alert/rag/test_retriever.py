# FAISS 리트리버 빌드·캐싱 로직을 검증하는 테스트.

from unittest.mock import patch, MagicMock
from lovebug_alert.rag.retriever import build_retriever, get_retriever


def test_build_retriever_returns_faiss_retriever():
    mock_faiss = MagicMock()
    mock_faiss.as_retriever.return_value = MagicMock()
    with patch("lovebug_alert.rag.retriever.OpenAIEmbeddings"):
        with patch("lovebug_alert.rag.retriever.FAISS") as mock_cls:
            mock_cls.from_documents.return_value = mock_faiss
            with patch("lovebug_alert.rag.retriever._load_documents", return_value=[MagicMock()]):
                retriever = build_retriever()
    assert retriever is not None


def test_get_retriever_caches_instance():
    import lovebug_alert.rag.retriever as mod
    sentinel = MagicMock()
    mod._retriever_cache = sentinel
    assert get_retriever() is sentinel
    mod._retriever_cache = None  # 테스트 후 초기화
