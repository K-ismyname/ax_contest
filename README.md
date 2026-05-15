# 러브버그 조기경보 시스템 🐛

> **붉은등우단털파리(Plecia longiforceps) 대발생을 기온 누적도일(DD)로 예측하고,  
> 시민 크라우드소싱 + Vision AI 검증으로 실시간 경보를 제공하는 AX 시스템**

---

## 핵심 지표

| 항목 | 값 |
|------|-----|
| DD vs 첫발생 DOY 피어슨 상관계수 | **r = 0.9965** (n=3) |
| 경보 임계값 (DD) | **419** (2023–2024 평균 첫발생 누적 DD) |
| 분석 기간 | 2022–2025년 서울 관찰 기록 |
| 2026년 예측 첫 발생일 | **2026-06-16** (4년 평균 기반) |
| 모니터링 지역 | 서울 25개 자치구 |

---

## AX 전환 스토리

```
기존 방식                          AI 전환 후
──────────────────                 ──────────────────────────────────
담당자가 뉴스/민원 보고 인지   →   매일 07:00 기온 DD 자동 수집·계산
경험적 판단으로 방제 결정      →   임계값 도달 시 자동 경보 + RAG 방제 권고
시민 민원 수동 접수·처리       →   제보 폼 → Vision AI 자동 검증 → 지도 반영
구 단위 대응 불가              →   서울 25개 구별 DD·경보 단계 실시간 표시
```

---

## 시스템 아키텍처

```
                    ┌─────────────────────────────┐
                    │      APScheduler (07:00)      │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │         daily_graph          │  LangGraph
                    │  collect_weather             │
                    │  → collect_observations      │
                    │  → compute_dd (25개 구별)    │
                    │  → aggregate_reports         │
                    │  → analyze_risk              │
                    │  → [주의·경보] generate_rag  │  Claude + FAISS RAG
                    │  → notify_official           │  streamlit_state.json
                    └─────────────────────────────┘

                    ┌─────────────────────────────┐
                    │       시민 제보 (실시간)      │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │        report_graph          │  LangGraph
                    │  classify_photo              │  Claude Vision API
                    │  → save_report (CSV)         │
                    │  → update_map (Folium)       │
                    │  → rag_citizen_response      │  Claude + FAISS RAG
                    │  → return_response           │
                    └─────────────────────────────┘

                    ┌─────────────────────────────┐
                    │      Streamlit 대시보드       │
                    │  담당자 뷰 │ 시민 뷰          │
                    │  구별 경보지도│제보 폼         │
                    └─────────────────────────────┘
```

---

## 경보 단계

| 단계 | 누적 DD | 색상 |
|------|---------|------|
| 정상 | < 251 | 🟢 |
| 관심 | 251 – 335 | 🔵 |
| 주의 | 335 – 419 | 🟡 |
| 경보 | ≥ 419 | 🔴 |

> **기저 온도 10°C** 기준 1월 1일부터 누적. 임계값 419는 2023–2024년 서울 첫 관찰 평균 누적 DD.

---

## 주요 기능

### 담당자 뷰
- 서울 25개 구별 누적 DD · 경보 단계 지도 (Folium)
- DD 경보 단계 진행 바 + 예상 첫 출현일 D-day
- 주의·경보 단계 시 RAG 기반 방제 권고 자동 생성
- Vision AI 검증 제보만 구별 순위에 집계

### 시민 뷰
- 현재 DD 진행 상황 + 예측 첫 출현일
- 러브버그 발견 제보 폼 (위치·사진·설명)
- **사진 자동 분류**: Claude Vision이 러브버그 여부 판별 후 ✅/❌ 배지 표시
- 접수 즉시 AI 대처법 안내 (RAG)

---

## 데이터 소스

| 데이터 | 출처 | 용도 |
|--------|------|------|
| 서울 25개 구 일별 기온 | [Open-Meteo Archive API](https://archive-api.open-meteo.com/) | 누적 DD 계산 |
| 러브버그 관찰 기록 | [GBIF](https://www.gbif.org/) · iNaturalist | 첫 발생일 추출 |
| 방제 대응 매뉴얼 | 서울시 공공자료 (PDF) | RAG 근거 문서 |

---

## 기술 스택

```
LangGraph       — daily_graph / report_graph 워크플로우 오케스트레이션
Claude API      — Vision 사진 분류 · RAG LLM (claude-sonnet-4-6)
FAISS           — 방제 매뉴얼 벡터 인덱스
OpenAI          — 임베딩 (text-embedding-3-small)
Streamlit       — 담당자·시민 이중 대시보드
Folium          — 서울 구별 경보 지도
APScheduler     — 매일 07:00 KST 자동 실행
Open-Meteo      — 무료 기상 아카이브 API
```

---

## 빠른 시작

### 1. 환경 설정

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. 환경변수 설정

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...   # Claude Vision + RAG LLM
OPENAI_API_KEY=sk-...          # FAISS 임베딩

# 이메일 알림 (선택)
SMTP_HOST=smtp.gmail.com
SMTP_USER=your@gmail.com
SMTP_PASS=app-password
NOTIFY_EMAIL=official@seoul.go.kr
```

### 3. 대시보드 실행

```bash
# 오늘 DD 계산 및 상태 파일 생성 (최초 1회)
python -c "
import sys; sys.path.insert(0, 'src')
from datetime import date
from lovebug_alert.rag.graph import build_daily_graph
g = build_daily_graph()
g.invoke({'date': date.today().isoformat(),
          'weather_today': {}, 'observations_today': [],
          'current_dd': 0.0,
          'reports_today': [], 'risk_level': '정상', 'rag_summary': '',
          'email_sent': False, 'report': {}, 'citizen_answer': '', 'map_path': '',
          'photo_verified': None, 'verification_note': ''})
"

# Streamlit 실행
streamlit run app.py
```

### 4. 자동 스케줄러 (매일 07:00 KST)

```bash
python scripts/run_daily.py
```

---

## 프로젝트 구조

```
src/lovebug_alert/
├── data/           # 데이터 수집 (Open-Meteo, GBIF, iNaturalist)
├── features/       # 누적 DD 계산 · 상관관계 분석
├── rag/
│   ├── nodes/      # LangGraph 노드
│   │   ├── classify.py   # Vision AI 사진 분류
│   │   ├── collect.py    # 날씨·관찰 수집
│   │   ├── compute.py    # 구별 DD 계산
│   │   ├── analyze.py    # 경보 단계 판정
│   │   ├── rag.py        # RAG 대응 요약 생성
│   │   ├── notify.py     # 상태 저장 · 이메일 발송
│   │   └── report.py     # 제보 저장 · 지도 갱신
│   ├── graph.py    # daily_graph · report_graph 조립
│   ├── retriever.py# FAISS 벡터 스토어
│   └── state.py    # AgentState 스키마
└── ui/
    ├── official.py # 담당자 뷰
    ├── citizen.py  # 시민 뷰
    └── state_loader.py
```

---

## 연도별 첫 발생 데이터

| 연도 | 첫 발생일 | DOY | 누적 DD |
|------|-----------|-----|---------|
| 2022 | 2022-06-29 | 180 | 646 |
| 2023 | 2023-06-16 | 167 | 475 |
| 2024 | 2024-06-04 | 156 | 363 |
| 2025 | 2025-06-14 | 165 | 461 |
| **2026** | **2026-06-16** | **167** | **486** (예측) |
