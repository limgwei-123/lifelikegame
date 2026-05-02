import json
import re

def extract_json(raw: str) -> dict:
    raw = raw.strip()

    # 去掉 ```json
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json", "", 1).strip()

    # 抓 JSON
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON found in LLM response")

    json_str = match.group()

    json_str = fix_common_json_issues(json_str)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print("❌ JSON parse failed:", e)
        print("RAW JSON:", json_str)
        raise

def fix_common_json_issues(json_str: str) -> str:
    # 1️⃣ 修复 "days": 没有值
    json_str = re.sub(r'"days"\s*:\s*(?=[}\]])', '"days": []', json_str)

    # 2️⃣ 修复多余逗号（最后一个字段有逗号）
    json_str = re.sub(r",\s*([}\]])", r"\1", json_str)

    return json_str