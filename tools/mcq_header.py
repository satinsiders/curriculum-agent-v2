from typing import List, Any


HEADER_TOKENS = {
    "passage", "context", "paragraph",
    "question", "prompt",
    "a", "b", "c", "d",
    "choice a", "choice b", "choice c", "choice d",
    "answer", "correct", "key",
    "solution", "explanation",
}


def _normalize(cell: Any) -> str:
    return str(cell or "").strip().lower()


def has_header(rows: List[List[Any]]) -> bool:
    """Best-effort check if the first row looks like a header.

    Heuristic: consider row[0] or row[1] mostly alphabetic and short, or if
    any cell in the first row matches common MCQ header tokens.
    """
    if not rows:
        return False

    first = rows[0]
    if not isinstance(first, list):
        return False

    # Token match
    tokens = {_normalize(c) for c in first}
    if tokens & HEADER_TOKENS:
        return True

    # Short, likely header text in first two cells
    for idx in (0, 1):
        if idx < len(first):
            cell = _normalize(first[idx])
            if 1 <= len(cell) <= 24 and cell.replace(" ", "").isalpha():
                # avoid cases where the cell is an actual short question
                if cell in {"passage", "question", "prompt"}:
                    return True

    return False

