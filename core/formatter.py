# File: formatter.py
from typing import Any, Dict

from config import MAX_LOOPS
from .agents import formatter as formatter_agent, format_qa_agent
from tools.google_exporter import create_lesson_doc, create_mcq_sheet

from utils.retry_helpers import run_with_retry, looper
from utils.log_helpers import with_lesson_id
from utils.io_helpers import safe_json, load_rows

async def format_with_qa(
    kind: str,
    lesson_id: str,
    title: str,
    raw_content: Any
) -> str:
    """Run the Formatter → Format-QA loop until approval, then return the export URL."""
    logger = with_lesson_id(lesson_id)
    base_payload: Dict[str, Any] = {
        "type": kind,
        "lesson_id": lesson_id,
        "title": title,
        "content": raw_content,
    }

    # Define runner for formatting
    fmt_review: Dict[str, Any] = {}

    async def run_fmt(payload: Any):
        resp = await run_with_retry(formatter_agent, payload, lesson_id)
        return safe_json(resp.final_output)

    async def validate(fmt_out: Any) -> bool:
        nonlocal fmt_review
        if not (isinstance(fmt_out, dict) and fmt_out.get("formatted") is not None):
            return False
        fmt_review = safe_json(
            (await run_with_retry(format_qa_agent, {"payload": fmt_out}, lesson_id)).final_output
        )
        return fmt_review.get("status") == "approve"

    async def update_fmt_payload(payload: Any, draft: Any) -> Any:
        nonlocal fmt_review
        feedback = fmt_review.get("feedback", "") if fmt_review else ""
        fmt_review = {}
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
        return ""

    # Export
    try:
        if kind == "article":
            url = create_lesson_doc(formatted.get("formatted"), f"{lesson_id} – {title}")
        else:
            rows = load_rows(formatted.get("formatted"))
            url = create_mcq_sheet(rows, f"{lesson_id} MCQs – {title}")
        logger.info(f"✅ Exported {'DOC' if kind=='article' else 'SHEET'} → {url}")
        return url
    except Exception as e:
        logger.error(f"❌ Export failed for {lesson_id} ({kind}): {e}")
        return ""
