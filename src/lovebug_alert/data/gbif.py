# GBIF API로 한국 붉은등우단털파리(Plecia longiforceps) 관찰 기록을 수집해 원천 JSON으로 저장한다.

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


RAW_DATA_DIR = Path("data/raw")
GBIF_OCCURRENCE_URL = "https://api.gbif.org/v1/occurrence/search"


def fetch_gbif_lovebug_korea(
    scientific_name: str = "Plecia longiforceps",
    country: str = "KR",
    limit: int = 300,
    *,
    raw_dir: Path = RAW_DATA_DIR,
) -> Path:
    records: list[dict[str, Any]] = []
    offset = 0
    end_of_records = False
    request_urls: list[str] = []

    while not end_of_records:
        params = urlencode({
            "scientificName": scientific_name,
            "country": country,
            "limit": limit,
            "offset": offset,
        })
        url = f"{GBIF_OCCURRENCE_URL}?{params}"
        request_urls.append(url)

        req = Request(url, headers={"User-Agent": "lovebug-alert-prototype"})
        with urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        results = payload.get("results", [])
        end_of_records = payload.get("endOfRecords", True)

        for r in results:
            records.append({
                "date": r.get("eventDate") or r.get("dateIdentified"),
                "year": r.get("year"),
                "month": r.get("month"),
                "day": r.get("day"),
                "latitude": r.get("decimalLatitude"),
                "longitude": r.get("decimalLongitude"),
                "source": r.get("datasetName") or r.get("institutionCode"),
                "gbif_key": r.get("key"),
                "occurrence_id": r.get("occurrenceID"),
                "locality": r.get("locality") or r.get("county") or r.get("stateProvince"),
                "basis_of_record": r.get("basisOfRecord"),
            })

        print(f"offset={offset} → {len(results)}건 수집 (누적 {len(records)}건, endOfRecords={end_of_records})")

        if end_of_records:
            break

        offset += limit
        time.sleep(1)

    output = {
        "scientific_name": scientific_name,
        "country": country,
        "total_fetched": len(records),
        "request_urls": request_urls,
        "results": records,
    }

    raw_dir.mkdir(parents=True, exist_ok=True)
    out_path = raw_dir / "gbif_lovebug_korea.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
