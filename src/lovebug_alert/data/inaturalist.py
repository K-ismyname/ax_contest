# iNaturalist 시민 관측 데이터를 서울 범위에서 수집해 원천 JSON으로 저장한다.

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


RAW_DATA_DIR = Path("data/raw")
INATURALIST_OBSERVATIONS_URL = "https://api.inaturalist.org/v1/observations"
SEOUL_BOUNDING_BOX = {
    "nelat": 37.7018,
    "nelng": 127.1836,
    "swlat": 37.4283,
    "swlng": 126.7645,
}


def save_raw_json(data: Any, filename: str, raw_dir: Path = RAW_DATA_DIR) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_path = raw_dir / filename
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    return output_path


def _safe_filename_part(value: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in value)


def fetch_lovebug_observations(
    start_date: str | date,
    end_date: str | date,
    *,
    taxon_name: str = "Plecia",
    per_page: int = 200,
    max_pages: int = 5,
    raw_dir: Path = RAW_DATA_DIR,
) -> Path:
    observations: list[dict[str, Any]] = []
    total_results = 0
    request_urls: list[str] = []

    for page in range(1, max_pages + 1):
        params = {
            "q": taxon_name,
            "d1": str(start_date),
            "d2": str(end_date),
            "per_page": per_page,
            "page": page,
            "order": "desc",
            "order_by": "observed_on",
            **SEOUL_BOUNDING_BOX,
        }
        url = f"{INATURALIST_OBSERVATIONS_URL}?{urlencode(params)}"
        request_urls.append(url)

        request = Request(url, headers={"User-Agent": "lovebug-alert-prototype"})
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))

        page_results = payload.get("results", [])
        total_results = payload.get("total_results", total_results)
        observations.extend(page_results)

        if len(page_results) < per_page:
            break

    output = {
        "taxon_name": taxon_name,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "bounding_box": SEOUL_BOUNDING_BOX,
        "total_results": total_results,
        "saved_results": len(observations),
        "request_urls": request_urls,
        "results": observations,
    }
    safe_taxon_name = _safe_filename_part(taxon_name)
    filename = f"inaturalist_{safe_taxon_name}_{start_date}_{end_date}.json"
    return save_raw_json(output, filename, raw_dir)
