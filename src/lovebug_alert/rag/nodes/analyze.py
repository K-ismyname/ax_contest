# DD 임계값 비교로 경보 레벨을 판정하는 노드.

from __future__ import annotations

from collections import Counter
from typing import Any

from lovebug_alert.rag.state import AgentState

DD_THRESHOLD = 419.0      # 2023~2024 평균 첫 관찰 누적 DD
WATCH_THRESHOLD = 250.0   # 관심: ~60%
CAUTION_THRESHOLD = 335.0 # 주의: ~80%

LEVEL_ORDER = ["정상", "관심", "주의", "경보"]


def _dd_to_level(dd: float) -> str:
    if dd >= DD_THRESHOLD:
        return "경보"
    if dd >= CAUTION_THRESHOLD:
        return "주의"
    if dd >= WATCH_THRESHOLD:
        return "관심"
    return "정상"


def analyze_risk(state: AgentState) -> dict[str, Any]:
    """현재 누적 DD를 임계값과 비교해 서울 전체 및 구별 경보 레벨을 반환한다."""
    level = _dd_to_level(state["current_dd"])
    district_risk = {
        district: _dd_to_level(dd)
        for district, dd in state.get("district_dd", {}).items()
    }

    # 사진 검증된 제보 3건 이상인 구는 최소 "관심" 단계로 상향
    verified = [
        r for r in state.get("reports_today", [])
        if str(r.get("photo_verified")) == "True"
    ]
    verified_by_district = Counter(r["location"] for r in verified if r.get("location"))
    for district, count in verified_by_district.items():
        if district in district_risk and count >= 3:
            current_idx = LEVEL_ORDER.index(district_risk[district])
            district_risk[district] = LEVEL_ORDER[max(1, current_idx)]

    return {"risk_level": level, "district_risk": district_risk}


def llm_risk_review(state: AgentState) -> dict[str, Any]:
    """LLM이 DD와 시민 제보를 종합해 최종 경보 단계를 결정한다."""
    from langchain_anthropic import ChatAnthropic

    verified_count = sum(
        1 for r in state.get("reports_today", [])
        if str(r.get("photo_verified")) == "True"
    )
    llm = ChatAnthropic(model="claude-sonnet-4-6", max_tokens=128)
    prompt = (
        f"현재 누적 DD: {state['current_dd']:.1f} (임계값 419).\n"
        f"DD 기반 경보 단계: {state['risk_level']}.\n"
        f"오늘 시민 확인 제보: {verified_count}건.\n"
        "위 정보를 종합해 최종 경보 단계를 결정하라. "
        "반드시 '정상', '관심', '주의', '경보' 중 하나만 반환하라. 다른 텍스트 없이."
    )
    response = llm.invoke(prompt).content.strip()
    if response not in ("정상", "관심", "주의", "경보"):
        response = state["risk_level"]
    return {"risk_level": response}
