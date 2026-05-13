# Open-Meteo 날씨 데이터를 서울 구 단위로 수집해 원천 JSON으로 저장한다.

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


RAW_DATA_DIR = Path("data/raw")
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

SEOUL_DISTRICT_COORDS: dict[str, tuple[float, float]] = {
    "강남구": (37.5172, 127.0473),
    "강동구": (37.5301, 127.1238),
    "강북구": (37.6396, 127.0257),
    "강서구": (37.5509, 126.8495),
    "관악구": (37.4784, 126.9516),
    "광진구": (37.5385, 127.0823),
    "구로구": (37.4955, 126.8877),
    "금천구": (37.4569, 126.8955),
    "노원구": (37.6542, 127.0568),
    "도봉구": (37.6688, 127.0471),
    "동대문구": (37.5744, 127.0396),
    "동작구": (37.5124, 126.9393),
    "마포구": (37.5663, 126.9019),
    "서대문구": (37.5791, 126.9368),
    "서초구": (37.4836, 127.0327),
    "성동구": (37.5633, 127.0369),
    "성북구": (37.5894, 127.0167),
    "송파구": (37.5145, 127.1059),
    "양천구": (37.5169, 126.8664),
    "영등포구": (37.5264, 126.8962),
    "용산구": (37.5326, 126.9905),
    "은평구": (37.6027, 126.9291),
    "종로구": (37.5735, 126.9788),
    "중구": (37.5636, 126.9976),
    "중랑구": (37.6063, 127.0925),
}


def save_raw_json(data: Any, filename: str, raw_dir: Path = RAW_DATA_DIR) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_path = raw_dir / filename
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    return output_path


def fetch_weather_archive(
    district: str,
    start_date: str | date,
    end_date: str | date,
    *,
    raw_dir: Path = RAW_DATA_DIR,
) -> Path:
    if district not in SEOUL_DISTRICT_COORDS:
        known = ", ".join(SEOUL_DISTRICT_COORDS)
        raise ValueError(f"Unknown district: {district}. Expected one of: {known}")

    latitude, longitude = SEOUL_DISTRICT_COORDS[district]
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "daily": ",".join(
            [
                "temperature_2m_max",
                "temperature_2m_min",
                "temperature_2m_mean",
                "precipitation_sum",
            ]
        ),
        "timezone": "Asia/Seoul",
    }
    url = f"{OPEN_METEO_ARCHIVE_URL}?{urlencode(params)}"

    with urlopen(url, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    payload["district"] = district
    payload["source_url"] = url
    filename = f"open_meteo_{district}_{start_date}_{end_date}.json"
    return save_raw_json(payload, filename, raw_dir)


def fetch_weather_archive_for_all_districts(
    start_date: str | date,
    end_date: str | date,
    *,
    raw_dir: Path = RAW_DATA_DIR,
) -> list[Path]:
    paths: list[Path] = []
    for district in SEOUL_DISTRICT_COORDS:
        paths.append(fetch_weather_archive(district, start_date, end_date, raw_dir=raw_dir))
    return paths
