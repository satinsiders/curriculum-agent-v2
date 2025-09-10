from dataclasses import dataclass, field
from typing import Any, Dict
import json


@dataclass(slots=True)
class LessonSpec:
    title: str
    meta: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: Any, idx: int) -> "LessonSpec":
        if isinstance(raw, cls):
            return raw
        if isinstance(raw, dict):
            return cls(title=raw.get("title", f"Lesson {idx:02d}"), meta=raw)
        if isinstance(raw, str):
            try:
                cand = json.loads(raw)
                if isinstance(cand, dict):
                    return cls(title=cand.get("title", f"Lesson {idx:02d}"), meta=cand)
            except json.JSONDecodeError:
                pass
            return cls(title=f"Lesson {idx:02d} – {raw.strip()}")
        raise TypeError(f"Unsupported lesson spec type: {type(raw)}")

