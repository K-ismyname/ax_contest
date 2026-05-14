# daily_graph·report_graph 조립을 검증하는 테스트.

from unittest.mock import patch
from lovebug_alert.rag.graph import build_daily_graph, build_report_graph


def test_daily_graph_compiles():
    graph = build_daily_graph()
    assert graph is not None


def test_daily_graph_skips_rag_on_normal():
    """정상 단계에서는 generate_rag_summary가 호출되지 않아야 한다."""
    rag_called = []

    def mock_rag(state):
        rag_called.append(True)
        return {"rag_summary": ""}

    with patch("lovebug_alert.rag.graph.collect_weather", lambda s: {"weather_today": {}}), \
         patch("lovebug_alert.rag.graph.collect_observations", lambda s: {"observations_today": []}), \
         patch("lovebug_alert.rag.graph.compute_dd", lambda s: {"current_dd": 100.0}), \
         patch("lovebug_alert.rag.graph.aggregate_reports", lambda s: {"reports_today": []}), \
         patch("lovebug_alert.rag.graph.analyze_risk", lambda s: {"risk_level": "정상"}), \
         patch("lovebug_alert.rag.graph.generate_rag_summary", mock_rag), \
         patch("lovebug_alert.rag.graph.notify_official", lambda s: {"email_sent": False}):
        graph = build_daily_graph()
        graph.invoke({
            "date": "2026-06-14", "weather_today": {}, "observations_today": [],
            "current_dd": 0.0, "reports_today": [], "risk_level": "정상",
            "rag_summary": "", "email_sent": False, "report": {},
            "citizen_answer": "", "map_path": "",
        })

    assert len(rag_called) == 0


def test_report_graph_compiles():
    graph = build_report_graph()
    assert graph is not None
