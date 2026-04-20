import csv
import json
import re
import time
from pathlib import Path

from app.services.llm_service import chat_with_llm

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def build_prompts(name: str, era: str, category: str, hall_code: str, raw_notes: str):
    system_prompt = (
        "你是博物馆数据整理助手。"
        "你的任务是根据给定事实，生成适合导览系统使用的展品简介。"
        "只能依据提供的信息写，不要编造未给出的具体史实。"
    )

    user_prompt = f"""
请根据下面资料生成 JSON。

要求：
1. 只输出 JSON，不要输出其他内容。
2. JSON 格式固定为：
{{
  "short_intro": "一句简短介绍，40-70字",
  "deep_intro": "一段较完整介绍，90-160字"
}}
3. 使用简体中文。
4. 不要编造出土地点、具体年代细节、尺寸、作者等未提供信息。
5. 语言自然，适合博物馆导览系统。

资料：
展品名称：{name}
所属展区代码：{hall_code}
年代：{era}
类别：{category}
补充说明：{raw_notes}
""".strip()

    return system_prompt, user_prompt


def parse_json_text(text: str) -> dict:
    cleaned = text.strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(0)
    return json.loads(cleaned)


def clean_text(value: str) -> str:
    value = value or ""
    value = value.replace("\r", " ").replace("\n", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def generate_intro_with_retry(system_prompt: str, user_prompt: str, retry_times: int = 2) -> dict:
    last_error = None

    for attempt in range(retry_times + 1):
        try:
            result_text = chat_with_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.4,
                max_tokens=220
            )
            result = parse_json_text(result_text)

            short_intro = clean_text(result.get("short_intro", ""))
            deep_intro = clean_text(result.get("deep_intro", ""))

            if not short_intro or not deep_intro:
                raise ValueError("生成结果缺少 short_intro 或 deep_intro")

            return {
                "short_intro": short_intro,
                "deep_intro": deep_intro
            }
        except Exception as exc:
            last_error = exc
            if attempt < retry_times:
                time.sleep(2)

    raise last_error


def main():
    input_path = DATA_DIR / "exhibits_minimal.csv"
    output_path = DATA_DIR / "exhibits.csv"

    rows = []
    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            system_prompt, user_prompt = build_prompts(
                name=row["name"],
                era=row.get("era", ""),
                category=row.get("category", ""),
                hall_code=row.get("hall_code", ""),
                raw_notes=row.get("raw_notes", "")
            )

            try:
                result = generate_intro_with_retry(system_prompt, user_prompt, retry_times=2)
                row["short_intro"] = result["short_intro"]
                row["deep_intro"] = result["deep_intro"]
                print(f"已生成：{row['name']}")
            except Exception as exc:
                raw_notes = clean_text(row.get("raw_notes", ""))
                row["short_intro"] = raw_notes or f"{row['name']}是馆内的重要展品。"
                row["deep_intro"] = raw_notes or f"{row['name']}是馆内的重要展品，后续可继续补充更完整的导览简介。"
                print(f"生成失败，已使用兜底文本：{row['name']} | {exc}")

            rows.append(row)

    fieldnames = [
        "hall_code", "name", "code", "era", "category",
        "short_intro", "deep_intro",
        "is_featured", "recommended_priority", "image_url", "raw_notes"
    ]

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "hall_code": row.get("hall_code", ""),
                "name": row.get("name", ""),
                "code": row.get("code", ""),
                "era": row.get("era", ""),
                "category": row.get("category", ""),
                "short_intro": clean_text(row.get("short_intro", "")),
                "deep_intro": clean_text(row.get("deep_intro", "")),
                "is_featured": row.get("is_featured", "0"),
                "recommended_priority": row.get("recommended_priority", "0"),
                "image_url": row.get("image_url", ""),
                "raw_notes": clean_text(row.get("raw_notes", "")),
            })

    print(f"已输出：{output_path}")


if __name__ == "__main__":
    main()