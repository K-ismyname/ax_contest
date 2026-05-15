# RAG 체인으로 담당자 대응 요약과 시민 대처법을 생성하는 노드.

from __future__ import annotations

from typing import Any

from langchain_openai import ChatOpenAI
from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate

from lovebug_alert.rag.prompts import OFFICIAL_SYSTEM, CITIZEN_SYSTEM
from lovebug_alert.rag.retriever import get_retriever
from lovebug_alert.rag.state import AgentState


def _build_chain(prompt_str: str):
    llm = ChatOpenAI(model="gpt-4o-mini", max_tokens=512)
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
    result = chain.invoke({"query": f"경보 단계 {state['risk_level']} 대응 조치"})
    return {"rag_summary": result.get("result", "")}


def rag_citizen_response(state: AgentState) -> dict[str, Any]:
    """시민 제보 후 대처법을 RAG로 생성한다."""
    location = state.get("report", {}).get("location", "서울")
    prompt = CITIZEN_SYSTEM.format(context="{context}", location=location)
    chain = _build_chain(prompt)
    result = chain.invoke({"query": "러브버그 대처법 행동 요령"})
    return {"citizen_answer": result.get("result", "")}
