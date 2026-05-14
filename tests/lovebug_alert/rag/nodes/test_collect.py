# collect_weather·collect_observations 노드를 검증하는 테스트.

from unittest.mock import patch, MagicMock
from lovebug_alert.rag.nodes.collect import collect_weather, collect_observations
from lovebug_alert.rag.state import AgentState


def _base_state() -> AgentState:
    return {
        "date": "2026-06-14",
        "weather_today": {}, "observations_today": [],
        "current_dd": 0.0, "reports_today": [],
        "risk_level": "정상", "rag_summary": "",
        "email_sent": False, "report": {},
        "citizen_answer": "", "map_path": "",
    }


def test_collect_weather_returns_25_districts():
    with patch("lovebug_alert.rag.nodes.collect.fetch_weather_archive") as mock_fetch:
        mock_fetch.return_value = MagicMock()
        with patch("lovebug_alert.rag.nodes.collect._parse_daily_mean", return_value=-2.5):
            result = collect_weather(_base_state())
    assert "weather_today" in result
    assert len(result["weather_today"]) == 25


def test_collect_observations_returns_list():
    with patch("lovebug_alert.rag.nodes.collect.fetch_gbif_today", return_value=[{"date": "2026-06-14"}]):
        result = collect_observations(_base_state())
    assert isinstance(result["observations_today"], list)
