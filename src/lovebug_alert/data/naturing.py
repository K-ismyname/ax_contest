# 네이처링에서 붉은등우단털파리 관찰 기록을 수집해 원천 JSON으로 저장한다.

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup


RAW_DATA_DIR = Path("data/raw")
BASE_URL = "https://www.naturing.net"
SEARCH_URL = f"{BASE_URL}/o/search"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _fetch_html(url: str, timeout: int = 30) -> str:
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def _parse_coord(text: str) -> tuple[float, float] | None:
    """위도/경도 좌표 패턴 파싱. '37.123, 127.456' 또는 개별 data 속성에서 추출."""
    match = re.search(r"(-?\d+\.\d+)[,\s]+(-?\d+\.\d+)", text)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None


def _parse_observation_list(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    records = []

    # 관찰 기록 카드: 다양한 선택자를 순서대로 시도
    items = (
        soup.select(".observation-item")
        or soup.select(".obs-item")
        or soup.select("li.item")
        or soup.select("article")
        or soup.select(".card")
    )

    for item in items:
        record: dict[str, Any] = {}

        # 날짜
        date_el = (
            item.select_one("[data-date]")
            or item.select_one(".date")
            or item.select_one("time")
        )
        if date_el:
            record["date"] = date_el.get("data-date") or date_el.get("datetime") or date_el.get_text(strip=True)

        # 위치명
        loc_el = (
            item.select_one("[data-location]")
            or item.select_one(".location")
            or item.select_one(".place")
            or item.select_one(".addr")
        )
        if loc_el:
            record["location_name"] = loc_el.get("data-location") or loc_el.get_text(strip=True)

        # 좌표 — data 속성에서 직접 추출 시도
        lat = item.get("data-lat") or item.get("data-latitude")
        lng = item.get("data-lng") or item.get("data-longitude")
        if lat and lng:
            record["latitude"] = float(lat)
            record["longitude"] = float(lng)
        else:
            # 좌표가 텍스트로 포함된 경우 파싱
            coord_el = item.select_one("[data-lat]") or item.select_one("[data-lng]")
            if coord_el:
                record["latitude"] = float(coord_el.get("data-lat", 0))
                record["longitude"] = float(coord_el.get("data-lng", 0))

        # 관찰 상세 페이지 URL
        link = item.select_one("a[href]")
        if link:
            href = link["href"]
            record["url"] = href if href.startswith("http") else f"{BASE_URL}{href}"

        if record:
            records.append(record)

    return records


def _parse_next_page(html: str, current_page: int) -> str | None:
    """다음 페이지 URL 또는 None 반환."""
    soup = BeautifulSoup(html, "html.parser")
    # rel="next" 링크
    next_link = soup.select_one('a[rel="next"]') or soup.select_one('.pagination .next a')
    if next_link and next_link.get("href"):
        href = next_link["href"]
        return href if href.startswith("http") else f"{BASE_URL}{href}"

    # page 파라미터 기반 페이지네이션
    next_page_link = soup.select_one(f'a[href*="page={current_page + 1}"]')
    if next_page_link:
        href = next_page_link["href"]
        return href if href.startswith("http") else f"{BASE_URL}{href}"

    return None


def fetch_naturing_observations(
    taxon_name: str = "붉은등우단털파리",
    *,
    max_pages: int = 10,
    delay_seconds: float = 2.0,
    raw_dir: Path = RAW_DATA_DIR,
) -> Path:
    params = urlencode({"q": taxon_name})
    first_url = f"{SEARCH_URL}?{params}"

    all_records: list[dict[str, Any]] = []
    visited_urls: list[str] = []
    current_url: str | None = first_url
    page = 1

    while current_url and page <= max_pages:
        print(f"  페이지 {page}: {current_url}")
        html = _fetch_html(current_url)
        visited_urls.append(current_url)

        records = _parse_observation_list(html)
        all_records.extend(records)
        print(f"    → {len(records)}건 파싱")

        if not records:
            # 결과 없음 또는 파싱 실패 — 원시 HTML 스니펫 저장 후 중단
            snippet_path = raw_dir / f"naturing_debug_page{page}.html"
            raw_dir.mkdir(parents=True, exist_ok=True)
            snippet_path.write_text(html[:5000], encoding="utf-8")
            print(f"    ↳ 파싱 결과 없음. 디버그 HTML 저장: {snippet_path}")
            break

        next_url = _parse_next_page(html, page)
        current_url = next_url
        page += 1

        if current_url:
            time.sleep(delay_seconds)

    output = {
        "taxon_name": taxon_name,
        "source": BASE_URL,
        "total_fetched": len(all_records),
        "pages_fetched": page - 1,
        "request_urls": visited_urls,
        "results": all_records,
    }
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_path = raw_dir / "naturing_lovebug.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"저장 완료: {out_path} ({len(all_records)}건)")
    return out_path
