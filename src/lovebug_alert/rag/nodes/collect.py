# 날씨·관찰 기록 수집 노드 — Open-Meteo와 GBIF API를 호출한다.

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from lovebug_alert.data.open_meteo import SEOUL_DISTRICT_COORDS, fetch_weather_archive
from lovebug_alert.data.gbif import GBIF_OCCURRENCE_URL
from lovebug_alert.rag.state import AgentState


def _parse_daily_mean(path: Any) -> float | None:
    """저장된 JSON 파일에서 마지막 날의 평균 기온을 반환한다."""
    data = json.loads(Path(str(path)).read_text())
    means = data["daily"]["temperature_2m_mean"]
    return means[-1] if means else None


def fetch_gbif_today(date_str: str) -> list[dict]:
    """GBIF에서 특정 날짜의 Plecia longiforceps 한국 관찰 기록을 반환한다."""
    params = urlencode({
        "scientificName": "Plecia longiforceps",
        "country": "KR",
        "eventDate": date_str,
        "limit": 100,
    })
    url = f"{GBIF_OCCURRENCE_URL}?{params}"
    req = Request(url, headers={"User-Agent": "lovebug-alert-prototype"})
    with urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read())
    return payload.get("results", [])


def collect_weather(state: AgentState) -> dict[str, Any]:
    """오늘 날짜 기준 서울 25개 구 기온을 수집해 state에 반환한다."""
    today = state["date"]
    year_start = f"{today[:4]}-01-01"
    weather: dict[str, Any] = {}

    for i, district in enumerate(SEOUL_DISTRICT_COORDS):
        path = fetch_weather_archive(district, year_start, today)
        mean = _parse_daily_mean(path)
        weather[district] = {"mean_today": mean}
        if i < len(SEOUL_DISTRICT_COORDS) - 1:
            time.sleep(1)

    return {"weather_today": weather}


def collect_observations(state: AgentState) -> dict[str, Any]:
    """오늘 날짜의 GBIF 러브버그 관찰 기록을 수집한다."""
    records = fetch_gbif_today(state["date"])
    return {"observations_today": records}
