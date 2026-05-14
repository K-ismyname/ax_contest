# compute_dd·aggregate_reports 노드를 검증하는 테스트.

import csv
import io
from unittest.mock import patch, mock_open
from lovebug_alert.rag.nodes.compute import compute_dd, aggregate_reports
from lovebug_alert.rag.state import AgentState


def _base_state(**kwargs) -> AgentState:
    base = {
        "date": "2026-06-14",
        "weather_today": {f"구{i}": {"mean_today": 20.0} for i in range(25)},
        "observations_today": [], "current_dd": 0.0,
        "reports_today": [], "risk_level": "정상",
        "rag_summary": "", "email_sent": False,
        "report": {}, "citizen_answer": "", "map_path": "",
    }
    base.update(kwargs)
    return base


def test_compute_dd_uses_existing_raw_files():
    with patch("lovebug_alert.rag.nodes.compute.compute_seoul_mean_dd") as mock_dd:
        mock_dd.return_value = {2026: {"2026-06-14": 342.0}}
        result = compute_dd(_base_state())
    assert result["current_dd"] == 342.0


def test_compute_dd_returns_zero_when_no_data():
    with patch("lovebug_alert.rag.nodes.compute.compute_seoul_mean_dd") as mock_dd:
        mock_dd.return_value = {2026: {}}
        result = compute_dd(_base_state())
    assert result["current_dd"] == 0.0


def test_aggregate_reports_filters_today(tmp_path):
    from lovebug_alert.rag.nodes.compute import REPORTS_CSV as orig
    csv_path = tmp_path / "reports.csv"
    csv_path.write_text(
        "date,location,latitude,longitude,photo_path,description,created_at\n"
        "2026-06-14,서울 은평구,37.6,126.9,,날아다님,2026-06-14T08:00:00\n"
        "2026-06-13,서울 강남구,37.5,127.0,,어제 봄,2026-06-13T10:00:00\n",
        encoding="utf-8",
    )
    with patch("lovebug_alert.rag.nodes.compute.REPORTS_CSV", csv_path):
        result = aggregate_reports(_base_state())
    assert len(result["reports_today"]) == 1
    assert result["reports_today"][0]["location"] == "서울 은평구"
