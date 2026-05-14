# DD 임계값 비교로 경보 레벨을 판정하는 노드.

from __future__ import annotations

from typing import Any

from lovebug_alert.rag.state import AgentState

DD_THRESHOLD = 419.0      # 2023~2024 평균 첫 관찰 누적 DD
WATCH_THRESHOLD = 250.0   # 관심: ~60%
CAUTION_THRESHOLD = 335.0 # 주의: ~80%


def analyze_risk(state: AgentState) -> dict[str, Any]:
    """현재 누적 DD를 임계값과 비교해 경보 레벨을 반환한다."""
    dd = state["current_dd"]

    if dd >= DD_THRESHOLD:
        level = "경보"
    elif dd >= CAUTION_THRESHOLD:
        level = "주의"
    elif dd >= WATCH_THRESHOLD:
        level = "관심"
    else:
        level = "정상"

    return {"risk_level": level}
