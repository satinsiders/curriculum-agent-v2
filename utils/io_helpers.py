# File: utils/io_helpers.py
import json
import random
from typing import Any, Dict, List, Sequence, Union
from agents import ItemHelpers

def safe_json(data: Any) -> Dict[str, Any]:
    if isinstance(data, dict):
        return data
    if isinstance(data, str):
        text = data.strip()
        if text.startswith("```"):
            text = text.strip("` \n")
            text = "\n".join(
                line for line in text.splitlines()
                if not line.lower().startswith("json")
            )
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"status": text.lower(), "feedback": ""}
    raise TypeError(f"Unexpected payload type: {type(data)}")

def load_rows(raw: Union[str, List[List[Any]]]) -> List[List[Any]]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Could not parse MCQ rows JSON: {exc}")
    raise TypeError(f"Unsupported MCQ formatted type: {type(raw)}")

def as_input_items(payload: Any) -> List[Dict[str, str]]:
    if (
        isinstance(payload, Sequence)
        and payload
        and isinstance(payload[0], dict)
        and "role" in payload[0]
    ):
        return list(payload)  # already in chat format
    if isinstance(payload, str):
        return ItemHelpers.input_to_new_input_list(payload)
    return ItemHelpers.input_to_new_input_list(json.dumps(payload, ensure_ascii=False))

def _jitter(delay: float) -> float:
    return max(0.1, delay * random.uniform(0.8, 1.2))
