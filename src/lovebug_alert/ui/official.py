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
    get_dd_ratio, get_district_report_counts, get_historical_district_counts,
    get_prediction_dday, get_risk_color,
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


def _bubble_marker(lat: float, lng: float, obs: int, max_count: int, today_reports: int, district: str) -> folium.Marker:
    ratio = obs / max_count if max_count else 0
    size = int(28 + ratio * 36)  # 28px ~ 64px
    if obs >= 8:
        bg, border = "#ef4444", "#b91c1c"
    elif obs >= 4:
        bg, border = "#f97316", "#c2410c"
    elif obs >= 1:
        bg, border = "#3b82f6", "#1d4ed8"
    else:
        bg, border = "#d1d5db", "#9ca3af"

    text_color = "#fff" if obs >= 1 else "#6b7280"
    font_size = max(9, min(13, size // 3))
    count_label = str(obs) if obs > 0 else "·"
    report_badge = (
        f'<div style="position:absolute;top:-4px;right:-4px;width:14px;height:14px;'
        f'border-radius:50%;background:#fff;border:2px solid {bg};'
        f'display:flex;align-items:center;justify-content:center;'
        f'font-size:8px;font-weight:700;color:{bg};">{today_reports}</div>'
    ) if today_reports else ""

    html = (
        f'<div style="position:relative;width:{size}px;height:{size}px;">'
        f'<div style="width:{size}px;height:{size}px;border-radius:50%;'
        f'background:{bg};border:2px solid {border};'
        f'box-shadow:0 2px 8px rgba(0,0,0,0.25);'
        f'display:flex;align-items:center;justify-content:center;">'
        f'<span style="color:{text_color};font-size:{font_size}px;font-weight:700;'
        f'font-family:sans-serif;line-height:1;">{count_label}</span>'
        f'</div>{report_badge}</div>'
    )

    popup_lines = [f"<b>{district}</b>", f"2025년 관측: {obs}건"]
    if today_reports:
        popup_lines.append(f"오늘 확인 제보: {today_reports}건")

    return folium.Marker(
        [lat, lng],
        icon=folium.DivIcon(
            html=html,
            icon_size=(size, size),
            icon_anchor=(size // 2, size // 2),
        ),
        popup=folium.Popup("<br>".join(popup_lines), max_width=160),
        tooltip=folium.Tooltip(f"{district} {obs}건", sticky=True),
    )


def _render_district_map(reports_df: pd.DataFrame) -> None:
    st.subheader("서울 구별 러브버그 출몰 현황 (2025년 실제 관측 데이터)")
    st.caption("iNaturalist 2025 관측 기록 · 원 크기 = 관측 건수 · 흰 배지 = 오늘 시민 확인 제보")

    hist_counts = get_historical_district_counts(year=2025)
    report_counts = get_district_report_counts(reports_df, verified_only=True)
    max_count = max(hist_counts.values(), default=1)

    m = folium.Map(
        location=[37.5665, 126.9780],
        zoom_start=11,
        tiles="CartoDB positron",
    )
    for district, (lat, lng) in SEOUL_DISTRICT_COORDS.items():
        obs = hist_counts.get(district, 0)
        today_reports = report_counts.get(district, 0)
        _bubble_marker(lat, lng, obs, max_count, today_reports, district).add_to(m)
    components.html(m._repr_html_(), height=450)


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
    _render_district_map(reports_df)
