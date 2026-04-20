import hashlib
import os
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEDIA_DIR = BASE_DIR / "media"
TTS_DIR = MEDIA_DIR / "tts"
TTS_DIR.mkdir(parents=True, exist_ok=True)

SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "").strip()
SILICONFLOW_TTS_URL = os.getenv(
    "SILICONFLOW_TTS_URL",
    "https://api.siliconflow.cn/v1/audio/speech",
).strip()

# 默认值用官方示例里最稳妥的一组，后续你可以用环境变量覆盖
TTS_MODEL = os.getenv("TTS_MODEL", "fnlp/MOSS-TTSD-v0.5").strip()
TTS_VOICE = os.getenv("TTS_VOICE", "fnlp/MOSS-TTSD-v0.5:alex").strip()
TTS_SPEED = float(os.getenv("TTS_SPEED", "1.0"))
TTS_GAIN = float(os.getenv("TTS_GAIN", "0.0"))
TTS_TIMEOUT = int(os.getenv("TTS_TIMEOUT", "90"))


def _safe_text(text: str | None) -> str:
    return (text or "").strip()


def _make_cache_name(exhibit_code: str, text: str) -> str:
    raw = f"{exhibit_code}|{text}|{TTS_MODEL}|{TTS_VOICE}|{TTS_SPEED}|{TTS_GAIN}"
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return f"{digest}.mp3"


def get_or_create_tts_audio(exhibit_code: str, text: str | None) -> str | None:
    """
    返回相对 URL，例如 /media/tts/xxx.mp3
    没有可生成的音频时返回 None。
    """
    cleaned_text = _safe_text(text)
    cleaned_code = _safe_text(exhibit_code)

    if not cleaned_text or not cleaned_code:
        return None

    if not SILICONFLOW_API_KEY:
        return None

    filename = _make_cache_name(cleaned_code, cleaned_text)
    file_path = TTS_DIR / filename

    if file_path.exists() and file_path.stat().st_size > 0:
        return f"/media/tts/{filename}"

    payload = {
        "model": TTS_MODEL,
        "input": cleaned_text,
        "voice": TTS_VOICE,
        "response_format": "mp3",
        "speed": TTS_SPEED,
        "gain": TTS_GAIN,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        SILICONFLOW_TTS_URL,
        json=payload,
        headers=headers,
        timeout=TTS_TIMEOUT,
    )
    response.raise_for_status()

    # 官方接口直接返回音频二进制内容，不是 JSON 链接
    file_path.write_bytes(response.content)

    if not file_path.exists() or file_path.stat().st_size == 0:
        return None

    return f"/media/tts/{filename}"
