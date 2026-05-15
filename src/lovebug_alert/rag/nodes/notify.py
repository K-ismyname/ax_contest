# 담당자 알림 노드 — Streamlit 상태 파일 갱신 및 이메일 발송.

from __future__ import annotations

import json
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from lovebug_alert.rag.state import AgentState

STREAMLIT_STATE_PATH = Path("data/processed/streamlit_state.json")
HISTORY_PATH = Path("data/processed/dd_history.jsonl")
NOTIFY_LEVELS = {"주의", "경보"}


def _send_email(subject: str, body: str) -> None:
    """환경변수 SMTP_* 설정이 있을 때만 이메일을 발송한다."""
    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    to_addr = os.getenv("NOTIFY_EMAIL")

    if not all([smtp_host, smtp_user, smtp_pass, to_addr]):
        return

    msg = MIMEText(body, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_addr

    with smtplib.SMTP_SSL(smtp_host, 465) as server:
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


def notify_official(state: AgentState) -> dict[str, Any]:
    """Streamlit 상태 파일을 갱신하고 주의 이상 시 이메일을 발송한다."""
    payload = {
        "date": state["date"],
        "current_dd": state["current_dd"],
        "district_dd": state.get("district_dd", {}),
        "district_risk": state.get("district_risk", {}),
        "risk_level": state["risk_level"],
        "reports_count": len(state["reports_today"]),
        "rag_summary": state["rag_summary"],
        "updated_at": datetime.now().isoformat(),
    }
    STREAMLIT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STREAMLIT_STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    history_entry = {
        "date": state["date"],
        "current_dd": state["current_dd"],
        "risk_level": state["risk_level"],
        "verified_reports": sum(
            1 for r in state["reports_today"] if str(r.get("photo_verified")) == "True"
        ),
    }
    with open(HISTORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(history_entry, ensure_ascii=False) + "\n")

    if state["risk_level"] in NOTIFY_LEVELS:
        subject = f"[러브버그 경보] {state['risk_level']} 단계 — {state['date']}"
        body = f"""
<h2>러브버그 {state['risk_level']} 단계 발령</h2>
<p>누적 DD: {state['current_dd']:.1f} / 임계값 419</p>
<p>오늘 시민 제보: {len(state['reports_today'])}건</p>
<hr>
<h3>대응 요약</h3>
<p>{state['rag_summary']}</p>
"""
        _send_email(subject, body)

    return {"email_sent": state["risk_level"] in NOTIFY_LEVELS}


def return_response(state: AgentState) -> dict[str, Any]:
    """시민 RAG 안내 문구를 그대로 반환한다 (Streamlit이 읽는 용도)."""
    return {"citizen_answer": state["citizen_answer"]}
