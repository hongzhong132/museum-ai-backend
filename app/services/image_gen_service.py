from __future__ import annotations

import logging
import os
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

API_KEY = os.getenv("SILICONFLOW_API_KEY", "").strip()
BASE_URL = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1").strip().rstrip("/")
IMAGE_MODEL = os.getenv("SILICONFLOW_IMAGE_MODEL", "Kwai-Kolors/Kolors").strip()
IMAGE_SIZE = os.getenv("SILICONFLOW_IMAGE_SIZE", "720x1280").strip()
IMAGE_TIMEOUT = float(os.getenv("SILICONFLOW_IMAGE_TIMEOUT", "120"))
IMAGE_STEPS = int(os.getenv("SILICONFLOW_IMAGE_STEPS", "28"))
IMAGE_GUIDANCE_SCALE = float(os.getenv("SILICONFLOW_IMAGE_GUIDANCE_SCALE", "7.0"))
IMAGE_CFG = float(os.getenv("SILICONFLOW_IMAGE_CFG", "4.0"))
IMAGE_NEGATIVE_PROMPT = os.getenv(
    "SILICONFLOW_IMAGE_NEGATIVE_PROMPT",
    (
        "人物, 人脸, 肖像, 古装人物, 武侠人物, 战士, 手持武器, 手, 身体, 半身像, 全身像, 群像, "
        "影视剧海报, 电影剧照, 战场, 历史场景插画, 网图感, 旅游宣传照, 二次元, 卡通, 漫画, Q版, 3D渲染, "
        "拼贴, 多主体, 杂乱背景, 夸张动作, 夸张表情, 文字, 字母, logo, 水印, 签名, 海报模板字样, "
        "边框, 低质量, 模糊, 畸形, 变形, 多余手指, 满月, 山水拼贴, 飞鸟装饰, 对称模板, 悬浮祥云, 俗艳国风素材"
    ),
).strip()

_session = requests.Session()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEDIA_DIR = BASE_DIR / "media"
CREATIVE_DIR = MEDIA_DIR / "creative"
CREATIVE_DIR.mkdir(parents=True, exist_ok=True)


def is_image_configured() -> bool:
    return bool(API_KEY and BASE_URL and IMAGE_MODEL)


def _safe_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _merge_negative_prompt(extra_negative_prompt: str | None = None) -> str:
    extra = _safe_text(extra_negative_prompt)
    if not extra:
        return IMAGE_NEGATIVE_PROMPT

    merged = []
    seen = set()
    for chunk in f"{IMAGE_NEGATIVE_PROMPT},{extra}".split(","):
        text = chunk.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        merged.append(text)
    return ", ".join(merged)


def _build_payload(prompt: str, negative_prompt: str) -> dict:
    payload = {
        "model": IMAGE_MODEL,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "num_inference_steps": max(1, IMAGE_STEPS),
        "seed": int(time.time() * 1000) % 10_000_000_000,
    }

    model_name = IMAGE_MODEL.lower()
    if "qwen/qwen-image" in model_name and "edit" not in model_name:
        payload["image_size"] = IMAGE_SIZE or "928x1664"
        payload["cfg"] = IMAGE_CFG
    elif "kolors" in model_name:
        payload["image_size"] = IMAGE_SIZE or "720x1280"
        payload["batch_size"] = 1
        payload["guidance_scale"] = IMAGE_GUIDANCE_SCALE
    else:
        payload["image_size"] = IMAGE_SIZE or "720x1280"

    return payload


def _guess_suffix(url: str, response: requests.Response | None = None) -> str:
    if response is not None:
        content_type = (response.headers.get("Content-Type") or "").lower()
        if "png" in content_type:
            return ".png"
        if "jpeg" in content_type or "jpg" in content_type:
            return ".jpg"
        if "webp" in content_type:
            return ".webp"

    path = urlparse(url).path.lower()
    for suffix in (".png", ".jpg", ".jpeg", ".webp"):
        if path.endswith(suffix):
            return ".jpg" if suffix == ".jpeg" else suffix
    return ".png"


def _download_image(url: str) -> str:
    response = _session.get(url, timeout=IMAGE_TIMEOUT)
    response.raise_for_status()
    suffix = _guess_suffix(url, response)
    file_name = f"creative_{int(time.time())}_{uuid.uuid4().hex[:8]}{suffix}"
    file_path = CREATIVE_DIR / file_name
    file_path.write_bytes(response.content)
    return f"/media/creative/{file_name}"


def _extract_image_url(data: dict) -> str:
    images = data.get("images") or data.get("data") or []
    if images and isinstance(images, list):
        first = images[0] or {}
        url = first.get("url") or first.get("b64_json")
        if url and not str(url).startswith("data:"):
            return str(url)

    raise RuntimeError("生图接口未返回可用图片 URL。")


def generate_image_relative_url(
    prompt: str,
    extra_negative_prompt: str | None = None,
) -> tuple[str, dict]:
    if not is_image_configured():
        raise RuntimeError("SiliconFlow 生图配置不完整，请检查 .env。")

    prompt = _safe_text(prompt)
    if not prompt:
        raise RuntimeError("生图提示词不能为空。")

    negative_prompt = _merge_negative_prompt(extra_negative_prompt)

    url = f"{BASE_URL}/images/generations"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = _build_payload(prompt, negative_prompt)

    logger.info("SiliconFlow image request start | model=%s", IMAGE_MODEL)
    response = _session.post(url, headers=headers, json=payload, timeout=IMAGE_TIMEOUT)
    if not response.ok:
        detail = response.text[:500]
        raise RuntimeError(f"生图接口调用失败，status={response.status_code}，body={detail}")

    data = response.json()
    image_url = _extract_image_url(data)
    relative_url = _download_image(image_url)

    meta = {
        "seed": data.get("seed") or payload.get("seed"),
        "timings": data.get("timings") or {},
        "model": IMAGE_MODEL,
    }
    logger.info(
        "SiliconFlow image request success | model=%s | relative_url=%s",
        IMAGE_MODEL,
        relative_url,
    )
    return relative_url, meta
