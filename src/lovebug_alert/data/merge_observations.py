# iNaturalist와 GBIF 관찰 기록을 통합하고 중복을 제거해 저장한다.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


def _parse_inat_record(r: dict[str, Any]) -> dict[str, Any]:
    """iNaturalist 레코드를 공통 스키마로 변환한다."""
    lat, lng = None, None
    loc = r.get("location")
    if loc:
        parts = str(loc).split(",")
        if len(parts) == 2:
            lat, lng = float(parts[0]), float(parts[1])

    geojson = r.get("geojson") or {}
    if not lat and geojson.get("coordinates"):
        lng, lat = geojson["coordinates"]

    taxon = r.get("taxon") or {}

    return {
        "id": f"inat_{r['id']}",
        "inat_id": str(r["id"]),
        "gbif_key": None,
        "date": r.get("observed_on"),
        "year": r.get("observed_on_details", {}).get("year"),
        "month": r.get("observed_on_details", {}).get("month"),
        "day": r.get("observed_on_details", {}).get("day"),
        "latitude": lat,
        "longitude": lng,
        "place_guess": r.get("place_guess"),
        "locality": None,
        "taxon_name": taxon.get("name"),
        "quality_grade": r.get("quality_grade"),
        "source": "iNaturalist",
        "url": r.get("uri"),
    }


def _parse_gbif_record(r: dict[str, Any]) -> dict[str, Any]:
    """GBIF 레코드를 공통 스키마로 변환한다."""
    oid = r.get("occurrence_id") or ""
    inat_id = str(oid).split("/")[-1] if "inaturalist" in str(oid) else None

    return {
        "id": f"gbif_{r['gbif_key']}",
        "inat_id": inat_id,
        "gbif_key": r.get("gbif_key"),
        "date": r.get("date", "")[:10] if r.get("date") else None,
        "year": r.get("year"),
        "month": r.get("month"),
        "day": r.get("day"),
        "latitude": r.get("latitude"),
        "longitude": r.get("longitude"),
        "place_guess": None,
        "locality": r.get("locality"),
        "taxon_name": "Plecia longiforceps",
        "quality_grade": "research" if r.get("basis_of_record") == "HUMAN_OBSERVATION" else None,
        "source": r.get("source"),
        "url": r.get("occurrence_id") if "http" in str(r.get("occurrence_id", "")) else None,
    }


def merge_and_deduplicate() -> Path:
    inat_raw = json.loads((RAW_DIR / "inaturalist_Plecia_2022-01-01_2025-12-31.json").read_text())
    gbif_raw = json.loads((RAW_DIR / "gbif_lovebug_korea.json").read_text())

    inat_records = [_parse_inat_record(r) for r in inat_raw["results"]]
    gbif_records = [_parse_gbif_record(r) for r in gbif_raw["results"]]

    # iNaturalist ID 기준 중복 제거
    # iNaturalist 레코드를 우선으로 두고, GBIF에서 같은 inat_id가 있으면 건너뜀
    seen_inat_ids: set[str] = {r["inat_id"] for r in inat_records if r["inat_id"]}

    merged: list[dict[str, Any]] = list(inat_records)
    dedup_count = 0

    for r in gbif_records:
        if r["inat_id"] and r["inat_id"] in seen_inat_ids:
            dedup_count += 1
            continue
        merged.append(r)
        if r["inat_id"]:
            seen_inat_ids.add(r["inat_id"])

    # 날짜순 정렬
    merged.sort(key=lambda r: (r["date"] or "9999", r["source"] or ""))

    output = {
        "description": "iNaturalist + GBIF 통합 관찰 기록 (중복 제거)",
        "total": len(merged),
        "from_inat": len(inat_records),
        "from_gbif": len(gbif_records),
        "deduplicated": dedup_count,
        "results": merged,
    }

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / "observations_merged.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
