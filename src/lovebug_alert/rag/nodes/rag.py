# RAG 체인으로 담당자 대응 요약과 시민 대처법을 생성하는 노드.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_anthropic import ChatAnthropic

_HISTORY_PATH = Path("data/processed/dd_history.jsonl")


def _dd_trend_sentence() -> str:
    if not _HISTORY_PATH.exists():
        return ""
    lines = _HISTORY_PATH.read_text(encoding="utf-8").strip().splitlines()[-7:]
    entries = [json.loads(l) for l in lines if l]
    if len(entries) < 2:
        return ""
    delta = entries[-1]["current_dd"] - entries[0]["current_dd"]
    days = len(entries) - 1
    return f"최근 {days}일간 DD 변화: +{delta:.1f} (일평균 +{delta/days:.1f})."
from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate

from lovebug_alert.rag.prompts import OFFICIAL_SYSTEM, CITIZEN_SYSTEM
from lovebug_alert.rag.retriever import get_retriever
from lovebug_alert.rag.state import AgentState


def _build_chain(prompt_str: str):
    llm = ChatAnthropic(model="claude-sonnet-4-6", max_tokens=512)
    prompt = PromptTemplate.from_template(prompt_str)
    return RetrievalQA.from_chain_type(
        llm=llm,
        retriever=get_retriever(),
        chain_type_kwargs={"prompt": prompt},
        return_source_documents=False,
    )


def generate_rag_summary(state: AgentState) -> dict[str, Any]:
    """담당자용 대응 요약을 RAG로 생성한다."""
    prompt = OFFICIAL_SYSTEM.format(
        context="{context}",
        risk_level=state["risk_level"],
        current_dd=state["current_dd"],
        report_count=len(state["reports_today"]),
    )
    chain = _build_chain(prompt)
    trend = _dd_trend_sentence()
    result = chain.invoke({"query": f"{trend} 경보 단계 {state['risk_level']} 대응 조치".strip()})
    return {"rag_summary": result.get("result", "")}


def rag_citizen_response(state: AgentState) -> dict[str, Any]:
    """시민 제보 후 대처법을 RAG로 생성한다."""
    location = state.get("report", {}).get("location", "서울")
    prompt = CITIZEN_SYSTEM.format(context="{context}", location=location)
    chain = _build_chain(prompt)
    result = chain.invoke({"query": "러브버그 대처법 행동 요령"})
    return {"citizen_answer": result.get("result", "")}
