# save_report·update_map 노드를 검증하는 테스트.

import csv
from pathlib import Path
from unittest.mock import patch
from lovebug_alert.rag.nodes.report import save_report, update_map
from lovebug_alert.rag.state import AgentState


def _state(location="서울 은평구") -> AgentState:
    return {
        "date": "2026-06-14", "weather_today": {},
        "observations_today": [], "current_dd": 342.0,
        "reports_today": [], "risk_level": "주의",
        "rag_summary": "", "email_sent": False,
        "report": {
            "date": "2026-06-14", "location": location,
            "latitude": 37.6, "longitude": 126.9,
            "photo_path": "", "description": "발견",
        },
        "citizen_answer": "", "map_path": "",
    }


def test_save_report_appends_to_csv(tmp_path):
    csv_path = tmp_path / "reports.csv"
    csv_path.write_text(
        "date,location,latitude,longitude,photo_path,description,created_at\n",
        encoding="utf-8",
    )
    with patch("lovebug_alert.rag.nodes.report.REPORTS_CSV", csv_path):
        save_report(_state())
    rows = list(csv.DictReader(csv_path.open()))
    assert len(rows) == 1
    assert rows[0]["location"] == "서울 은평구"


def test_update_map_returns_map_path(tmp_path):
    with patch("lovebug_alert.rag.nodes.report.MAP_OUTPUT_PATH", tmp_path / "map.html"):
        with patch("lovebug_alert.rag.nodes.report.REPORTS_CSV") as mock_csv:
            mock_csv.exists.return_value = False
            result = update_map(_state())
    assert "map_path" in result
    assert result["map_path"] != ""
