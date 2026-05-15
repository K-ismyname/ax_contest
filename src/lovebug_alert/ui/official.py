# 담당자용 러브버그 조기경보 대시보드 뷰.

from __future__ import annotations

from datetime import date as dt
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from lovebug_alert.data.open_meteo import SEOUL_DISTRICT_COORDS
from lovebug_alert.ui.state_loader import (
    get_dd_ratio, get_district_report_counts, get_prediction_dday, get_risk_color,
)

_VERIFIED_NOTE = "✅ Vision AI 검증 제보만 집계"

DD_THRESHOLD = 419.0


def _render_risk_banner(risk_level: str, current_dd: float, date_str: str) -> None:
    color = get_risk_color(risk_level)
    ratio = get_dd_ratio(current_dd)
    st.markdown(
        f'<div style="background:{color};padding:12px;border-radius:8px;'
        f'color:white;font-size:1.1rem;margin-bottom:8px;">'
        f'🚨 <strong>{risk_level}</strong> 단계 | 누적 DD: {current_dd:.1f} / {DD_THRESHOLD:.0f}'
        f' ({ratio*100:.0f}%) | {date_str}</div>',
        unsafe_allow_html=True,
    )


def _render_metric_cards(current_dd: float, reports_df: pd.DataFrame, date_str: str) -> None:
    today = date_str if date_str != "N/A" else dt.today().isoformat()
    dday, pred_date = get_prediction_dday(today)
    district_counts = get_district_report_counts(reports_df, verified_only=True)
    high_risk = [d for d, c in district_counts.items() if c >= 1]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("누적 DD", f"{current_dd:.1f}", f"{get_dd_ratio(current_dd)*100:.0f}% / 임계값")
    with col2:
        dday_label = f"D{dday:+d}" if pred_date != "N/A" else "N/A"
        st.metric("예상 첫 출현일", pred_date, dday_label)
    with col3:
        st.metric("오늘 시민 제보", f"{len(reports_df)}건")
    with col4:
        names = "·".join(high_risk[:3]) + ("..." if len(high_risk) > 3 else "")
        st.metric("제보 구 수", f"{len(high_risk)}개", names or "없음")


def _render_dd_progress(current_dd: float) -> None:
    st.caption("DD 경보 단계 진행")
    col_n, col_w, col_c, col_a = st.columns(4)
    with col_n:
        st.markdown("🟢 **정상** < 251")
    with col_w:
        st.markdown("🔵 **관심** 251~335")
    with col_c:
        st.markdown("🟡 **주의** 335~419")
    with col_a:
        st.markdown("🔴 **경보** ≥ 419")
    st.progress(get_dd_ratio(current_dd))


def _render_rag_section(risk_level: str, rag_summary: str) -> None:
    if risk_level not in ("주의", "경보"):
        return
    st.divider()
    st.subheader("📋 자동 방제 권고")
    st.info(rag_summary or "일일 분석(scripts/run_daily.py) 실행 후 요약이 생성됩니다.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📧 담당자 이메일 발송"):
            st.toast("환경변수(SMTP_HOST, SMTP_USER, SMTP_PASS, NOTIFY_EMAIL)를 설정한 후 daily_graph 실행 시 자동 발송됩니다.")
    with c2:
        with st.expander("✅ 방제 체크리스트"):
            st.markdown(
                "- [ ] 주요 공원·학교 주변 방제 약품 준비\n"
                "- [ ] 민원 대응 매뉴얼 숙지\n"
                "- [ ] 자치구 담당자 공유\n"
                "- [ ] 시민 안내방송 검토\n"
            )


_RISK_FOLIUM_COLOR = {"경보": "red", "주의": "orange", "관심": "blue", "정상": "lightgray"}
_RISK_EMOJI = {"경보": "🔴", "주의": "🟡", "관심": "🔵", "정상": "🟢"}


def _render_district_map(reports_df: pd.DataFrame, app_state: dict) -> None:
    left, right = st.columns(2)
    district_dd: dict[str, float] = app_state.get("district_dd", {})
    district_risk: dict[str, str] = app_state.get("district_risk", {})
    report_counts = get_district_report_counts(reports_df, verified_only=True)

    # 경보 단계 → DD 높은 순으로 정렬
    sorted_districts = sorted(
        district_dd.items(), key=lambda x: x[1], reverse=True
    )

    with left:
        st.subheader("구별 경보 현황")
        st.caption(_VERIFIED_NOTE)
        for name, dd_val in sorted_districts[:10]:
            level = district_risk.get(name, "정상")
            count = report_counts.get(name, 0)
            emoji = _RISK_EMOJI[level]
            count_label = f" · 제보 {count}건" if count else ""
            st.write(f"{emoji} **{name}** — DD {dd_val:.0f} ({level}){count_label}")

    with right:
        st.subheader("서울 구별 경보 지도")
        m = folium.Map(location=[37.5665, 126.9780], zoom_start=11)
        for district, (lat, lng) in SEOUL_DISTRICT_COORDS.items():
            level = district_risk.get(district, "정상")
            dd_val = district_dd.get(district, 0.0)
            count = report_counts.get(district, 0)
            color = _RISK_FOLIUM_COLOR[level]
            folium.CircleMarker(
                [lat, lng],
                radius=10,
                color=color,
                fill=True,
                fill_opacity=0.7,
                popup=f"{district}<br>DD: {dd_val:.0f} | {level}<br>확인 제보: {count}건",
            ).add_to(m)
        components.html(m._repr_html_(), height=380)


def render_official_view(app_state: dict) -> None:
    """담당자용 뷰를 렌더링한다."""
    risk_level = app_state.get("risk_level", "정상")
    current_dd = float(app_state.get("current_dd", 0.0))
    reports_df = app_state.get("reports_df", pd.DataFrame())
    rag_summary = app_state.get("rag_summary", "")
    date_str = app_state.get("date", "N/A")

    _render_risk_banner(risk_level, current_dd, date_str)
    _render_metric_cards(current_dd, reports_df, date_str)
    _render_dd_progress(current_dd)
    _render_rag_section(risk_level, rag_summary)
    st.divider()
    _render_district_map(reports_df, app_state)
