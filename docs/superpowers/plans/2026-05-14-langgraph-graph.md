# LangGraph 에이전트 구현 계획 (Plan 1/2 — 그래프 + 노드)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `daily_graph`(매일 배치)와 `report_graph`(시민 제보 실시간) 두 LangGraph 그래프를 구현하고, RAG 기반 담당자 요약·시민 안내를 포함한 전체 파이프라인을 동작시킨다.

**Architecture:** 기존 `data/` 수집 모듈과 `features/degree_days.py`를 노드 함수로 래핑한다. 각 노드는 `AgentState → dict` 순수 함수로 설계해 단위 테스트가 용이하다. RAG는 PDF를 FAISS에 인덱싱하고 LangChain의 `RetrievalQA` 체인으로 쿼리한다.

**Tech Stack:** `langgraph`, `langchain-anthropic` (Claude Sonnet), `langchain-openai` (임베딩), `faiss-cpu`, `apscheduler`, `pypdf`, `pytest`

---

## 파일 구조

```
src/lovebug_alert/rag/
├── __init__.py
├── state.py              # AgentState TypedDict
├── graph.py              # daily_graph + report_graph 조립
├── prompts.py            # RAG 프롬프트 템플릿
└── nodes/
    ├── __init__.py
    ├── collect.py        # collect_weather, collect_observations
    ├── compute.py        # compute_dd, aggregate_reports
    ├── analyze.py        # analyze_risk
    ├── rag.py            # generate_rag_summary, rag_citizen_response
    └── notify.py         # notify_official, return_response

tests/lovebug_alert/rag/
├── __init__.py
├── test_state.py
├── test_graph.py
└── nodes/
    ├── __init__.py
    ├── test_collect.py
    ├── test_compute.py
    ├── test_analyze.py
    ├── test_rag.py
    └── test_notify.py

data/
└── reports.csv           # 시민 제보 저장소 (헤더만 초기화)

scripts/
└── run_daily.py          # APScheduler 진입점
```

---

## Task 1: 의존성 설치 + 디렉터리 스캐폴딩

**Files:**
- Modify: `pyproject.toml` 또는 직접 pip install

- [ ] **Step 1: 패키지 설치**

```bash
cd "/Users/leegahee/workspace/ax 공모전"
.venv/bin/pip install \
  langgraph \
  langchain-anthropic \
  langchain-openai \
  langchain-community \
  faiss-cpu \
  apscheduler \
  pypdf \
  pytest \
  pytest-mock
```

Expected: 모두 `Successfully installed` 출력.

- [ ] **Step 2: 디렉터리 생성**

```bash
mkdir -p src/lovebug_alert/rag/nodes
mkdir -p tests/lovebug_alert/rag/nodes
touch src/lovebug_alert/rag/__init__.py
touch src/lovebug_alert/rag/nodes/__init__.py
touch tests/lovebug_alert/rag/__init__.py
touch tests/lovebug_alert/rag/nodes/__init__.py
```

- [ ] **Step 3: reports.csv 초기화**

```bash
echo "date,location,latitude,longitude,photo_path,description,created_at" > data/reports.csv
```

- [ ] **Step 4: 커밋**

```bash
git add data/reports.csv src/lovebug_alert/rag/ tests/lovebug_alert/
git commit -m "feat: rag 모듈 디렉터리 스캐폴딩 + reports.csv 초기화"
```

---

## Task 2: AgentState TypedDict

**Files:**
- Create: `src/lovebug_alert/rag/state.py`
- Create: `tests/lovebug_alert/rag/test_state.py`

- [ ] **Step 1: 테스트 작성**

`tests/lovebug_alert/rag/test_state.py`:
```python
from lovebug_alert.rag.state import AgentState


def test_agent_state_has_required_keys():
    state: AgentState = {
        "date": "2026-06-14",
        "weather_today": {},
        "observations_today": [],
        "current_dd": 0.0,
        "reports_today": [],
        "risk_level": "정상",
        "rag_summary": "",
        "email_sent": False,
        "report": {},
        "citizen_answer": "",
        "map_path": "",
    }
    assert state["date"] == "2026-06-14"
    assert state["risk_level"] == "정상"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd "/Users/leegahee/workspace/ax 공모전"
.venv/bin/pytest tests/lovebug_alert/rag/test_state.py -v
```

Expected: `ModuleNotFoundError: No module named 'lovebug_alert.rag.state'`

- [ ] **Step 3: AgentState 구현**

`src/lovebug_alert/rag/state.py`:
```python
# LangGraph 에이전트의 공유 상태 스키마를 정의한다.

from __future__ import annotations

from typing import Any
from typing_extensions import TypedDict


class AgentState(TypedDict):
    # 공통
    date: str                      # "YYYY-MM-DD"

    # daily_graph
    weather_today: dict[str, Any]  # {district: {max, min, mean, precip}}
    observations_today: list[dict] # GBIF 관찰 기록
    current_dd: float              # 서울 평균 누적 DD (1/1 기준)
    reports_today: list[dict]      # 당일 시민 제보 목록
    risk_level: str                # "정상" | "관심" | "주의" | "경보"
    rag_summary: str               # 담당자용 RAG 대응 요약
    email_sent: bool

    # report_graph
    report: dict[str, Any]         # 시민 제보 단건
    citizen_answer: str            # RAG 시민 대처법 안내
    map_path: str                  # Folium HTML 경로
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
.venv/bin/pytest tests/lovebug_alert/rag/test_state.py -v
```

Expected: `PASSED`

- [ ] **Step 5: 커밋**

```bash
git add src/lovebug_alert/rag/state.py tests/lovebug_alert/rag/test_state.py
git commit -m "feat: AgentState TypedDict 정의"
```

---

## Task 3: collect 노드 (collect_weather, collect_observations)

**Files:**
- Create: `src/lovebug_alert/rag/nodes/collect.py`
- Create: `tests/lovebug_alert/rag/nodes/test_collect.py`

- [ ] **Step 1: 테스트 작성**

`tests/lovebug_alert/rag/nodes/test_collect.py`:
```python
from unittest.mock import patch, MagicMock
from lovebug_alert.rag.nodes.collect import collect_weather, collect_observations
from lovebug_alert.rag.state import AgentState


def _base_state() -> AgentState:
    return {
        "date": "2026-06-14",
        "weather_today": {}, "observations_today": [],
        "current_dd": 0.0, "reports_today": [],
        "risk_level": "정상", "rag_summary": "",
        "email_sent": False, "report": {},
        "citizen_answer": "", "map_path": "",
    }


def test_collect_weather_returns_25_districts():
    with patch("lovebug_alert.rag.nodes.collect.fetch_weather_archive") as mock_fetch:
        mock_fetch.return_value = MagicMock()
        with patch("lovebug_alert.rag.nodes.collect._parse_daily_mean", return_value=-2.5):
            result = collect_weather(_base_state())
    assert "weather_today" in result
    assert len(result["weather_today"]) == 25


def test_collect_observations_returns_list():
    with patch("lovebug_alert.rag.nodes.collect.fetch_gbif_today", return_value=[{"date": "2026-06-14"}]):
        result = collect_observations(_base_state())
    assert isinstance(result["observations_today"], list)
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
.venv/bin/pytest tests/lovebug_alert/rag/nodes/test_collect.py -v
```

Expected: `ImportError`

- [ ] **Step 3: collect.py 구현**

`src/lovebug_alert/rag/nodes/collect.py`:
```python
# 날씨·관찰 기록 수집 노드 — Open-Meteo와 GBIF API를 호출한다.

from __future__ import annotations

import json
import time
from datetime import date as dt
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from lovebug_alert.data.open_meteo import (
    OPEN_METEO_ARCHIVE_URL,
    SEOUL_DISTRICT_COORDS,
    fetch_weather_archive,
)
from lovebug_alert.data.gbif import GBIF_OCCURRENCE_URL
from lovebug_alert.rag.state import AgentState


def _parse_daily_mean(path: Any) -> float | None:
    """저장된 JSON 파일에서 마지막 날의 평균 기온을 반환한다."""
    data = json.loads(Path(str(path)).read_text())
    means = data["daily"]["temperature_2m_mean"]
    return means[-1] if means else None


def fetch_gbif_today(date_str: str) -> list[dict]:
    """GBIF에서 특정 날짜의 Plecia longiforceps 한국 관찰 기록을 반환한다."""
    from urllib.request import Request
    params = urlencode({
        "scientificName": "Plecia longiforceps",
        "country": "KR",
        "eventDate": date_str,
        "limit": 100,
    })
    url = f"{GBIF_OCCURRENCE_URL}?{params}"
    req = Request(url, headers={"User-Agent": "lovebug-alert-prototype"})
    with urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read())
    return payload.get("results", [])


def collect_weather(state: AgentState) -> dict[str, Any]:
    """오늘 날짜 기준 서울 25개 구 기온을 수집해 state에 반환한다."""
    today = state["date"]
    year_start = f"{today[:4]}-01-01"
    weather: dict[str, Any] = {}

    for i, district in enumerate(SEOUL_DISTRICT_COORDS):
        path = fetch_weather_archive(district, year_start, today)
        mean = _parse_daily_mean(path)
        weather[district] = {"mean_today": mean}
        if i < len(SEOUL_DISTRICT_COORDS) - 1:
            time.sleep(1)  # rate limit 방지

    return {"weather_today": weather}


def collect_observations(state: AgentState) -> dict[str, Any]:
    """오늘 날짜의 GBIF 러브버그 관찰 기록을 수집한다."""
    records = fetch_gbif_today(state["date"])
    return {"observations_today": records}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
.venv/bin/pytest tests/lovebug_alert/rag/nodes/test_collect.py -v
```

Expected: `2 passed`

- [ ] **Step 5: 커밋**

```bash
git add src/lovebug_alert/rag/nodes/collect.py tests/lovebug_alert/rag/nodes/test_collect.py
git commit -m "feat: collect_weather·collect_observations 노드 구현"
```

---

## Task 4: compute 노드 (compute_dd, aggregate_reports)

**Files:**
- Create: `src/lovebug_alert/rag/nodes/compute.py`
- Create: `tests/lovebug_alert/rag/nodes/test_compute.py`

- [ ] **Step 1: 테스트 작성**

`tests/lovebug_alert/rag/nodes/test_compute.py`:
```python
import csv, io
from unittest.mock import patch, mock_open
from lovebug_alert.rag.nodes.compute import compute_dd, aggregate_reports
from lovebug_alert.rag.state import AgentState


def _base_state(**kwargs) -> AgentState:
    base = {
        "date": "2026-06-14",
        "weather_today": {f"구{i}": {"mean_today": 20.0} for i in range(25)},
        "observations_today": [], "current_dd": 0.0,
        "reports_today": [], "risk_level": "정상",
        "rag_summary": "", "email_sent": False,
        "report": {}, "citizen_answer": "", "map_path": "",
    }
    base.update(kwargs)
    return base


def test_compute_dd_uses_existing_raw_files():
    with patch("lovebug_alert.rag.nodes.compute.compute_seoul_mean_dd") as mock_dd:
        mock_dd.return_value = {2026: {"2026-06-14": 342.0}}
        result = compute_dd(_base_state())
    assert result["current_dd"] == 342.0


def test_compute_dd_returns_zero_when_no_data():
    with patch("lovebug_alert.rag.nodes.compute.compute_seoul_mean_dd") as mock_dd:
        mock_dd.return_value = {2026: {}}
        result = compute_dd(_base_state())
    assert result["current_dd"] == 0.0


def test_aggregate_reports_filters_today():
    csv_content = (
        "date,location,latitude,longitude,photo_path,description,created_at\n"
        "2026-06-14,서울 은평구,37.6,126.9,,날아다님,2026-06-14T08:00:00\n"
        "2026-06-13,서울 강남구,37.5,127.0,,어제 봄,2026-06-13T10:00:00\n"
    )
    with patch("builtins.open", mock_open(read_data=csv_content)):
        result = aggregate_reports(_base_state())
    assert len(result["reports_today"]) == 1
    assert result["reports_today"][0]["location"] == "서울 은평구"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
.venv/bin/pytest tests/lovebug_alert/rag/nodes/test_compute.py -v
```

Expected: `ImportError`

- [ ] **Step 3: compute.py 구현**

`src/lovebug_alert/rag/nodes/compute.py`:
```python
# DD 계산 및 시민 제보 집계 노드.

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from lovebug_alert.features.degree_days import compute_seoul_mean_dd
from lovebug_alert.rag.state import AgentState

REPORTS_CSV = Path("data/reports.csv")


def compute_dd(state: AgentState) -> dict[str, Any]:
    """1월 1일부터 오늘까지 서울 평균 누적 DD를 반환한다."""
    year = int(state["date"][:4])
    dd_by_year = compute_seoul_mean_dd([year])
    dd_map = dd_by_year.get(year, {})
    current_dd = dd_map.get(state["date"], 0.0)
    return {"current_dd": current_dd}


def aggregate_reports(state: AgentState) -> dict[str, Any]:
    """data/reports.csv에서 오늘 날짜의 제보를 필터링해 반환한다."""
    today = state["date"]
    today_reports: list[dict] = []

    if not REPORTS_CSV.exists():
        return {"reports_today": []}

    with open(REPORTS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("date", "").startswith(today):
                today_reports.append(dict(row))

    return {"reports_today": today_reports}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
.venv/bin/pytest tests/lovebug_alert/rag/nodes/test_compute.py -v
```

Expected: `3 passed`

- [ ] **Step 5: 커밋**

```bash
git add src/lovebug_alert/rag/nodes/compute.py tests/lovebug_alert/rag/nodes/test_compute.py
git commit -m "feat: compute_dd·aggregate_reports 노드 구현"
```

---

## Task 5: analyze_risk 노드

**Files:**
- Create: `src/lovebug_alert/rag/nodes/analyze.py`
- Create: `tests/lovebug_alert/rag/nodes/test_analyze.py`

- [ ] **Step 1: 테스트 작성**

`tests/lovebug_alert/rag/nodes/test_analyze.py`:
```python
import pytest
from lovebug_alert.rag.nodes.analyze import analyze_risk
from lovebug_alert.rag.state import AgentState

DD_THRESHOLD = 419.0


def _state(dd: float) -> AgentState:
    return {
        "date": "2026-06-14", "weather_today": {},
        "observations_today": [], "current_dd": dd,
        "reports_today": [], "risk_level": "정상",
        "rag_summary": "", "email_sent": False,
        "report": {}, "citizen_answer": "", "map_path": "",
    }


@pytest.mark.parametrize("dd,expected", [
    (100.0, "정상"),    # < 60% (251)
    (251.0, "관심"),    # 60% 경계
    (335.0, "주의"),    # 80% 경계
    (419.0, "경보"),    # 100% 경계
    (500.0, "경보"),    # 초과
])
def test_analyze_risk_levels(dd, expected):
    result = analyze_risk(_state(dd))
    assert result["risk_level"] == expected
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
.venv/bin/pytest tests/lovebug_alert/rag/nodes/test_analyze.py -v
```

Expected: `ImportError`

- [ ] **Step 3: analyze.py 구현**

`src/lovebug_alert/rag/nodes/analyze.py`:
```python
# DD 임계값 비교로 경보 레벨을 판정하는 노드.

from __future__ import annotations

from typing import Any

from lovebug_alert.rag.state import AgentState

DD_THRESHOLD = 419.0      # 2023~2024 평균 첫 관찰 누적 DD
WATCH_RATIO = 0.60        # 관심: 60%
CAUTION_RATIO = 0.80      # 주의: 80%
ALERT_RATIO = 1.00        # 경보: 100%


def analyze_risk(state: AgentState) -> dict[str, Any]:
    """현재 누적 DD를 임계값과 비교해 경보 레벨을 반환한다."""
    dd = state["current_dd"]
    ratio = dd / DD_THRESHOLD

    if ratio >= ALERT_RATIO:
        level = "경보"
    elif ratio >= CAUTION_RATIO:
        level = "주의"
    elif ratio >= WATCH_RATIO:
        level = "관심"
    else:
        level = "정상"

    return {"risk_level": level}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
.venv/bin/pytest tests/lovebug_alert/rag/nodes/test_analyze.py -v
```

Expected: `5 passed`

- [ ] **Step 5: 커밋**

```bash
git add src/lovebug_alert/rag/nodes/analyze.py tests/lovebug_alert/rag/nodes/test_analyze.py
git commit -m "feat: analyze_risk 노드 구현 (DD 3단계 경보)"
```

---

## Task 6: RAG 파이프라인 — PDF 인덱싱

**Files:**
- Create: `src/lovebug_alert/rag/retriever.py`
- Create: `tests/lovebug_alert/rag/test_retriever.py`

- [ ] **Step 1: 테스트 작성**

`tests/lovebug_alert/rag/test_retriever.py`:
```python
from unittest.mock import patch, MagicMock
from lovebug_alert.rag.retriever import build_retriever, get_retriever


def test_build_retriever_returns_faiss_retriever():
    mock_faiss = MagicMock()
    mock_faiss.as_retriever.return_value = MagicMock()
    with patch("lovebug_alert.rag.retriever.FAISS") as mock_cls:
        mock_cls.from_documents.return_value = mock_faiss
        with patch("lovebug_alert.rag.retriever._load_documents", return_value=[MagicMock()]):
            retriever = build_retriever()
    assert retriever is not None


def test_get_retriever_caches_instance():
    import lovebug_alert.rag.retriever as mod
    sentinel = MagicMock()
    mod._retriever_cache = sentinel
    assert get_retriever() is sentinel
    mod._retriever_cache = None  # 테스트 후 초기화
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
.venv/bin/pytest tests/lovebug_alert/rag/test_retriever.py -v
```

Expected: `ImportError`

- [ ] **Step 3: retriever.py 구현**

`src/lovebug_alert/rag/retriever.py`:
```python
# PDF 문서를 FAISS 벡터 스토어에 인덱싱하고 리트리버를 반환한다.

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

PDF_SOURCES = [
    Path("data/2026년 붉은등우단털파리(러브버그)대발생 대비 선제방역 및 대응계획.pdf"),
    Path("도시복합재난조기경보/docs/1._예·경보_단계별_건강취약계층_미세먼지_행동매뉴얼.pdf"),
]
FAISS_INDEX_PATH = Path("data/processed/faiss_index")

_retriever_cache: Any = None


def _load_documents() -> list:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = []
    for pdf_path in PDF_SOURCES:
        if pdf_path.exists():
            loader = PyPDFLoader(str(pdf_path))
            docs.extend(splitter.split_documents(loader.load()))
    return docs


def build_retriever():
    """PDF를 로드해 FAISS 인덱스를 빌드하고 저장한다."""
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    docs = _load_documents()
    vectorstore = FAISS.from_documents(docs, embeddings)
    FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(FAISS_INDEX_PATH))
    return vectorstore.as_retriever(search_kwargs={"k": 4})


def get_retriever():
    """캐시된 리트리버를 반환한다. 없으면 인덱스에서 로드한다."""
    global _retriever_cache
    if _retriever_cache is not None:
        return _retriever_cache

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    if FAISS_INDEX_PATH.exists():
        vectorstore = FAISS.load_local(
            str(FAISS_INDEX_PATH), embeddings, allow_dangerous_deserialization=True
        )
    else:
        vectorstore = FAISS.from_documents(_load_documents(), embeddings)
        vectorstore.save_local(str(FAISS_INDEX_PATH))

    _retriever_cache = vectorstore.as_retriever(search_kwargs={"k": 4})
    return _retriever_cache
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
.venv/bin/pytest tests/lovebug_alert/rag/test_retriever.py -v
```

Expected: `2 passed`

- [ ] **Step 5: FAISS 인덱스 실제 빌드 (API 키 필요)**

```bash
OPENAI_API_KEY=<your_key> .venv/bin/python -c "
from src.lovebug_alert.rag.retriever import build_retriever
r = build_retriever()
print('인덱스 빌드 완료')
"
```

Expected: `data/processed/faiss_index/` 디렉터리 생성.

- [ ] **Step 6: 커밋**

```bash
git add src/lovebug_alert/rag/retriever.py tests/lovebug_alert/rag/test_retriever.py
git commit -m "feat: FAISS RAG 리트리버 구현 (PDF 인덱싱)"
```

---

## Task 7: RAG 노드 + 프롬프트

**Files:**
- Create: `src/lovebug_alert/rag/prompts.py`
- Create: `src/lovebug_alert/rag/nodes/rag.py`
- Create: `tests/lovebug_alert/rag/nodes/test_rag.py`

- [ ] **Step 1: prompts.py 작성**

`src/lovebug_alert/rag/prompts.py`:
```python
# LangChain RAG 체인에 사용되는 프롬프트 템플릿.

OFFICIAL_SYSTEM = """당신은 서울시 러브버그(붉은등우단털파리) 방제 담당자를 돕는 AI입니다.
아래 참고 문서를 바탕으로 현재 경보 상황에 맞는 대응 조치를 200자 이내로 요약하세요.
문서에 없는 내용은 추측하지 마세요.

참고 문서:
{context}

현재 상황: 경보 단계={risk_level}, 누적DD={current_dd:.1f}, 오늘 제보={report_count}건
"""

CITIZEN_SYSTEM = """당신은 서울 시민에게 러브버그(붉은등우단털파리) 대처법을 안내하는 AI입니다.
아래 참고 문서를 바탕으로 일반 시민이 이해하기 쉬운 언어로 3가지 행동 요령을 알려주세요.
각 요령은 한 문장으로 작성하세요.

참고 문서:
{context}

제보 위치: {location}
"""
```

- [ ] **Step 2: 테스트 작성**

`tests/lovebug_alert/rag/nodes/test_rag.py`:
```python
from unittest.mock import patch, MagicMock
from lovebug_alert.rag.nodes.rag import generate_rag_summary, rag_citizen_response
from lovebug_alert.rag.state import AgentState


def _base_state(**kwargs) -> AgentState:
    base = {
        "date": "2026-06-14", "weather_today": {},
        "observations_today": [], "current_dd": 342.0,
        "reports_today": [{"location": "은평구"}],
        "risk_level": "주의", "rag_summary": "",
        "email_sent": False,
        "report": {"location": "서울 은평구", "date": "2026-06-14"},
        "citizen_answer": "", "map_path": "",
    }
    base.update(kwargs)
    return base


def test_generate_rag_summary_returns_string():
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = {"result": "선제 방제 준비를 권고합니다."}
    with patch("lovebug_alert.rag.nodes.rag._build_chain", return_value=mock_chain):
        result = generate_rag_summary(_base_state())
    assert isinstance(result["rag_summary"], str)
    assert len(result["rag_summary"]) > 0


def test_rag_citizen_response_returns_string():
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = {"result": "창문을 닫으세요."}
    with patch("lovebug_alert.rag.nodes.rag._build_chain", return_value=mock_chain):
        result = rag_citizen_response(_base_state())
    assert isinstance(result["citizen_answer"], str)
```

- [ ] **Step 3: 테스트 실패 확인**

```bash
.venv/bin/pytest tests/lovebug_alert/rag/nodes/test_rag.py -v
```

Expected: `ImportError`

- [ ] **Step 4: nodes/rag.py 구현**

`src/lovebug_alert/rag/nodes/rag.py`:
```python
# RAG 체인으로 담당자 대응 요약과 시민 대처법을 생성하는 노드.

from __future__ import annotations

from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

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
    result = chain.invoke({"query": f"경보 단계 {state['risk_level']} 대응 조치"})
    return {"rag_summary": result.get("result", "")}


def rag_citizen_response(state: AgentState) -> dict[str, Any]:
    """시민 제보 후 대처법을 RAG로 생성한다."""
    location = state.get("report", {}).get("location", "서울")
    prompt = CITIZEN_SYSTEM.format(context="{context}", location=location)
    chain = _build_chain(prompt)
    result = chain.invoke({"query": "러브버그 대처법 행동 요령"})
    return {"citizen_answer": result.get("result", "")}
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
.venv/bin/pytest tests/lovebug_alert/rag/nodes/test_rag.py -v
```

Expected: `2 passed`

- [ ] **Step 6: 커밋**

```bash
git add src/lovebug_alert/rag/prompts.py src/lovebug_alert/rag/nodes/rag.py tests/lovebug_alert/rag/nodes/test_rag.py
git commit -m "feat: RAG 노드 구현 (담당자 요약·시민 안내)"
```

---

## Task 8: notify 노드

**Files:**
- Create: `src/lovebug_alert/rag/nodes/notify.py`
- Create: `tests/lovebug_alert/rag/nodes/test_notify.py`

- [ ] **Step 1: 테스트 작성**

`tests/lovebug_alert/rag/nodes/test_notify.py`:
```python
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from lovebug_alert.rag.nodes.notify import notify_official, return_response
from lovebug_alert.rag.state import AgentState


def _state(risk_level="주의", rag_summary="방제 준비 필요") -> AgentState:
    return {
        "date": "2026-06-14", "weather_today": {},
        "observations_today": [], "current_dd": 342.0,
        "reports_today": [], "risk_level": risk_level,
        "rag_summary": rag_summary, "email_sent": False,
        "report": {}, "citizen_answer": "창문을 닫으세요.", "map_path": "",
    }


def test_notify_official_writes_state_file(tmp_path):
    with patch("lovebug_alert.rag.nodes.notify.STREAMLIT_STATE_PATH", tmp_path / "state.json"):
        with patch("lovebug_alert.rag.nodes.notify._send_email", return_value=None):
            result = notify_official(_state())
    state_file = tmp_path / "state.json"
    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert data["risk_level"] == "주의"


def test_notify_official_sends_email_on_caution():
    with patch("lovebug_alert.rag.nodes.notify.STREAMLIT_STATE_PATH", Path("/tmp/test_state.json")):
        with patch("lovebug_alert.rag.nodes.notify._send_email") as mock_email:
            notify_official(_state(risk_level="주의"))
    mock_email.assert_called_once()


def test_notify_official_no_email_on_normal():
    with patch("lovebug_alert.rag.nodes.notify.STREAMLIT_STATE_PATH", Path("/tmp/test_state.json")):
        with patch("lovebug_alert.rag.nodes.notify._send_email") as mock_email:
            notify_official(_state(risk_level="정상"))
    mock_email.assert_not_called()


def test_return_response_passes_through():
    state = _state()
    result = return_response(state)
    assert result["citizen_answer"] == "창문을 닫으세요."
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
.venv/bin/pytest tests/lovebug_alert/rag/nodes/test_notify.py -v
```

Expected: `ImportError`

- [ ] **Step 3: notify.py 구현**

`src/lovebug_alert/rag/nodes/notify.py`:
```python
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
        "risk_level": state["risk_level"],
        "reports_count": len(state["reports_today"]),
        "rag_summary": state["rag_summary"],
        "updated_at": datetime.now().isoformat(),
    }
    STREAMLIT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STREAMLIT_STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

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
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
.venv/bin/pytest tests/lovebug_alert/rag/nodes/test_notify.py -v
```

Expected: `4 passed`

- [ ] **Step 5: 커밋**

```bash
git add src/lovebug_alert/rag/nodes/notify.py tests/lovebug_alert/rag/nodes/test_notify.py
git commit -m "feat: notify_official·return_response 노드 구현"
```

---

## Task 9: daily_graph 조립

**Files:**
- Create: `src/lovebug_alert/rag/graph.py`
- Create: `tests/lovebug_alert/rag/test_graph.py`

- [ ] **Step 1: 테스트 작성**

`tests/lovebug_alert/rag/test_graph.py`:
```python
from unittest.mock import patch, MagicMock
from lovebug_alert.rag.graph import build_daily_graph, build_report_graph


def _mock_nodes():
    """모든 노드를 패스스루 mock으로 대체한다."""
    return {
        "lovebug_alert.rag.nodes.collect.collect_weather": lambda s: {"weather_today": {}},
        "lovebug_alert.rag.nodes.collect.collect_observations": lambda s: {"observations_today": []},
        "lovebug_alert.rag.nodes.compute.compute_dd": lambda s: {"current_dd": 342.0},
        "lovebug_alert.rag.nodes.compute.aggregate_reports": lambda s: {"reports_today": []},
        "lovebug_alert.rag.nodes.analyze.analyze_risk": lambda s: {"risk_level": "주의"},
        "lovebug_alert.rag.nodes.rag.generate_rag_summary": lambda s: {"rag_summary": "방제 준비"},
        "lovebug_alert.rag.nodes.notify.notify_official": lambda s: {"email_sent": True},
    }


def test_daily_graph_compiles():
    graph = build_daily_graph()
    assert graph is not None


def test_daily_graph_skips_rag_on_normal(monkeypatch):
    """정상 단계에서는 generate_rag_summary가 호출되지 않아야 한다."""
    rag_called = []

    def mock_rag(state):
        rag_called.append(True)
        return {"rag_summary": ""}

    with patch("lovebug_alert.rag.graph.collect_weather", lambda s: {"weather_today": {}}), \
         patch("lovebug_alert.rag.graph.collect_observations", lambda s: {"observations_today": []}), \
         patch("lovebug_alert.rag.graph.compute_dd", lambda s: {"current_dd": 100.0}), \
         patch("lovebug_alert.rag.graph.aggregate_reports", lambda s: {"reports_today": []}), \
         patch("lovebug_alert.rag.graph.analyze_risk", lambda s: {"risk_level": "정상"}), \
         patch("lovebug_alert.rag.graph.generate_rag_summary", mock_rag), \
         patch("lovebug_alert.rag.graph.notify_official", lambda s: {"email_sent": False}):
        graph = build_daily_graph()
        graph.invoke({"date": "2026-06-14", "weather_today": {}, "observations_today": [],
                      "current_dd": 0.0, "reports_today": [], "risk_level": "정상",
                      "rag_summary": "", "email_sent": False, "report": {},
                      "citizen_answer": "", "map_path": ""})

    assert len(rag_called) == 0


def test_report_graph_compiles():
    graph = build_report_graph()
    assert graph is not None
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
.venv/bin/pytest tests/lovebug_alert/rag/test_graph.py -v
```

Expected: `ImportError`

- [ ] **Step 3: graph.py 구현**

`src/lovebug_alert/rag/graph.py`:
```python
# daily_graph와 report_graph LangGraph 그래프를 정의한다.

from __future__ import annotations

from langgraph.graph import StateGraph, END

from lovebug_alert.rag.state import AgentState
from lovebug_alert.rag.nodes.collect import collect_weather, collect_observations
from lovebug_alert.rag.nodes.compute import compute_dd, aggregate_reports
from lovebug_alert.rag.nodes.analyze import analyze_risk
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
    g.add_node("generate_rag_summary", generate_rag_summary)
    g.add_node("notify_official", notify_official)

    g.set_entry_point("collect_weather")
    g.add_edge("collect_weather", "collect_observations")
    g.add_edge("collect_observations", "compute_dd")
    g.add_edge("compute_dd", "aggregate_reports")
    g.add_edge("aggregate_reports", "analyze_risk")
    g.add_conditional_edges(
        "analyze_risk",
        _risk_router,
        {"generate_rag_summary": "generate_rag_summary", "notify_official": "notify_official"},
    )
    g.add_edge("generate_rag_summary", "notify_official")
    g.add_edge("notify_official", END)

    return g.compile()


def build_report_graph():
    """시민 제보를 처리하는 실시간 그래프를 빌드한다."""
    from lovebug_alert.rag.nodes.collect import collect_weather  # noqa: F401 (unused in report)
    from lovebug_alert.rag.nodes.notify import return_response
    from lovebug_alert.rag.nodes.rag import rag_citizen_response

    # report_graph 전용 노드 임포트
    from lovebug_alert.rag.nodes.report import save_report, update_map

    g = StateGraph(AgentState)

    g.add_node("save_report", save_report)
    g.add_node("update_map", update_map)
    g.add_node("rag_citizen_response", rag_citizen_response)
    g.add_node("return_response", return_response)

    g.set_entry_point("save_report")
    g.add_edge("save_report", "update_map")
    g.add_edge("update_map", "rag_citizen_response")
    g.add_edge("rag_citizen_response", "return_response")
    g.add_edge("return_response", END)

    return g.compile()
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
.venv/bin/pytest tests/lovebug_alert/rag/test_graph.py -v
```

Expected: `3 passed`

- [ ] **Step 5: 커밋**

```bash
git add src/lovebug_alert/rag/graph.py tests/lovebug_alert/rag/test_graph.py
git commit -m "feat: daily_graph·report_graph LangGraph 조립"
```

---

## Task 10: report 노드 + APScheduler 진입점

**Files:**
- Create: `src/lovebug_alert/rag/nodes/report.py`
- Create: `scripts/run_daily.py`
- Create: `tests/lovebug_alert/rag/nodes/test_report.py`

- [ ] **Step 1: 테스트 작성**

`tests/lovebug_alert/rag/nodes/test_report.py`:
```python
import csv
from pathlib import Path
from unittest.mock import patch
from lovebug_alert.rag.nodes.report import save_report, update_map
from lovebug_alert.rag.state import AgentState


def _state(location="서울 은평구") -> AgentState:
    return {
        "date": "2026-06-14", "weather_today": {},
        "observations_today": [], "current_dd": 342.0,
        "reports_today": [], "risk_level": "주의",
        "rag_summary": "", "email_sent": False,
        "report": {"date": "2026-06-14", "location": location,
                   "latitude": 37.6, "longitude": 126.9,
                   "photo_path": "", "description": "발견"},
        "citizen_answer": "", "map_path": "",
    }


def test_save_report_appends_to_csv(tmp_path):
    csv_path = tmp_path / "reports.csv"
    csv_path.write_text("date,location,latitude,longitude,photo_path,description,created_at\n")
    with patch("lovebug_alert.rag.nodes.report.REPORTS_CSV", csv_path):
        save_report(_state())
    rows = list(csv.DictReader(csv_path.open()))
    assert len(rows) == 1
    assert rows[0]["location"] == "서울 은평구"


def test_update_map_returns_map_path(tmp_path):
    with patch("lovebug_alert.rag.nodes.report.MAP_OUTPUT_PATH", tmp_path / "map.html"):
        with patch("lovebug_alert.rag.nodes.report.REPORTS_CSV") as mock_csv:
            mock_csv.exists.return_value = False
            result = update_map(_state())
    assert "map_path" in result
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
.venv/bin/pytest tests/lovebug_alert/rag/nodes/test_report.py -v
```

Expected: `ImportError`

- [ ] **Step 3: nodes/report.py 구현**

`src/lovebug_alert/rag/nodes/report.py`:
```python
# 시민 제보 저장 및 Folium 지도 갱신 노드.

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

import folium

from lovebug_alert.rag.state import AgentState

REPORTS_CSV = Path("data/reports.csv")
MAP_OUTPUT_PATH = Path("data/processed/report_map.html")


def save_report(state: AgentState) -> dict[str, Any]:
    """제보를 reports.csv에 추가한다."""
    report = state["report"]
    row = {
        "date": report.get("date", state["date"]),
        "location": report.get("location", ""),
        "latitude": report.get("latitude", ""),
        "longitude": report.get("longitude", ""),
        "photo_path": report.get("photo_path", ""),
        "description": report.get("description", ""),
        "created_at": datetime.now().isoformat(),
    }
    REPORTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    write_header = not REPORTS_CSV.exists()
    with open(REPORTS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)
    return {}


def update_map(state: AgentState) -> dict[str, Any]:
    """전체 제보 목록으로 Folium 지도를 재생성한다."""
    m = folium.Map(location=[37.5665, 126.9780], zoom_start=11)

    if REPORTS_CSV.exists():
        with open(REPORTS_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    lat, lng = float(row["latitude"]), float(row["longitude"])
                    folium.CircleMarker(
                        [lat, lng],
                        radius=6,
                        color="red",
                        fill=True,
                        popup=f"{row['date']} {row['location']}",
                    ).add_to(m)
                except (ValueError, KeyError):
                    continue

    MAP_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(MAP_OUTPUT_PATH))
    return {"map_path": str(MAP_OUTPUT_PATH)}
```

- [ ] **Step 4: run_daily.py 작성**

`scripts/run_daily.py`:
```python
# APScheduler로 daily_graph를 매일 오전 7시에 실행한다.

from datetime import date
from apscheduler.schedulers.blocking import BlockingScheduler

import sys
sys.path.insert(0, "src")

from lovebug_alert.rag.graph import build_daily_graph

daily_graph = build_daily_graph()


def run_daily():
    today = date.today().isoformat()
    print(f"[daily_graph] {today} 실행 시작")
    result = daily_graph.invoke({
        "date": today,
        "weather_today": {}, "observations_today": [],
        "current_dd": 0.0, "reports_today": [],
        "risk_level": "정상", "rag_summary": "",
        "email_sent": False, "report": {},
        "citizen_answer": "", "map_path": "",
    })
    print(f"[daily_graph] 완료 — 경보: {result['risk_level']}, DD: {result['current_dd']:.1f}")


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="Asia/Seoul")
    scheduler.add_job(run_daily, "cron", hour=7, minute=0)
    print("스케줄러 시작 (매일 07:00 KST)")
    scheduler.start()
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
.venv/bin/pytest tests/lovebug_alert/rag/nodes/test_report.py -v
```

Expected: `2 passed`

- [ ] **Step 6: 전체 테스트 실행**

```bash
.venv/bin/pytest tests/lovebug_alert/rag/ -v
```

Expected: 모든 테스트 `passed`

- [ ] **Step 7: 커밋**

```bash
git add src/lovebug_alert/rag/nodes/report.py scripts/run_daily.py tests/lovebug_alert/rag/nodes/test_report.py
git commit -m "feat: report 노드 + APScheduler 진입점 구현"
```

---

## 스펙 커버리지 자가 검토

| 스펙 항목 | 담당 Task |
|---|---|
| daily_graph 7개 노드 | Task 3~5, 7~9 |
| report_graph 5개 노드 | Task 7~10 |
| 3단계 경보 (DD 기준) | Task 5 |
| RAG 담당자 요약 | Task 6~7 |
| RAG 시민 챗봇 | Task 7 |
| Streamlit 상태 파일 갱신 | Task 8 |
| 이메일 발송 (주의 이상) | Task 8 |
| APScheduler 7시 트리거 | Task 10 |
| Folium 지도 갱신 | Task 10 |
| Streamlit UI (시민·담당자 뷰) | **Plan 2에서 구현** |
