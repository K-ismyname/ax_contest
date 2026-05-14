# LangGraph 에이전트의 공유 상태 스키마를 정의한다.

from __future__ import annotations

from typing import Any
from typing_extensions import TypedDict


class LovebugState(TypedDict):
    dd_current: float       # 오늘 기준 누적 도일 (DD)
    risk_level: str         # "정상" | "관심" | "주의" | "경보"
    observations: list      # GBIF·iNaturalist 관찰 기록 목록
    reports: list           # 시민 제보 목록
    prediction_date: str    # 올해 예상 첫 출현일 "YYYY-MM-DD"


class AgentState(TypedDict):
    # 공통
    date: str                      # "YYYY-MM-DD"

    # daily_graph
    weather_today: dict[str, Any]  # {district: {max, min, mean, precip}}
    observations_today: list[dict] # GBIF 관찰 기록
    current_dd: float              # 서울 평균 누적 DD (1/1 기준)
    reports_today: list[dict]      # 당일 시민 제보 목록
    risk_level: str                # "정상" | "관심" | "주의" | "경보"
    rag_summary: str               # 담당자용 RAG 대응 요약
    email_sent: bool

    # report_graph
    report: dict[str, Any]         # 시민 제보 단건
    citizen_answer: str            # RAG 시민 대처법 안내
    map_path: str                  # Folium HTML 경로
