# Context Notes

## 2026-05-13

- `CLAUDE.md`의 프로젝트 메모에 따라 첫 구현 범위를 Open-Meteo와 iNaturalist 원천 데이터 수집으로 제한한다.
- 서울 25개 구 좌표는 Open-Meteo 구별 날씨 호출의 기준점으로 사용한다.
- 원천 API 응답은 후처리 전에 재현 가능하도록 `data/raw/` 아래 JSON 파일로 저장한다.
- iNaturalist는 러브버그 분류군 식별이 데이터 상황에 따라 달라질 수 있어 기본 검색어를 `Plecia`로 두고 호출자가 바꿀 수 있게 한다.

