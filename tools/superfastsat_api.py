import os
import time
import logging
import requests
from typing import List, Any, Optional
from tools.mcq_header import has_header

BASE_URL = os.getenv("SFS_BASE_URL", "https://prod-admin-api.superfastsat.com")
ADMIN_EMAIL = os.getenv("SFS_ADMIN_EMAIL")
ADMIN_PASS = os.getenv("SFS_ADMIN_PASS")
DOMAIN_ID = int(os.getenv("SFS_DOMAIN_ID", "1"))
SKILL_ID = int(os.getenv("SFS_SKILL_ID", "11"))

logger = logging.getLogger(__name__)

_token_cache = {"token": None, "expiry": 0.0}


def _login() -> str:
    if not ADMIN_EMAIL or not ADMIN_PASS:
        raise RuntimeError("SuperfastSAT credentials not configured")
    if _token_cache["token"] and time.time() < _token_cache["expiry"]:
        return _token_cache["token"]

    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
        headers={"Accept": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data.get("token") or data.get("accessToken")
    if not token:
        raise RuntimeError("No token returned from login")

    _token_cache["token"] = token
    _token_cache["expiry"] = time.time() + 3500
    return token


def _authed_fetch(path: str, method: str, payload: Any, token: str) -> Any:
    url = f"{BASE_URL}{path}"
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    resp = requests.request(method, url, json=payload, headers=headers, timeout=60)
    if resp.status_code == 401:
        token = _login()
        headers["Authorization"] = f"Bearer {token}"
        resp = requests.request(method, url, json=payload, headers=headers, timeout=60)
    if resp.status_code >= 300:
        raise RuntimeError(f"Request failed ({resp.status_code}) -> {resp.text}")
    if resp.content:
        return resp.json()
    return {}


def _create_lesson(title: str, token: str) -> int:
    payload = {"lessonType": "ENGLISH", "title": title, "lessonGoal": " "}
    data = _authed_fetch("/lessons", "post", payload, token)
    return data.get("id")


def _create_unit(lesson_id: int, row: List[Any], idx: int, token: str) -> None:
    letters = ["A", "B", "C", "D"]
    correct = str(row[6] or "").strip().upper()
    choices = [
        {"title": row[2 + i] or "", "isCorrect": letters[i] == correct}
        for i in range(4)
    ]
    raw = str(row[0] or "")
    with_breaks = raw.replace("\r\n", "<br/>").replace("\n", "<br/>")
    payload = {
        "unitType": "CHOICE_PROBLEM",
        "difficultyType": "MEDIUM",
        "duration": 1,
        "title": f"\ubb38\uc81c{idx}",
        "questionText": with_breaks,
        "question": row[1] or "",
        "solution": row[7] or "",
        "choices": choices,
        "domainId": DOMAIN_ID,
        "skillId": SKILL_ID,
    }
    _authed_fetch(f"/lessons/{lesson_id}/units", "post", payload, token)


def upload_rows(rows: List[List[Any]], title: str) -> Optional[int]:
    """Upload MCQ rows to SuperfastSAT. Returns lesson ID or None."""
    if not ADMIN_EMAIL or not ADMIN_PASS:
        logger.info("SuperfastSAT credentials not configured; skipping upload")
        return None
    if not rows:
        logger.warning("No rows provided for SuperfastSAT upload")
        return None

    start_idx = 1 if has_header(rows) else 0
    if len(rows) - start_idx < 1:
        logger.warning("No question rows found in sheet")
        return None

    token = _login()
    lesson_id = _create_lesson(title, token)
    idx = 1
    for i, row in enumerate(rows[start_idx:], start=start_idx + 1):
        try:
            _create_unit(lesson_id, row, idx, token)
            idx += 1
            time.sleep(0.5)
        except Exception as exc:
            logger.warning("Row %s failed: %s", i, exc)
            continue

    logger.info("Uploaded %s units to SuperfastSAT lesson %s", idx - 1, lesson_id)
    return lesson_id

