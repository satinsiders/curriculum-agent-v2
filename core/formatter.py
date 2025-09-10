# File: formatter.py
import logging
import asyncio
from typing import Any, Dict, List, Tuple, Union

from config import RETRY_BACKOFF, MAX_RETRY_DELAY, MAX_LOOPS
from .agents import formatter as formatter_agent, format_qa_agent
from tools.google_exporter import create_lesson_doc, create_mcq_sheet
from .agents import Runner, Agent

from utils.retry_helpers import run_with_retry, looper
from utils.log_helpers import with_lesson_id
from utils.io_helpers import safe_json, load_rows, as_input_items, _jitter

async def format_with_qa(
    kind: str,
    lesson_id: str,
    title: str,
    raw_content: Any
) -> Tuple[str, Union[str, List[List[Any]]]]:
    """
    Runs the Formatter → Format-QA loop using looper until approval, then exports.
    """
    logger = with_lesson_id(lesson_id)
    base_payload: Dict[str, Any] = {
        "type": kind,
        "lesson_id": lesson_id,
        "title": title,
        "content": raw_content,
    }

    # Define runner for formatting
    async def run_fmt(payload: Any):
        resp = await run_with_retry(formatter_agent, payload, lesson_id)
        return safe_json(resp.final_output)

    # Success if fqa approves
    def validate(fmt_out: Any) -> bool:
        return isinstance(fmt_out, dict) and fmt_out.get("formatted") is not None

    # Async update payload function for Format-QA loop
    async def update_fmt_payload(payload: Any, draft: Any) -> Any:
        qa_resp = await run_with_retry(format_qa_agent, {"payload": draft}, lesson_id)
        feedback = safe_json(qa_resp.final_output).get("feedback", "")
        return {**payload, "draft": draft, "revision": feedback}

    formatted = await looper(
        agent=formatter_agent,
        lesson_id=lesson_id,
        kind=f"Format-{kind}",
        initial_payload=base_payload,
        runner_fn=run_fmt,
        success_fn=validate,
        update_payload_fn=update_fmt_payload,
    )
    if not formatted:
        logger.error(f"⚠️ {lesson_id} {kind.upper()} failed Format-QA after {MAX_LOOPS} attempts")
        return kind, ""

    # Export
    try:
        if kind == "article":
            url = create_lesson_doc(formatted.get("formatted"), f"{lesson_id} – {title}")
        else:
            rows = load_rows(formatted.get("formatted"))
            url = create_mcq_sheet(rows, f"{lesson_id} MCQs – {title}")
        logger.info(f"✅ Exported {'DOC' if kind=='article' else 'SHEET'} → {url}")
        return kind, url
    except Exception as e:
        logger.error(f"❌ Export failed for {lesson_id} ({kind}): {e}")
        return kind, ""
