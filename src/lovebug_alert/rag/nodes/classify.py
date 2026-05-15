# 제보 사진에서 러브버그를 Vision LLM으로 분류하는 노드.

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from lovebug_alert.rag.state import AgentState

_MEDIA_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
_PROMPT = (
    "이 사진에 러브버그(붉은등우단털파리, Plecia longiforceps)가 있나요? "
    "'있음' 또는 '없음'으로 시작해 한 문장으로 설명하세요."
)


def classify_photo(state: AgentState) -> dict[str, Any]:
    """제보 사진을 OpenAI Vision으로 분석해 러브버그 여부를 판별한다."""
    photo_path = state.get("report", {}).get("photo_path", "")
    if not photo_path or not Path(photo_path).exists():
        return {"photo_verified": None, "verification_note": ""}

    try:
        import openai

        path = Path(photo_path)
        media_type = _MEDIA_TYPES.get(path.suffix.lower(), "image/jpeg")
        image_data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")

        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=128,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_data}"}},
                    {"type": "text", "text": _PROMPT},
                ],
            }],
        )
        note = response.choices[0].message.content.strip()
        return {"photo_verified": note.startswith("있음"), "verification_note": note}

    except Exception as e:
        return {"photo_verified": None, "verification_note": f"분류 실패: {e}"}
