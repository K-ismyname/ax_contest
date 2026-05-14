# analyze_risk 노드를 검증하는 테스트 — DD 임계값 기반 경보 레벨 판정.

import pytest
from lovebug_alert.rag.nodes.analyze import analyze_risk
from lovebug_alert.rag.state import AgentState

DD_THRESHOLD = 419.0


def _state(dd: float) -> AgentState:
    return {
        "date": "2026-06-14", "weather_today": {},
        "observations_today": [], "current_dd": dd,
        "reports_today": [], "risk_level": "정상",
        "rag_summary": "", "email_sent": False,
        "report": {}, "citizen_answer": "", "map_path": "",
    }


@pytest.mark.parametrize("dd,expected", [
    (100.0, "정상"),    # < 60% (251)
    (251.0, "관심"),    # 60% 경계
    (335.0, "주의"),    # 80% 경계
    (419.0, "경보"),    # 100% 경계
    (500.0, "경보"),    # 초과
])
def test_analyze_risk_levels(dd, expected):
    result = analyze_risk(_state(dd))
    assert result["risk_level"] == expected
