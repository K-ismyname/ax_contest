# Open-Meteo forecast API로 서울 오늘 날씨를 가져와 한국어 경보 메시지를 출력한다.

from __future__ import annotations

import json
from datetime import date
from urllib.parse import urlencode
from urllib.request import urlopen


OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

SEOUL_LAT = 37.5665
SEOUL_LON = 126.9780
EXTREME_HEAT_THRESHOLD = 35.0  # °C

RAIN_WEATHER_CODES = {51, 53, 55, 61, 63, 65, 80, 81, 82, 85, 86, 95, 96, 99}


def fetch_today_weather() -> dict:
    params = {
        "latitude": SEOUL_LAT,
        "longitude": SEOUL_LON,
        "daily": ",".join(
            [
                "weather_code",
                "temperature_2m_max",
                "precipitation_sum",
            ]
        ),
        "forecast_days": 1,
        "timezone": "Asia/Seoul",
    }
    url = f"{OPEN_METEO_FORECAST_URL}?{urlencode(params)}"

    with urlopen(url, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    daily = payload.get("daily", {})
    return {
        "weather_code": daily.get("weather_code", [0])[0],
        "temperature_2m_max": daily.get("temperature_2m_max", [0.0])[0],
        "precipitation_sum": daily.get("precipitation_sum", [0.0])[0],
    }


def classify_weather(weather_code: int, temp_max: float) -> str:
    if temp_max >= EXTREME_HEAT_THRESHOLD:
        return "외출 자제하세요"
    if weather_code in RAIN_WEATHER_CODES:
        return "우산 챙기세요"
    return "오늘 산책하기 좋아요"


def main() -> None:
    today = date.today().isoformat()
    print(f"[weather_alert] {today} 실행 시작")

    weather = fetch_today_weather()
    message = classify_weather(weather["weather_code"], weather["temperature_2m_max"])

    print(
        f"[weather_alert] 완료 — 날씨코드: {weather['weather_code']}, "
        f"최고기온: {weather['temperature_2m_max']}°C, 메시지: {message}"
    )


if __name__ == "__main__":
    main()
