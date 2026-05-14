# 시민 제보 저장 및 Folium 지도 갱신 노드 — 스텁.

from typing import Any
from lovebug_alert.rag.state import AgentState


def save_report(state: AgentState) -> dict[str, Any]:
    return {}


def update_map(state: AgentState) -> dict[str, Any]:
    return {"map_path": ""}
