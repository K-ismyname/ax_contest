# Streamlit 대시보드 구현 계획 (Plan 2/2 — UI)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 담당자·시민 뷰를 토글로 전환하는 Streamlit 대시보드를 구현한다.

**Architecture:** `app.py`를 진입점으로, `src/lovebug_alert/ui/` 아래 state_loader(순수 함수), official(담당자 뷰), citizen(시민 뷰) 세 모듈로 분리한다. `data/processed/streamlit_state.json`(daily_graph 출력)과 `data/reports.csv`를 UI 데이터 소스로 사용한다.

**Tech Stack:** `streamlit`, `folium`, `pandas`, `lovebug_alert.rag.graph` (report_graph)

---

## 파일 구조

```
app.py                              # streamlit run app.py (프로젝트 루트)
src/lovebug_alert/ui/
├── __init__.py
├── state_loader.py                 # 순수 데이터 로딩·계산 함수
├── official.py                     # render_official_view()
└── citizen.py                      # render_citizen_view() + 제보 폼
tests/lovebug_alert/ui/
├── __init__.py
└── test_state_loader.py            # 순수 함수 단위 테스트
```

---

## Task 1: UI 모듈 스캐폴딩 + streamlit 설치

**Files:**
- Create: `src/lovebug_alert/ui/__init__.py`
- Create: `tests/lovebug_alert/ui/__init__.py`

- [ ] **Step 1: streamlit 설치**

```bash
cd "/Users/leegahee/workspace/ax 공모전"
.venv/bin/pip install streamlit
```

Expected: `Successfully installed streamlit-...` 또는 `already satisfied`.

- [ ] **Step 2: 디렉터리 + `__init__.py` 생성**

```bash
cd "/Users/leegahee/workspace/ax 공모전"
mkdir -p src/lovebug_alert/ui
mkdir -p tests/lovebug_alert/ui
touch src/lovebug_alert/ui/__init__.py
touch tests/lovebug_alert/ui/__init__.py
```

- [ ] **Step 3: 커밋**

```bash
cd "/Users/leegahee/workspace/ax 공모전"
git add src/lovebug_alert/ui/ tests/lovebug_alert/ui/
git commit -m "feat: Streamlit UI 모듈 스캐폴딩"
```

---

## Task 2: state_loader.py (순수 함수 + 테스트)

**Files:**
- Create: `src/lovebug_alert/ui/state_loader.py`
- Create: `tests/lovebug_alert/ui/test_state_loader.py`

- [ ] **Step 1: 테스트 작성**

`tests/lovebug_alert/ui/test_state_loader.py`:
```python
# state_loader 순수 함수를 검증하는 테스트.

import json
import pytest
import pandas as pd
from unittest.mock import patch
from lovebug_alert.ui.state_loader import (
    load_state, load_reports_df, get_risk_color, get_dd_ratio,
    get_district_report_counts, get_prediction_dday,
)


def test_load_state_returns_defaults_when_no_file(tmp_path):
    with patch("lovebug_alert.ui.state_loader.STREAMLIT_STATE_PATH", tmp_path / "missing.json"):
        result = load_state()
    assert result["risk_level"] == "정상"
    assert result["current_dd"] == 0.0


def test_load_state_reads_json(tmp_path):
    p = tmp_path / "state.json"
    p.write_text(
        json.dumps({
            "risk_level": "주의", "current_dd": 342.0, "date": "2026-06-14",
            "reports_count": 2, "rag_summary": "방제 준비", "updated_at": "2026-06-14T07:00:00",
        }),
        encoding="utf-8",
    )
    with patch("lovebug_alert.ui.state_loader.STREAMLIT_STATE_PATH", p):
        result = load_state()
    assert result["risk_level"] == "주의"
    assert result["current_dd"] == 342.0


def test_get_risk_color():
    assert get_risk_color("경보") == "#ef4444"
    assert get_risk_color("주의") == "#f59e0b"
    assert get_risk_color("관심") == "#3b82f6"
    assert get_risk_color("정상") == "#22c55e"


def test_get_dd_ratio_caps_at_one():
    assert get_dd_ratio(419.0) == pytest.approx(1.0)
    assert get_dd_ratio(838.0) == pytest.approx(1.0)
    assert get_dd_ratio(209.5) == pytest.approx(0.5)


def test_get_district_report_counts():
    df = pd.DataFrame({"location": ["서울 은평구", "서울 강남구", "서울 은평구", "모름"]})
    counts = get_district_report_counts(df)
    assert counts.get("은평구") == 2
    assert counts.get("강남구") == 1
    assert "모름" not in counts


def test_get_prediction_dday(tmp_path):
    csv_path = tmp_path / "dd_analysis.csv"
    csv_path.write_text("year,first_obs_date\n2026,2026-06-16\n", encoding="utf-8")
    with patch("lovebug_alert.ui.state_loader.DD_ANALYSIS_CSV", csv_path):
        dday, pred_date = get_prediction_dday("2026-06-01")
    assert pred_date == "2026-06-16"
    assert dday == 15


def test_load_reports_df_returns_empty_when_no_file(tmp_path):
    with patch("lovebug_alert.ui.state_loader.REPORTS_CSV", tmp_path / "missing.csv"):
        df = load_reports_df()
    assert len(df) == 0
    assert "location" in df.columns
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd "/Users/leegahee/workspace/ax 공모전"
.venv/bin/pytest tests/lovebug_alert/ui/test_state_loader.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: state_loader.py 구현**

`src/lovebug_alert/ui/state_loader.py`:
```python
# Streamlit 앱의 데이터 로딩·계산 순수 함수 모음.

from __future__ import annotations

import json
from datetime import date as dt
from pathlib import Path
from typing import Any

import pandas as pd

from lovebug_alert.data.open_meteo import SEOUL_DISTRICT_COORDS

STREAMLIT_STATE_PATH = Path("data/processed/streamlit_state.json")
REPORTS_CSV = Path("data/reports.csv")
DD_ANALYSIS_CSV = Path("data/processed/dd_analysis.csv")
DD_THRESHOLD = 419.0
RISK_COLORS = {
    "경보": "#ef4444",
    "주의": "#f59e0b",
    "관심": "#3b82f6",
    "정상": "#22c55e",
}


def load_state() -> dict[str, Any]:
    """streamlit_state.json을 읽어 반환한다. 파일 없으면 기본값 반환."""
    if not STREAMLIT_STATE_PATH.exists():
        return {
            "date": "N/A", "current_dd": 0.0, "risk_level": "정상",
            "reports_count": 0, "rag_summary": "", "updated_at": "N/A",
        }
    return json.loads(STREAMLIT_STATE_PATH.read_text(encoding="utf-8"))


def load_reports_df() -> pd.DataFrame:
    """reports.csv를 DataFrame으로 반환한다. 파일 없으면 빈 DataFrame."""
    if not REPORTS_CSV.exists():
        return pd.DataFrame(columns=["date", "location", "latitude", "longitude",
                                     "photo_path", "description", "created_at"])
    return pd.read_csv(REPORTS_CSV)


def get_risk_color(risk_level: str) -> str:
    """경보 단계에 대응하는 hex 색상 코드를 반환한다."""
    return RISK_COLORS.get(risk_level, "#6b7280")


def get_dd_ratio(current_dd: float) -> float:
    """현재 DD의 임계값 대비 비율을 [0.0, 1.0] 범위로 반환한다."""
    return min(current_dd / DD_THRESHOLD, 1.0)


def get_district_report_counts(reports_df: pd.DataFrame) -> dict[str, int]:
    """구별 제보 건수 딕셔너리를 반환한다 (구명 → 건수)."""
    counts: dict[str, int] = {}
    for loc in reports_df.get("location", pd.Series(dtype=str)):
        loc_str = str(loc)
        for district in SEOUL_DISTRICT_COORDS:
            if district in loc_str:
                counts[district] = counts.get(district, 0) + 1
                break
    return counts


def get_prediction_dday(today_str: str) -> tuple[int, str]:
    """dd_analysis.csv에서 올해 예상 첫 출현일과 D-day를 반환한다.

    Returns: (d_day, predicted_date_str) — d_day는 today 기준 남은 날수.
    """
    if not DD_ANALYSIS_CSV.exists():
        return 0, "N/A"

    df = pd.read_csv(DD_ANALYSIS_CSV)
    today = dt.fromisoformat(today_str)
    year = today.year

    year_row = df[df["year"] == year]
    if year_row.empty:
        return 0, "N/A"

    pred_date_str = str(year_row.iloc[0]["first_obs_date"])
    pred_date = dt.fromisoformat(pred_date_str)
    d_day = (pred_date - today).days
    return d_day, pred_date_str


def load_app_state() -> dict[str, Any]:
    """모든 앱 데이터를 통합해 반환한다."""
    state = load_state()
    state["reports_df"] = load_reports_df()
    return state
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd "/Users/leegahee/workspace/ax 공모전"
.venv/bin/pytest tests/lovebug_alert/ui/test_state_loader.py -v
```

Expected: `6 passed`.

- [ ] **Step 5: 커밋**

```bash
cd "/Users/leegahee/workspace/ax 공모전"
git add src/lovebug_alert/ui/state_loader.py tests/lovebug_alert/ui/test_state_loader.py
git commit -m "feat: UI state_loader 순수 함수 구현"
```

---

## Task 3: 담당자 뷰 (official.py)

**Files:**
- Create: `src/lovebug_alert/ui/official.py`

(Streamlit 렌더링 함수는 `st.*` 의존성으로 단위 테스트 불가 — 임포트 검증 + 앱 실행으로 확인)

- [ ] **Step 1: official.py 구현**

`src/lovebug_alert/ui/official.py`:
```python
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
    district_counts = get_district_report_counts(reports_df)
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


def _render_district_map(reports_df: pd.DataFrame) -> None:
    left, right = st.columns(2)
    district_counts = get_district_report_counts(reports_df)
    sorted_districts = sorted(district_counts.items(), key=lambda x: x[1], reverse=True)

    with left:
        st.subheader("구별 제보 순위")
        if sorted_districts:
            for i, (name, count) in enumerate(sorted_districts[:10], 1):
                tag = "🔴" if count >= 3 else "🟡" if count >= 1 else "🟢"
                st.write(f"{i}. {tag} {name} — {count}건")
        else:
            st.write("오늘 접수된 제보가 없습니다.")

    with right:
        st.subheader("서울 제보 지도")
        m = folium.Map(location=[37.5665, 126.9780], zoom_start=11)
        for district, (lat, lng) in SEOUL_DISTRICT_COORDS.items():
            count = district_counts.get(district, 0)
            color = "red" if count >= 3 else "orange" if count >= 1 else "lightgray"
            folium.CircleMarker(
                [lat, lng],
                radius=8 + count * 2,
                color=color,
                fill=True,
                fill_opacity=0.6,
                popup=f"{district}: {count}건",
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
    _render_district_map(reports_df)
```

- [ ] **Step 2: 임포트 검증**

```bash
cd "/Users/leegahee/workspace/ax 공모전"
.venv/bin/python -c "from lovebug_alert.ui.official import render_official_view; print('OK')"
```

Expected: `OK`.

- [ ] **Step 3: 커밋**

```bash
cd "/Users/leegahee/workspace/ax 공모전"
git add src/lovebug_alert/ui/official.py
git commit -m "feat: 담당자 뷰 렌더링 컴포넌트 구현"
```

---

## Task 4: 시민 뷰 (citizen.py)

**Files:**
- Create: `src/lovebug_alert/ui/citizen.py`

- [ ] **Step 1: citizen.py 구현**

`src/lovebug_alert/ui/citizen.py`:
```python
# 시민용 러브버그 대처법 안내 및 제보 뷰.

from __future__ import annotations

from datetime import date as dt
from pathlib import Path

import pandas as pd
import streamlit as st

from lovebug_alert.ui.state_loader import (
    get_dd_ratio, get_prediction_dday, get_risk_color,
)

DD_THRESHOLD = 419.0


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


def _render_action_cards() -> None:
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
    with st.form("report_form"):
        location = st.text_input("발견 위치 (예: 서울 은평구 불광동)")
        col_lat, col_lng = st.columns(2)
        with col_lat:
            lat = st.number_input("위도", value=37.5665, format="%.4f")
        with col_lng:
            lng = st.number_input("경도", value=126.9780, format="%.4f")
        description = st.text_area("상황 설명 (선택)", placeholder="예: 창문에 20마리 이상 붙어 있음")
        photo = st.file_uploader("사진 첨부 (선택)", type=["jpg", "jpeg", "png"])
        submitted = st.form_submit_button("제보하기")

    if submitted and location:
        photo_path = ""
        if photo:
            save_dir = Path("data/uploads")
            save_dir.mkdir(parents=True, exist_ok=True)
            photo_path = str(save_dir / photo.name)
            (save_dir / photo.name).write_bytes(photo.read())

        report = {
            "date": dt.today().isoformat(),
            "location": location,
            "latitude": lat,
            "longitude": lng,
            "photo_path": photo_path,
            "description": description,
        }

        with st.spinner("AI 대처법 생성 중..."):
            try:
                from lovebug_alert.rag.graph import build_report_graph
                graph = build_report_graph()
                result = graph.invoke({
                    "date": dt.today().isoformat(),
                    "weather_today": {}, "observations_today": [],
                    "current_dd": float(app_state.get("current_dd", 0.0)),
                    "reports_today": [], "risk_level": app_state.get("risk_level", "정상"),
                    "rag_summary": "", "email_sent": False,
                    "report": report,
                    "citizen_answer": "", "map_path": "",
                })
                citizen_answer = result.get("citizen_answer", "")
            except Exception as e:
                citizen_answer = f"(AI 응답 생성 실패: {e})"

        st.success("제보가 접수되었습니다!")
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
    display_cols = ["date", "location", "description", "created_at"]
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
    _render_action_cards()
    st.divider()

    left, right = st.columns(2)
    with left:
        _render_report_form(app_state)
    with right:
        _render_local_stats(current_dd, date_str)

    st.divider()
    _render_report_list(reports_df)
```

- [ ] **Step 2: 임포트 검증**

```bash
cd "/Users/leegahee/workspace/ax 공모전"
.venv/bin/python -c "from lovebug_alert.ui.citizen import render_citizen_view; print('OK')"
```

Expected: `OK`.

- [ ] **Step 3: 커밋**

```bash
cd "/Users/leegahee/workspace/ax 공모전"
git add src/lovebug_alert/ui/citizen.py
git commit -m "feat: 시민 뷰 렌더링 컴포넌트 구현 (제보 폼 포함)"
```

---

## Task 5: app.py 진입점 + 전체 검증

**Files:**
- Create: `app.py`

- [ ] **Step 1: app.py 작성**

`app.py`:
```python
# Streamlit 러브버그 조기경보 시스템 진입점.

import streamlit as st

from lovebug_alert.ui.state_loader import load_app_state
from lovebug_alert.ui.official import render_official_view
from lovebug_alert.ui.citizen import render_citizen_view

st.set_page_config(
    page_title="러브버그 조기경보 시스템",
    page_icon="🐛",
    layout="wide",
)

col_logo, col_toggle = st.columns([5, 1])
with col_logo:
    st.title("🐛 러브버그 조기경보 시스템")
with col_toggle:
    is_official = st.toggle("담당자 뷰", value=True)

app_state = load_app_state()

if is_official:
    render_official_view(app_state)
else:
    render_citizen_view(app_state)
```

- [ ] **Step 2: 임포트 smoke test**

```bash
cd "/Users/leegahee/workspace/ax 공모전"
.venv/bin/python -c "import app; print('OK')" 2>&1 | head -5
```

Expected: `OK` (streamlit이 실제로 렌더링을 시도하지 않으므로 임포트만 검증).

만약 `ScriptRunContext` 오류가 나면 정상입니다 — Streamlit이 서버 컨텍스트 없이 실행될 때 발생하는 경고이며 앱 실행에는 문제 없습니다.

- [ ] **Step 3: UI 테스트 포함 전체 테스트 실행**

```bash
cd "/Users/leegahee/workspace/ax 공모전"
.venv/bin/pytest tests/ -v --tb=short 2>&1 | tail -15
```

Expected: 기존 24개 + 신규 6개 = **30 passed**.

- [ ] **Step 4: 커밋**

```bash
cd "/Users/leegahee/workspace/ax 공모전"
git add app.py
git commit -m "feat: Streamlit 대시보드 진입점 (담당자·시민 뷰 토글)"
```

---

## 스펙 커버리지 자가 검토

| 스펙 항목 | 담당 Task |
|---|---|
| 상단 담당자·시민 토글 | Task 5 (app.py) |
| 담당자 경보 배너 (색상 코딩) | Task 3 |
| 담당자 4개 지표 카드 | Task 3 |
| DD 경보 단계 progress bar | Task 3 |
| 자동 방제 권고 섹션 (주의 이상) | Task 3 |
| 이메일 발송 버튼 | Task 3 |
| 방제 체크리스트 | Task 3 |
| 구별 제보 순위 리스트 | Task 3 |
| 서울시 구별 Folium 지도 | Task 3 |
| 시민 경보 배지 + 대형 DD 숫자 | Task 4 |
| 시민 3개 행동 안내 카드 | Task 4 |
| 시민 제보 폼 (위치·사진·설명) | Task 4 |
| 제보 후 RAG 시민 대처법 안내 | Task 4 |
| DD 진행률 바 + 연도별 발생 이력 | Task 4 |
| 올해 예측 첫 출현일 D-day | Task 4 |
| 최근 제보 현황 목록 | Task 4 |
