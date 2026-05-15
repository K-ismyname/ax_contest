# 기온 누적도일(DD) 계산 및 붉은등우단털파리 첫 관찰일과의 상관관계 분석 모듈.

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

# 곤충 발육 하한온도 (도일 계산 기준)
BASE_TEMP = 10.0
RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


# ── 1. 누적 DD 계산 ───────────────────────────────────────────────────────────

def _daily_dd(t_mean: float | None) -> float:
    if t_mean is None:
        return 0.0
    return max(0.0, t_mean - BASE_TEMP)


def load_district_dd(district: str, years: list[int]) -> dict[int, dict[str, float]]:
    """구별 open_meteo JSON에서 연도별 일별 누적DD를 반환한다.

    반환: {year: {"YYYY-MM-DD": cumulative_dd, ...}}
    """
    result: dict[int, dict[str, float]] = {}
    for path in sorted(RAW_DIR.glob(f"open_meteo_{district}_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        daily = data["daily"]
        temp_by_date: dict[str, float | None] = {
            d: t for d, t in zip(daily["time"], daily["temperature_2m_mean"])
        }
        for year in years:
            cumulative = 0.0
            year_dd: dict[str, float] = {}
            for date_str, t_mean in temp_by_date.items():
                if not date_str.startswith(str(year)):
                    continue
                cumulative += _daily_dd(t_mean)
                year_dd[date_str] = round(cumulative, 2)
            if year_dd:
                result[year] = year_dd
    return result


def compute_seoul_mean_dd(years: list[int]) -> dict[int, dict[str, float]]:
    """서울 25개 구 평균 누적DD를 연도별로 반환한다."""
    seen: set[str] = set()
    districts: list[str] = []
    for f in sorted(RAW_DIR.glob("open_meteo_*.json")):
        parts = f.stem.split("_")
        if len(parts) >= 3:
            district = parts[2]
            if district not in seen:
                seen.add(district)
                districts.append(district)

    # 전체 구 DD 합산
    totals: dict[int, dict[str, float]] = {y: {} for y in years}
    counts: dict[int, dict[str, int]] = {y: {} for y in years}

    for district in districts:
        dd_by_year = load_district_dd(district, years)
        for year, dd_map in dd_by_year.items():
            for date_str, val in dd_map.items():
                totals[year][date_str] = totals[year].get(date_str, 0.0) + val
                counts[year][date_str] = counts[year].get(date_str, 0) + 1

    # 평균
    mean_dd: dict[int, dict[str, float]] = {}
    for year in years:
        mean_dd[year] = {
            d: round(totals[year][d] / counts[year][d], 2)
            for d in sorted(totals[year])
        }

    return mean_dd


# ── 2. GBIF 첫 관찰일 추출 ───────────────────────────────────────────────────

def extract_first_observation(
    years: list[int],
    *,
    seoul_only: bool = True,
) -> dict[int, dict[str, Any]]:
    """연도별 첫 관찰일과 DOY(1월1일=1)를 반환한다."""
    gbif = json.loads((RAW_DIR / "gbif_lovebug_korea.json").read_text(encoding="utf-8"))
    results = gbif["results"]

    first_obs: dict[int, dict[str, Any]] = {}
    for year in years:
        candidates = [
            r for r in results
            if r.get("year") == year
            and r.get("date")
            and (not seoul_only or r.get("locality") == "Seoul")
        ]
        # 서울 데이터가 없으면 전국으로 fallback
        if not candidates:
            candidates = [
                r for r in results
                if r.get("year") == year and r.get("date")
            ]

        if not candidates:
            continue

        earliest = min(candidates, key=lambda r: r["date"][:10])
        date_str = earliest["date"][:10]

        # DOY 계산 (1월 1일 = 1)
        from datetime import date as dt
        y, m, d = map(int, date_str.split("-"))
        doy = (dt(y, m, d) - dt(y, 1, 1)).days + 1

        first_obs[year] = {
            "date": date_str,
            "doy": doy,
            "latitude": earliest.get("latitude"),
            "longitude": earliest.get("longitude"),
            "locality": earliest.get("locality"),
            "source": earliest.get("source"),
            "seoul_only": seoul_only and earliest.get("locality") == "Seoul",
        }

    return first_obs


# ── 3. 상관관계 분석 ─────────────────────────────────────────────────────────

def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = sum((x - mean_x) ** 2 for x in xs) ** 0.5
    den_y = sum((y - mean_y) ** 2 for y in ys) ** 0.5
    if den_x == 0 or den_y == 0:
        return None
    return round(num / (den_x * den_y), 4)


# ── 4. 메인: 분석 실행 및 CSV 저장 ──────────────────────────────────────────

def run(years: list[int] | None = None) -> Path:
    if years is None:
        years = [2023, 2024, 2025]

    print("서울 25개 구 누적 DD 계산 중...")
    seoul_dd = compute_seoul_mean_dd(years)

    print("GBIF 첫 관찰일 추출 중...")
    first_obs = extract_first_observation(years)

    rows: list[dict[str, Any]] = []
    for year in years:
        if year not in first_obs:
            print(f"  {year}: 관찰 기록 없음 — 건너뜀")
            continue

        obs = first_obs[year]
        obs_date = obs["date"]
        dd_map = seoul_dd.get(year, {})

        # 첫 관찰일 당일 누적 DD
        dd_at_obs = dd_map.get(obs_date)

        # 전날까지 누적 DD (관찰 전 누적 기준)
        sorted_dates = sorted(dd_map.keys())
        prior_dates = [d for d in sorted_dates if d < obs_date]
        dd_day_before = dd_map[prior_dates[-1]] if prior_dates else 0.0

        rows.append({
            "year": year,
            "first_obs_date": obs_date,
            "doy": obs["doy"],
            "locality": obs["locality"],
            "source": obs["source"],
            "latitude": obs["latitude"],
            "longitude": obs["longitude"],
            "dd_at_first_obs": dd_at_obs,
            "dd_day_before_obs": dd_day_before,
            "base_temp_c": BASE_TEMP,
        })
        print(f"  {year}: 첫 관찰 {obs_date} (DOY={obs['doy']}), 누적DD={dd_at_obs}")

    # 상관관계
    valid = [r for r in rows if r["dd_at_first_obs"] is not None]
    doys = [r["doy"] for r in valid]
    dds = [r["dd_at_first_obs"] for r in valid]
    r_val = _pearson(doys, dds)
    print(f"\nDOY vs 누적DD 피어슨 상관계수 (n={len(valid)}): {r_val}")

    # CSV 저장
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / "dd_analysis.csv"
    if rows:
        fieldnames = list(rows[0].keys())
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    # 요약 행 추가 (메타)
    summary_path = PROCESSED_DIR / "dd_analysis_summary.json"
    summary_path.write_text(
        json.dumps({
            "years_analyzed": years,
            "n_years_with_data": len(valid),
            "base_temp_c": BASE_TEMP,
            "pearson_r_doy_vs_dd": r_val,
            "rows": rows,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n저장 완료: {out_path}")
    return out_path


if __name__ == "__main__":
    run()
