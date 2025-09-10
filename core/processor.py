# File: processor.py
import logging, asyncio
from typing import Any, Dict, Optional, Tuple

from config import MAX_LOOPS
from models.spec import LessonSpec
from core.agents import lesson_writer, problem_generator, qa_agent, Agent
from core.formatter import format_with_qa
from utils.retry_helpers import run_with_retry, looper
from utils.log_helpers import with_lesson_id
from utils.io_helpers import safe_json, _jitter

async def _process_lesson(
    idx: int, spec: LessonSpec
) -> Optional[Tuple[str, str, Dict[str, Any]]]:
    """Generate a full lesson (article + MCQs), pass it through QA, format, and export."""
    lesson_id = f"Lesson {idx:02d}"
    logger = with_lesson_id(lesson_id)

    # 1️⃣ Generate article with QA via looper
    async def run_article(payload: Any):
        return (await run_with_retry(lesson_writer, payload, lesson_id)).final_output

    art = await looper(
        agent=lesson_writer,
        lesson_id=lesson_id,
        kind="Article",
        initial_payload={"lesson_spec": spec.meta or spec.title},
        runner_fn=run_article,
        success_fn=lambda _: True,
        update_payload_fn=lambda p, r: p
    )
    if not art:
        return None

    # 2️⃣ Generate MCQs for each difficulty
    difficulties = ["easy", "medium", "hard"]
    qs_sets: Dict[str, Any] = {}
    for diff in difficulties:
        async def run_mcq(payload: Any):
            return (await run_with_retry(problem_generator, payload, lesson_id)).final_output

        async def mcq_success(res: Any) -> bool:
            qa_data = safe_json((await run_with_retry(qa_agent, {"payload": res}, lesson_id)).final_output)
            return qa_data.get("status") == "approve"

        async def update_mcq(payload: Any, res: Any) -> Any:
            qa_data = safe_json((await run_with_retry(qa_agent, {"payload": res}, lesson_id)).final_output)
            return {**payload, "draft": res, "revision": qa_data.get("feedback", "")}

        payload = {"lesson_spec": spec.meta or spec.title, "difficulty": diff, "num_questions": 5}
        draft = await looper(
            agent=problem_generator,
            lesson_id=lesson_id,
            kind=f"MCQs-{diff}",
            initial_payload=payload,
            runner_fn=run_mcq,
            success_fn=mcq_success,
            update_payload_fn=update_mcq,
        )
        if not draft:
            return None
        qs_sets[diff] = draft

    # 3️⃣ Format & export the article
    _, doc_url = await format_with_qa("article", lesson_id, spec.title, art)
    if not doc_url:
        logger.error(f"❌ {lesson_id} article export failed")
        return None

    # 4️⃣ Format & export MCQs
    _, sheets = await format_with_qa("mcq", lesson_id, spec.title, qs_sets)
    if not sheets:
        logger.error(f"❌ {lesson_id} mcq export failed")
        return None

    return lesson_id, doc_url, sheets
