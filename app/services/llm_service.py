
import json
import logging
import os
import time
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

API_KEY = os.getenv("SILICONFLOW_API_KEY", "").strip()
BASE_URL = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1").strip().rstrip("/")
MODEL_NAME = os.getenv("SILICONFLOW_MODEL", "Pro/deepseek-ai/DeepSeek-V3.2").strip()

# 调小默认超时和重试，优先保证讲解接口快速失败并回退模板
TIMEOUT = float(os.getenv("SILICONFLOW_TIMEOUT", "12"))
USE_LLM = os.getenv("USE_LLM", "true").strip().lower() in {"1", "true", "yes", "on"}

MAX_RETRIES = int(os.getenv("SILICONFLOW_MAX_RETRIES", "0"))
RETRY_BACKOFF_SECONDS = float(os.getenv("SILICONFLOW_RETRY_BACKOFF_SECONDS", "0.6"))

DEFAULT_TEMPERATURE = 0.5
DEFAULT_MAX_TOKENS = 220

_session = requests.Session()


def is_llm_enabled() -> bool:
    return USE_LLM


def is_llm_configured() -> bool:
    return bool(USE_LLM and API_KEY and BASE_URL and MODEL_NAME)


def _clamp_temperature(value: float | int | None) -> float:
    try:
        temp = float(value if value is not None else DEFAULT_TEMPERATURE)
    except Exception:
        temp = DEFAULT_TEMPERATURE

    if temp < 0:
        return 0.0
    if temp > 2:
        return 2.0
    return temp


def _clamp_max_tokens(value: int | None) -> int:
    try:
        tokens = int(value if value is not None else DEFAULT_MAX_TOKENS)
    except Exception:
        tokens = DEFAULT_MAX_TOKENS

    if tokens < 1:
        return 1
    if tokens > 4096:
        return 4096
    return tokens


def _preview_text(text: str, limit: int = 180) -> str:
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _extract_message_content(data: dict[str, Any]) -> str:
    try:
        choice = data["choices"][0]
        message = choice["message"]
        content = message["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"模型返回格式异常：{data}") from exc

    if isinstance(content, str):
        result = content.strip()
        if not result:
            raise RuntimeError("模型返回内容为空。")
        return result

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                item_type = str(item.get("type", "")).strip().lower()
                if item_type in {"text", "output_text", ""}:
                    text_part = str(item.get("text", "")).strip()
                    if text_part:
                        parts.append(text_part)
            elif isinstance(item, str):
                text_part = item.strip()
                if text_part:
                    parts.append(text_part)

        result = "\n".join(parts).strip()
        if not result:
            raise RuntimeError("模型返回内容为空。")
        return result

    raise RuntimeError(f"模型返回 content 类型异常：{type(content)}")


def _build_payload(
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    return {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }


def _should_retry(status_code: int) -> bool:
    return status_code == 429 or 500 <= status_code < 600


def _request_llm(
    payload: dict[str, Any],
    timeout: float | tuple[float, float] | None = None,
    max_retries: int | None = None,
) -> requests.Response:
    url = f"{BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    final_timeout = timeout if timeout is not None else TIMEOUT
    final_max_retries = MAX_RETRIES if max_retries is None else max(0, int(max_retries))

    last_error: Exception | None = None

    for attempt in range(final_max_retries + 1):
        start_time = time.perf_counter()

        try:
            response = _session.post(
                url,
                headers=headers,
                json=payload,
                timeout=final_timeout,
            )
        except requests.RequestException as exc:
            elapsed = time.perf_counter() - start_time
            logger.warning(
                "LLM request transport error | model=%s | attempt=%s/%s | elapsed=%.2fs | error=%s",
                MODEL_NAME,
                attempt + 1,
                final_max_retries + 1,
                elapsed,
                exc,
            )
            last_error = exc

            if attempt < final_max_retries:
                sleep_seconds = RETRY_BACKOFF_SECONDS * (attempt + 1)
                time.sleep(sleep_seconds)
                continue

            raise RuntimeError(f"调用大模型接口失败：{exc}") from exc

        elapsed = time.perf_counter() - start_time
        logger.info(
            "LLM request finished | model=%s | status=%s | attempt=%s/%s | elapsed=%.2fs",
            MODEL_NAME,
            response.status_code,
            attempt + 1,
            final_max_retries + 1,
            elapsed,
        )

        if response.ok:
            return response

        detail = _preview_text(response.text, limit=500)
        logger.warning(
            "LLM request non-200 | model=%s | status=%s | attempt=%s/%s | body=%s",
            MODEL_NAME,
            response.status_code,
            attempt + 1,
            final_max_retries + 1,
            detail,
        )

        if attempt < final_max_retries and _should_retry(response.status_code):
            sleep_seconds = RETRY_BACKOFF_SECONDS * (attempt + 1)
            time.sleep(sleep_seconds)
            continue

        raise RuntimeError(
            f"大模型调用失败，status={response.status_code}，body={detail}"
        )

    if last_error is not None:
        raise RuntimeError(f"调用大模型接口失败：{last_error}") from last_error

    raise RuntimeError("大模型调用失败：未知错误。")


def chat_with_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.5,
    max_tokens: int = 220,
    timeout: float | tuple[float, float] | None = None,
    max_retries: int | None = None,
) -> str:
    if not is_llm_enabled():
        raise RuntimeError("USE_LLM=false，当前已关闭大模型调用。")

    if not is_llm_configured():
        raise RuntimeError("大模型配置不完整，请检查 .env 文件。")

    system_prompt = str(system_prompt or "").strip()
    user_prompt = str(user_prompt or "").strip()

    if not system_prompt:
        raise RuntimeError("system_prompt 不能为空。")
    if not user_prompt:
        raise RuntimeError("user_prompt 不能为空。")

    final_temperature = _clamp_temperature(temperature)
    final_max_tokens = _clamp_max_tokens(max_tokens)

    payload = _build_payload(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=final_temperature,
        max_tokens=final_max_tokens,
    )

    logger.debug(
        "LLM payload prepared | model=%s | system_len=%s | user_len=%s | temperature=%.2f | max_tokens=%s",
        MODEL_NAME,
        len(system_prompt),
        len(user_prompt),
        final_temperature,
        final_max_tokens,
    )

    response = _request_llm(
        payload=payload,
        timeout=timeout,
        max_retries=max_retries,
    )

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        body_preview = _preview_text(response.text, limit=500)
        raise RuntimeError(f"模型返回的不是合法 JSON：{body_preview}") from exc

    content = _extract_message_content(data)

    finish_reason = None
    usage = None
    try:
        finish_reason = data.get("choices", [{}])[0].get("finish_reason")
        usage = data.get("usage")
    except Exception:
        finish_reason = None
        usage = None

    logger.debug(
        "LLM response parsed | model=%s | finish_reason=%s | usage=%s | preview=%s",
        MODEL_NAME,
        finish_reason,
        usage,
        _preview_text(content, limit=200),
    )

    return content