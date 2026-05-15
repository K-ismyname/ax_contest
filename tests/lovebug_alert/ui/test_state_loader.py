# state_loader 순수 함수를 검증하는 테스트.

import json
import pytest
import pandas as pd
from unittest.mock import patch
from lovebug_alert.ui.state_loader import (
    load_state, load_reports_df, get_risk_color, get_dd_ratio,
    get_district_report_counts, get_prediction_dday,
)


def test_load_state_returns_defaults_when_no_file(tmp_path):
    with patch("lovebug_alert.ui.state_loader.STREAMLIT_STATE_PATH", tmp_path / "missing.json"):
        result = load_state()
    assert result["risk_level"] == "정상"
    assert result["current_dd"] == 0.0


def test_load_state_reads_json(tmp_path):
    p = tmp_path / "state.json"
    p.write_text(
        json.dumps({
            "risk_level": "주의", "current_dd": 342.0, "date": "2026-06-14",
            "reports_count": 2, "rag_summary": "방제 준비", "updated_at": "2026-06-14T07:00:00",
        }),
        encoding="utf-8",
    )
    with patch("lovebug_alert.ui.state_loader.STREAMLIT_STATE_PATH", p):
        result = load_state()
    assert result["risk_level"] == "주의"
    assert result["current_dd"] == 342.0


def test_get_risk_color():
    assert get_risk_color("경보") == "#ef4444"
    assert get_risk_color("주의") == "#f59e0b"
    assert get_risk_color("관심") == "#3b82f6"
    assert get_risk_color("정상") == "#22c55e"


def test_get_dd_ratio_caps_at_one():
    assert get_dd_ratio(419.0) == pytest.approx(1.0)
    assert get_dd_ratio(838.0) == pytest.approx(1.0)
    assert get_dd_ratio(209.5) == pytest.approx(0.5)


def test_get_district_report_counts():
    df = pd.DataFrame({"location": ["서울 은평구", "서울 강남구", "서울 은평구", "모름"]})
    counts = get_district_report_counts(df)
    assert counts.get("은평구") == 2
    assert counts.get("강남구") == 1
    assert "모름" not in counts


def test_get_prediction_dday(tmp_path):
    csv_path = tmp_path / "dd_analysis.csv"
    csv_path.write_text("year,first_obs_date\n2026,2026-06-16\n", encoding="utf-8")
    with patch("lovebug_alert.ui.state_loader.DD_ANALYSIS_CSV", csv_path):
        dday, pred_date = get_prediction_dday("2026-06-01")
    assert pred_date == "2026-06-16"
    assert dday == 15


def test_load_reports_df_returns_empty_when_no_file(tmp_path):
    with patch("lovebug_alert.ui.state_loader.REPORTS_CSV", tmp_path / "missing.csv"):
        df = load_reports_df()
    assert len(df) == 0
    assert "location" in df.columns
