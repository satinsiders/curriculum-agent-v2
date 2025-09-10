# File: curriculum.py
import asyncio
import json
import logging
from logging import getLogger
from typing import Any, Dict

from config import MAX_LOOPS, MAX_PARALLEL_LESSONS
from core.agents import brainstormer, reviewer
from core.processor import _process_lesson
from models.spec import LessonSpec

from utils.retry_helpers import run_with_retry, looper
from utils.log_helpers import with_lesson_id
from utils.io_helpers import safe_json

_base_logger = getLogger(__name__)

async def generate_curriculum(topic: str) -> Dict[str, Any]:
    """
    Generates a sequence of lessons for the given topic by running the brainstormer,
    reviewer, and processor agents with retries, and exporting the results.
    """
    _base_logger.info(f"🚀 Starting curriculum generation for topic: {topic!r}")

    # 1️⃣ Outline brainstorm + QA loop via looper
    async def run_brain(payload: Any):
        return (await run_with_retry(brainstormer, payload, "Outline")).final_output

    async def review_success(raw: str) -> bool:
        review = safe_json((await run_with_retry(reviewer, raw, "Outline")).final_output)
        _base_logger.info(
            f"✅ Reviewer status: {review.get('status')} • Feedback: {review.get('feedback')!r}"
        )
        return review.get("status") == "approve"

    async def update_outline(payload: Any, raw: str) -> Any:
        feedback = safe_json((await run_with_retry(reviewer, raw, "Outline")).final_output).get("feedback", "")
        return {"topic": topic, "previous": raw, "feedback": feedback}

    raw_outline = await looper(
        agent=brainstormer,
        lesson_id="Outline",
        kind="Outline",
        initial_payload=topic,
        runner_fn=run_brain,
        success_fn=review_success,
        update_payload_fn=update_outline,
    )
    if not raw_outline:
        _base_logger.error(f"❌ Outline for topic {topic!r} failed QA after {MAX_LOOPS} loops.")
        return {}

    # Parse and validate outline
    parsed = safe_json(raw_outline)
    if not isinstance(parsed, list):
        _base_logger.error(
            f"❌ Parsed brainstormer output is not a list: {type(parsed).__name__}"
        )
        return {}

    _base_logger.info(f"📚 Parsed {len(parsed)} lesson specs.")
    _base_logger.debug(
        f"📄 Parsed outline:\n{json.dumps(parsed, indent=2)[:1000]}..."
    )

    # Convert to LessonSpec objects
    specs = []
    for idx, item in enumerate(parsed, 1):
        try:
            spec = LessonSpec.from_raw(item, idx)
            specs.append(spec)
        except Exception as e:
            _base_logger.error(f"❌ Failed to create LessonSpec #{idx}: {e}")

    if not specs:
        _base_logger.error("❌ No valid lesson specs generated. Aborting.")
        return {}

    # Process lessons concurrently, up to the parallel limit
    sem = asyncio.Semaphore(MAX_PARALLEL_LESSONS)

    async def throttled(idx: int, spec: LessonSpec):
        lesson_id = f"Lesson {idx:02d}"
        logger = with_lesson_id(lesson_id)
        logger.info(f"⚙️ Processing {lesson_id}: {spec.title!r}")
        async with sem:
            try:
                result = await _process_lesson(idx, spec)
                if result:
                    logger.info(f"✅ {lesson_id} completed successfully.")
                else:
                    logger.warning(f"⚠️ {lesson_id} failed and returned None.")
                return result
            except Exception as e:
                logger.exception(f"❌ {lesson_id} crashed: {e}")
                return None

    tasks = [throttled(idx, spec) for idx, spec in enumerate(specs, 1)]
    finished = await asyncio.gather(*tasks)

    # Collect successful outputs
    output: Dict[str, Any] = {}
    for res in finished:
        if res:
            lid, doc_url, sheets = res
            output[lid] = {"doc": doc_url, "sheets": sheets}

    _base_logger.info(
        f"🏁 Curriculum generation complete. {len(output)} lessons succeeded."
    )
    return output
