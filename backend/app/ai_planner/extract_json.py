import json
import re

def extract_json(raw: str) -> dict:
    # 去掉 ```json
    raw = raw.strip()

    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json", "", 1).strip()

    # 提取 JSON 部分
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON found in LLM response")

    json_str = match.group()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print("❌ JSON parse failed:", e)
        print("RAW JSON:", json_str)
        raise