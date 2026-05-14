# RAG 노드 (담당자 요약·시민 대처법) 를 검증하는 테스트.

from unittest.mock import patch, MagicMock
from lovebug_alert.rag.nodes.rag import generate_rag_summary, rag_citizen_response
from lovebug_alert.rag.state import AgentState


def _base_state(**kwargs) -> AgentState:
    base = {
        "date": "2026-06-14", "weather_today": {},
        "observations_today": [], "current_dd": 342.0,
        "reports_today": [{"location": "은평구"}],
        "risk_level": "주의", "rag_summary": "",
        "email_sent": False,
        "report": {"location": "서울 은평구", "date": "2026-06-14"},
        "citizen_answer": "", "map_path": "",
    }
    base.update(kwargs)
    return base


def test_generate_rag_summary_returns_string():
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = {"result": "선제 방제 준비를 권고합니다."}
    with patch("lovebug_alert.rag.nodes.rag._build_chain", return_value=mock_chain):
        result = generate_rag_summary(_base_state())
    assert isinstance(result["rag_summary"], str)
    assert len(result["rag_summary"]) > 0


def test_rag_citizen_response_returns_string():
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = {"result": "창문을 닫으세요."}
    with patch("lovebug_alert.rag.nodes.rag._build_chain", return_value=mock_chain):
        result = rag_citizen_response(_base_state())
    assert isinstance(result["citizen_answer"], str)
