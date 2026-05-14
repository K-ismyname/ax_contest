# AgentState TypedDict 스키마를 검증하는 테스트.

from lovebug_alert.rag.state import AgentState


def test_agent_state_has_required_keys():
    state: AgentState = {
        "date": "2026-06-14",
        "weather_today": {},
        "observations_today": [],
        "current_dd": 0.0,
        "reports_today": [],
        "risk_level": "정상",
        "rag_summary": "",
        "email_sent": False,
        "report": {},
        "citizen_answer": "",
        "map_path": "",
    }
    assert state["date"] == "2026-06-14"
    assert state["risk_level"] == "정상"
