# LangGraph 에이전트 설계 스펙

**날짜:** 2026-05-14  
**범위:** `rag/graph.py` 중심의 LangGraph 에이전트 구조

---

## 1. 배경 및 목표

러브버그(Plecia longiforceps) 조기경보 시스템의 핵심 로직을 LangGraph 에이전트로 구현한다.

- 매일 자동으로 기상 데이터와 관찰 기록을 수집해 누적 DD를 계산하고 경보 레벨을 판정한다.
- 시민이 Streamlit UI에서 제보하면 즉시 처리하고 RAG 기반 대처법을 안내한다.
- 담당자는 Streamlit 대시보드에서 현황을 확인하고, 주의 이상 시 이메일로 알림을 받는다.

---

## 2. 그래프 구조

두 개의 독립된 그래프로 분리한다.

### 2-1. `daily_graph` — 매일 자동 실행 (APScheduler로 오전 7시 트리거)

```
collect_weather → collect_observations → compute_dd
    → aggregate_reports → analyze_risk
    → (주의 이상) generate_rag_summary
    → notify_official
```

| 노드 | 역할 | 입력 | 출력 |
|---|---|---|---|
| `collect_weather` | Open-Meteo API로 오늘 서울 25구 기온 수집 | `date` | `weather_today` |
| `collect_observations` | GBIF API로 최신 관찰 기록 수집 | `date` | `observations_today` |
| `compute_dd` | 누적 DD 계산 (base=10°C, 1/1 누적) | `weather_today` | `current_dd` |
| `aggregate_reports` | `data/reports.csv`에서 당일 시민 제보 집계 | `date` | `reports_today` |
| `analyze_risk` | DD 임계값 비교 → 경보 레벨 판정 | `current_dd` | `risk_level` |
| `generate_rag_summary` | 매뉴얼 PDF → 담당자 대응 요약 생성 | `risk_level`, `current_dd`, `reports_today` | `rag_summary` |
| `notify_official` | Streamlit 상태 파일 갱신 + 이메일 발송 | `risk_level`, `rag_summary` | `email_sent` |

**조건부 엣지:** `analyze_risk` → `generate_rag_summary`는 `risk_level`이 "주의" 또는 "경보"일 때만 실행. "정상"·"관심"이면 `generate_rag_summary`를 건너뛰고 `notify_official`로 직행.

### 2-2. `report_graph` — 시민 제보 시 실행

```
receive_report → save_report → update_map
    → rag_citizen_response → return_response
```

| 노드 | 역할 | 입력 | 출력 |
|---|---|---|---|
| `receive_report` | Streamlit 폼 데이터 수신 (날짜·위치·사진) | Streamlit form payload | `report` |
| `save_report` | `data/reports.csv`에 행 추가 | `report` | 저장 확인 |
| `update_map` | Folium 지도 HTML 재생성 | `report` | `map_path` |
| `rag_citizen_response` | 매뉴얼 PDF → 시민 대처법 안내 생성 | `report` | `citizen_answer` |
| `return_response` | Streamlit UI에 안내 문구 반환 | `citizen_answer` | 화면 출력 |

---

## 3. 경보 단계

DD 임계값 **419** (2023~2024년 평균) 기준.

| 단계 | DD 조건 | 기준값 | 조치 |
|---|---|---|---|
| 정상 | DD < 251 | < 60% | Streamlit 현황 표시만 |
| 관심 | 251 ≤ DD < 335 | 60~80% | Streamlit 강조 표시 |
| 주의 | 335 ≤ DD < 419 | 80~100% | 이메일 발송 + RAG 요약 |
| 경보 | DD ≥ 419 | ≥ 100% | 이메일 발송 + RAG 요약 |

---

## 4. AgentState 스키마

```python
class AgentState(TypedDict):
    # 공통
    date: str                    # "YYYY-MM-DD"

    # daily_graph
    weather_today: dict          # {district: {max, min, mean}}
    observations_today: list     # GBIF 관찰 기록
    current_dd: float            # 서울 평균 누적 DD
    reports_today: list          # 당일 시민 제보 목록
    risk_level: str              # "정상" | "관심" | "주의" | "경보"
    rag_summary: str             # 담당자용 대응 요약
    email_sent: bool

    # report_graph
    report: dict                 # 시민 제보 단건
    citizen_answer: str          # RAG 시민 안내 문구
    map_path: str                # Folium HTML 경로
```

---

## 5. 파일 구조

```
src/lovebug_alert/
├── data/                        # 기존 수집 모듈
│   ├── open_meteo.py
│   ├── gbif.py
│   └── merge_observations.py
├── features/
│   └── degree_days.py           # 기존 DD 계산
└── rag/
    ├── graph.py                 # LangGraph 그래프 정의 (daily + report)
    ├── nodes/
    │   ├── collect.py           # collect_weather, collect_observations
    │   ├── compute.py           # compute_dd, aggregate_reports
    │   ├── analyze.py           # analyze_risk
    │   ├── rag.py               # generate_rag_summary, rag_citizen_response
    │   └── notify.py            # notify_official, return_response
    ├── state.py                 # AgentState TypedDict
    └── prompts.py               # RAG 프롬프트 템플릿
```

---

## 6. RAG 소스 문서

`도시복합재난조기경보/docs/` 아래 PDF 두 건.

- `[교육부] 고농도 미세먼지 대응 실무매뉴얼` — 담당자 대응 절차
- `[보건복지부] 어린이집·노인요양시설 매뉴얼` — 취약계층 대응

임베딩: `text-embedding-3-small`, 청크 크기 500토큰, 겹침 50토큰.  
벡터 스토어: FAISS (로컬, Docker 볼륨 마운트).

---

## 7. 외부 의존성

| 항목 | 용도 |
|---|---|
| `langgraph` | 그래프 실행 엔진 |
| `langchain-anthropic` | Claude Sonnet (LLM 추론 + RAG 생성) |
| `langchain-openai` | 임베딩 전용 (`text-embedding-3-small`) |
| `faiss-cpu` | 벡터 스토어 |
| `streamlit` | 시민 UI + 담당자 대시보드 |
| `folium` | 제보 지도 |
| `smtplib` (stdlib) | 이메일 발송 |

---

## 8. 구현 범위 외 (이번 스펙 제외)

- 사용자 인증 (시민/담당자 로그인)
- 데이터베이스 (SQLite/PostgreSQL 전환) — 현재는 CSV
- CI/CD, 프로덕션 배포
