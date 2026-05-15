# Streamlit 앱의 데이터 로딩·계산 순수 함수 모음.

from __future__ import annotations

import json
from datetime import date as dt
from pathlib import Path
from typing import Any

import pandas as pd

from lovebug_alert.data.open_meteo import SEOUL_DISTRICT_COORDS

STREAMLIT_STATE_PATH = Path("data/processed/streamlit_state.json")
REPORTS_CSV = Path("data/reports.csv")
DD_ANALYSIS_CSV = Path("data/processed/dd_analysis.csv")
DD_THRESHOLD = 419.0
RISK_COLORS = {
    "경보": "#ef4444",
    "주의": "#f59e0b",
    "관심": "#3b82f6",
    "정상": "#22c55e",
}


def load_state() -> dict[str, Any]:
    """streamlit_state.json을 읽어 반환한다. 파일 없으면 기본값 반환."""
    if not STREAMLIT_STATE_PATH.exists():
        return {
            "date": "N/A", "current_dd": 0.0, "risk_level": "정상",
            "reports_count": 0, "rag_summary": "", "updated_at": "N/A",
        }
    return json.loads(STREAMLIT_STATE_PATH.read_text(encoding="utf-8"))


def load_reports_df() -> pd.DataFrame:
    """reports.csv를 DataFrame으로 반환한다. 파일 없으면 빈 DataFrame."""
    if not REPORTS_CSV.exists():
        return pd.DataFrame(columns=["date", "location", "latitude", "longitude",
                                     "photo_path", "description", "created_at"])
    return pd.read_csv(REPORTS_CSV)


def get_risk_color(risk_level: str) -> str:
    """경보 단계에 대응하는 hex 색상 코드를 반환한다."""
    return RISK_COLORS.get(risk_level, "#6b7280")


def get_dd_ratio(current_dd: float) -> float:
    """현재 DD의 임계값 대비 비율을 [0.0, 1.0] 범위로 반환한다."""
    return min(current_dd / DD_THRESHOLD, 1.0)


def get_district_report_counts(reports_df: pd.DataFrame) -> dict[str, int]:
    """구별 제보 건수 딕셔너리를 반환한다 (구명 → 건수)."""
    counts: dict[str, int] = {}
    for loc in reports_df.get("location", pd.Series(dtype=str)):
        loc_str = str(loc)
        for district in SEOUL_DISTRICT_COORDS:
            if district in loc_str:
                counts[district] = counts.get(district, 0) + 1
                break
    return counts


def get_prediction_dday(today_str: str) -> tuple[int, str]:
    """dd_analysis.csv에서 올해 예상 첫 출현일과 D-day를 반환한다.

    Returns: (d_day, predicted_date_str) — d_day는 today 기준 남은 날수.
    """
    if not DD_ANALYSIS_CSV.exists():
        return 0, "N/A"

    df = pd.read_csv(DD_ANALYSIS_CSV)
    today = dt.fromisoformat(today_str)
    year = today.year

    year_row = df[df["year"] == year]
    if year_row.empty:
        return 0, "N/A"

    pred_date_str = str(year_row.iloc[0]["first_obs_date"])
    pred_date = dt.fromisoformat(pred_date_str)
    d_day = (pred_date - today).days
    return d_day, pred_date_str


def load_app_state() -> dict[str, Any]:
    """모든 앱 데이터를 통합해 반환한다."""
    state = load_state()
    state["reports_df"] = load_reports_df()
    return state
