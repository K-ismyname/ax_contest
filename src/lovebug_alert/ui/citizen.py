# 시민용 러브버그 대처법 안내 및 제보 뷰.

from __future__ import annotations

import json
import os
from datetime import date as dt
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st

from lovebug_alert.ui.state_loader import (
    get_dd_ratio, get_prediction_dday, get_risk_color,
)

DD_THRESHOLD = 419.0
_LOCATION_TYPES = ["공원/녹지", "주택가", "하천/수변", "도로변", "기타"]
_SCALES = ["1~2마리", "10마리 이내", "대규모 (10마리 이상)"]
_ACTIVE_LEVELS = {"관심", "주의", "경보"}


def _search_address(query: str) -> tuple[float, float, str] | None:
    """카카오 로컬 API로 주소를 위도·경도로 변환한다."""
    api_key = os.getenv("KAKAO_API_KEY", "")
    if not api_key or not query.strip():
        return None
    url = (
        "https://dapi.kakao.com/v2/local/search/address.json?"
        + urlencode({"query": query, "size": 1})
    )
    try:
        req = Request(url, headers={"Authorization": f"KakaoAK {api_key}"})
        with urlopen(req, timeout=5) as resp:
            docs = json.loads(resp.read().decode("utf-8"))["documents"]
        if not docs:
            return None
        return float(docs[0]["y"]), float(docs[0]["x"]), docs[0]["address_name"]
    except Exception:
        return None


def _render_hero(risk_level: str, current_dd: float, date_str: str) -> None:
    color = get_risk_color(risk_level)
    today = date_str if date_str != "N/A" else dt.today().isoformat()
    dday, pred_date = get_prediction_dday(today)
    dday_label = f"D{dday:+d}" if pred_date != "N/A" else ""
    st.markdown(
        f'<div style="text-align:center;padding:20px;">'
        f'<span style="background:{color};color:white;padding:4px 14px;'
        f'border-radius:20px;font-weight:bold;font-size:1rem;">{risk_level}</span>'
        f'<h1 style="margin:10px 0;">{current_dd:.0f}'
        f'<small style="font-size:1.2rem;color:#888;"> / {DD_THRESHOLD:.0f} DD</small></h1>'
        f'<p style="color:#666;">예상 첫 출현일: <strong>{pred_date}</strong> ({dday_label})</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_action_cards(risk_level: str) -> None:
    """주의·경보 단계일 때만 출현 대응 행동 카드를 표시한다."""
    if risk_level not in _ACTIVE_LEVELS:
        st.info("🟢 현재 러브버그 출현 전 단계입니다. 출현 시기가 다가오면 행동 요령이 안내됩니다.")
        return

    st.subheader("지금 해야 할 행동")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("🪟 **창문·방충망 점검**\n\n방충망 구멍을 확인하고 야간에는 창문을 닫으세요.")
    with c2:
        st.warning("🌳 **산·공원 근처 주의**\n\n풀숲 활동 시 긴 소매 착용을 권장합니다.")
    with c3:
        st.success("📍 **발견 시 제보**\n\n아래 폼에 위치·사진을 제출해주세요. 방제에 큰 도움이 됩니다!")


def _render_report_form(app_state: dict) -> None:
    """제보 폼을 렌더링하고 제출 시 report_graph를 실행한다."""
    st.subheader("🐛 러브버그 발견 제보")

    # ── 주소 검색 (폼 외부 — 버튼 클릭 시 API 호출) ─────────────────────
    col_addr, col_btn = st.columns([3, 1])
    with col_addr:
        address_query = st.text_input(
            "발견 주소",
            placeholder="예: 서울 은평구 불광동",
            key="address_query",
        )
    with col_btn:
        st.write("")  # 버튼 수직 정렬 맞춤
        st.write("")
        if st.button("주소 검색"):
            result = _search_address(address_query)
            if result:
                st.session_state["resolved_address"] = result
            else:
                st.session_state["resolved_address"] = None
                has_key = bool(os.getenv("KAKAO_API_KEY"))
                msg = "주소를 찾지 못했습니다. 더 구체적으로 입력해주세요." if has_key \
                    else "KAKAO_API_KEY가 설정되지 않았습니다."
                st.error(msg)

    resolved = st.session_state.get("resolved_address")
    if resolved:
        st.success(f"📍 {resolved[2]}")

    # ── 제보 폼 ────────────────────────────────────────────────────────────
    with st.form("report_form"):
        location_type = st.selectbox("발견 장소", _LOCATION_TYPES)
        scale = st.radio("발견 규모", _SCALES, horizontal=True)
        photo = st.file_uploader("사진 첨부 (필수)", type=["jpg", "jpeg", "png"])
        submitted = st.form_submit_button("제보하기")

    if submitted:
        if not resolved:
            st.error("주소를 먼저 검색해주세요.")
            return
        if not photo:
            st.error("사진을 첨부해주세요. AI가 러브버그 여부를 자동으로 판별합니다.")
            return

        lat, lng, addr_name = resolved
        photo_path = ""
        save_dir = Path("data/uploads")
        save_dir.mkdir(parents=True, exist_ok=True)
        photo_path = str(save_dir / photo.name)
        (save_dir / photo.name).write_bytes(photo.read())

        report = {
            "date": dt.today().isoformat(),
            "location": addr_name,
            "latitude": lat,
            "longitude": lng,
            "photo_path": photo_path,
            "location_type": location_type,
            "scale": scale,
            "description": f"{location_type} / {scale}",
        }

        with st.spinner("사진 분석 및 AI 대처법 생성 중..."):
            try:
                from lovebug_alert.rag.graph import build_report_graph
                graph = build_report_graph()
                result = graph.invoke({
                    "date": dt.today().isoformat(),
                    "weather_today": {}, "observations_today": [],
                    "current_dd": float(app_state.get("current_dd", 0.0)),
                    "district_dd": {}, "district_risk": {},
                    "reports_today": [], "risk_level": app_state.get("risk_level", "정상"),
                    "rag_summary": "", "email_sent": False,
                    "report": report,
                    "citizen_answer": "", "map_path": "",
                    "photo_verified": None, "verification_note": "",
                })
                citizen_answer = result.get("citizen_answer", "")
                photo_verified = result.get("photo_verified")
                verification_note = result.get("verification_note", "")
            except Exception as e:
                citizen_answer = f"(AI 응답 생성 실패: {e})"
                photo_verified = None
                verification_note = ""

        # 제출 후 주소 초기화
        st.session_state["resolved_address"] = None

        st.success("제보가 접수되었습니다.")
        if photo_verified is True:
            st.success(f"✅ **러브버그 확인됨** — {verification_note}")
        elif photo_verified is False:
            st.warning(f"❌ **러브버그 미확인** — {verification_note}")
        if citizen_answer:
            st.info(f"**AI 대처법 안내**\n\n{citizen_answer}")


def _render_local_stats(current_dd: float, date_str: str) -> None:
    st.subheader("우리 동네 현황")
    today = date_str if date_str != "N/A" else dt.today().isoformat()

    dd_ratio = get_dd_ratio(current_dd)
    st.caption(f"누적 DD 진행률: {dd_ratio*100:.0f}%")
    st.progress(dd_ratio)

    st.caption("연도별 첫 출현일")
    for year, obs_date in [(2023, "2023-06-16"), (2024, "2024-06-04"), (2025, "2025-06-14")]:
        st.write(f"• {year}년: {obs_date}")

    dday, pred_date = get_prediction_dday(today)
    if pred_date != "N/A":
        st.caption(f"올해 예측 첫 출현일: **{pred_date}** (D{dday:+d})")


def _render_report_list(reports_df: pd.DataFrame) -> None:
    st.subheader("최근 제보 현황")
    if reports_df.empty:
        st.write("아직 접수된 제보가 없습니다.")
        return
    display_cols = ["date", "location", "location_type", "scale", "photo_verified", "created_at"]
    available = [c for c in display_cols if c in reports_df.columns]
    st.dataframe(
        reports_df[available].sort_values("created_at", ascending=False).head(20),
        use_container_width=True,
    )


def render_citizen_view(app_state: dict) -> None:
    """시민용 뷰를 렌더링한다."""
    risk_level = app_state.get("risk_level", "정상")
    current_dd = float(app_state.get("current_dd", 0.0))
    reports_df = app_state.get("reports_df", pd.DataFrame())
    date_str = app_state.get("date", "N/A")

    _render_hero(risk_level, current_dd, date_str)
    _render_action_cards(risk_level)
    st.divider()

    left, right = st.columns(2)
    with left:
        _render_report_form(app_state)
    with right:
        _render_local_stats(current_dd, date_str)

    st.divider()
    _render_report_list(reports_df)
