# DD 계산 및 시민 제보 집계 노드.

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from lovebug_alert.data.open_meteo import SEOUL_DISTRICT_COORDS
from lovebug_alert.features.degree_days import compute_seoul_mean_dd, load_district_dd
from lovebug_alert.rag.state import AgentState

REPORTS_CSV = Path("data/reports.csv")


def compute_dd(state: AgentState) -> dict[str, Any]:
    """1월 1일부터 오늘까지 서울 평균 및 구별 누적 DD를 반환한다."""
    year = int(state["date"][:4])
    today = state["date"]

    # 서울 평균
    dd_by_year = compute_seoul_mean_dd([year])
    current_dd = dd_by_year.get(year, {}).get(today, 0.0)

    # 구별 DD
    district_dd: dict[str, float] = {}
    for district in SEOUL_DISTRICT_COORDS:
        dd_map = load_district_dd(district, [year]).get(year, {})
        district_dd[district] = dd_map.get(today, 0.0)

    return {"current_dd": current_dd, "district_dd": district_dd}


def aggregate_reports(state: AgentState) -> dict[str, Any]:
    """data/reports.csv에서 오늘 날짜의 제보를 필터링해 반환한다."""
    today = state["date"]
    today_reports: list[dict] = []

    if not REPORTS_CSV.exists():
        return {"reports_today": []}

    with open(REPORTS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("date", "").startswith(today):
                today_reports.append(dict(row))

    return {"reports_today": today_reports}
