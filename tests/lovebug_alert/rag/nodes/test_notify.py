# notify_official·return_response 노드를 검증하는 테스트.

import json
from pathlib import Path
from unittest.mock import patch
from lovebug_alert.rag.nodes.notify import notify_official, return_response
from lovebug_alert.rag.state import AgentState


def _state(risk_level="주의", rag_summary="방제 준비 필요") -> AgentState:
    return {
        "date": "2026-06-14", "weather_today": {},
        "observations_today": [], "current_dd": 342.0,
        "reports_today": [], "risk_level": risk_level,
        "rag_summary": rag_summary, "email_sent": False,
        "report": {}, "citizen_answer": "창문을 닫으세요.", "map_path": "",
    }


def test_notify_official_writes_state_file(tmp_path):
    with patch("lovebug_alert.rag.nodes.notify.STREAMLIT_STATE_PATH", tmp_path / "state.json"):
        with patch("lovebug_alert.rag.nodes.notify._send_email", return_value=None):
            result = notify_official(_state())
    state_file = tmp_path / "state.json"
    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert data["risk_level"] == "주의"


def test_notify_official_sends_email_on_caution():
    with patch("lovebug_alert.rag.nodes.notify.STREAMLIT_STATE_PATH", Path("/tmp/test_state.json")):
        with patch("lovebug_alert.rag.nodes.notify._send_email") as mock_email:
            notify_official(_state(risk_level="주의"))
    mock_email.assert_called_once()


def test_notify_official_no_email_on_normal():
    with patch("lovebug_alert.rag.nodes.notify.STREAMLIT_STATE_PATH", Path("/tmp/test_state.json")):
        with patch("lovebug_alert.rag.nodes.notify._send_email") as mock_email:
            notify_official(_state(risk_level="정상"))
    mock_email.assert_not_called()


def test_return_response_passes_through():
    state = _state()
    result = return_response(state)
    assert result["citizen_answer"] == "창문을 닫으세요."
