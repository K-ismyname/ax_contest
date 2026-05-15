# daily_graph와 report_graph LangGraph 그래프를 정의한다.

from __future__ import annotations

from langgraph.graph import StateGraph, END

from lovebug_alert.rag.state import AgentState
from lovebug_alert.rag.nodes.collect import collect_weather, collect_observations
from lovebug_alert.rag.nodes.compute import compute_dd, aggregate_reports
from lovebug_alert.rag.nodes.analyze import analyze_risk, llm_risk_review
from lovebug_alert.rag.nodes.rag import generate_rag_summary, rag_citizen_response
from lovebug_alert.rag.nodes.notify import notify_official, return_response


def _risk_router(state: AgentState) -> str:
    """주의·경보면 RAG 요약 노드로, 아니면 알림 노드로 직행한다."""
    if state["risk_level"] in ("주의", "경보"):
        return "generate_rag_summary"
    return "notify_official"


def build_daily_graph():
    """매일 자동 실행되는 배치 그래프를 빌드한다."""
    g = StateGraph(AgentState)

    g.add_node("collect_weather", collect_weather)
    g.add_node("collect_observations", collect_observations)
    g.add_node("compute_dd", compute_dd)
    g.add_node("aggregate_reports", aggregate_reports)
    g.add_node("analyze_risk", analyze_risk)
    g.add_node("llm_risk_review", llm_risk_review)
    g.add_node("generate_rag_summary", generate_rag_summary)
    g.add_node("notify_official", notify_official)

    g.set_entry_point("collect_weather")
    g.add_edge("collect_weather", "collect_observations")
    g.add_edge("collect_observations", "compute_dd")
    g.add_edge("compute_dd", "aggregate_reports")
    g.add_edge("aggregate_reports", "analyze_risk")
    g.add_edge("analyze_risk", "llm_risk_review")
    g.add_conditional_edges(
        "llm_risk_review",
        _risk_router,
        {"generate_rag_summary": "generate_rag_summary", "notify_official": "notify_official"},
    )
    g.add_edge("generate_rag_summary", "notify_official")
    g.add_edge("notify_official", END)

    return g.compile()


def build_report_graph():
    """시민 제보를 처리하는 실시간 그래프를 빌드한다."""
    from lovebug_alert.rag.nodes.classify import classify_photo
    from lovebug_alert.rag.nodes.report import save_report, update_map

    g = StateGraph(AgentState)

    g.add_node("classify_photo", classify_photo)
    g.add_node("save_report", save_report)
    g.add_node("update_map", update_map)
    g.add_node("rag_citizen_response", rag_citizen_response)
    g.add_node("return_response", return_response)

    g.set_entry_point("classify_photo")
    g.add_edge("classify_photo", "save_report")
    g.add_edge("save_report", "update_map")
    g.add_edge("update_map", "rag_citizen_response")
    g.add_edge("rag_citizen_response", "return_response")
    g.add_edge("return_response", END)

    return g.compile()
