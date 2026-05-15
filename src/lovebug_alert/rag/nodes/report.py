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
        "location_type": report.get("location_type", ""),
        "scale": report.get("scale", ""),
        "photo_verified": state.get("photo_verified", None),
        "verification_note": state.get("verification_note", ""),
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
                    verified = str(row.get("photo_verified", "")).strip()
                    color = "red" if verified == "True" else "gray"
                    label = "✅ 확인됨" if verified == "True" else ("❌ 미확인" if verified == "False" else "사진 없음")
                    folium.CircleMarker(
                        [lat, lng],
                        radius=6,
                        color=color,
                        fill=True,
                        popup=f"{label} | {row['date']} {row['location']}",
                    ).add_to(m)
                except (ValueError, KeyError):
                    continue

    MAP_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(MAP_OUTPUT_PATH))
    return {"map_path": str(MAP_OUTPUT_PATH)}
