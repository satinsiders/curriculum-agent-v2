# File: processor.py
from typing import Any, Dict, Optional, Tuple

from models.spec import LessonSpec
from core.agents import lesson_writer, problem_generator, qa_agent
from core.formatter import format_with_qa
from utils.retry_helpers import run_with_retry, looper
from utils.log_helpers import with_lesson_id
from utils.io_helpers import safe_json

async def process_lesson(
    idx: int, spec: LessonSpec
) -> Optional[Tuple[str, str, Dict[str, Any]]]:
    """Generate a full lesson (article + MCQs), pass it through QA, format, and export."""
    lesson_id = f"Lesson {idx:02d}"
    logger = with_lesson_id(lesson_id)

    # 1️⃣ Generate article with QA via looper
    article_review: Dict[str, Any] = {}

    async def run_article(payload: Any):
        return (await run_with_retry(lesson_writer, payload, lesson_id)).final_output

    async def article_success(draft: Any) -> bool:
        nonlocal article_review
        article_review = safe_json((await run_with_retry(qa_agent, {"payload": draft}, lesson_id)).final_output)
        return article_review.get("status") == "approve"

    async def update_article(payload: Any, draft: Any) -> Any:
        nonlocal article_review
        feedback = article_review.get("feedback", "") if article_review else ""
        article_review = {}
        return {**payload, "draft": draft, "revision": feedback}

    art = await looper(
        agent=lesson_writer,
        lesson_id=lesson_id,
        kind="Article",
        initial_payload={"lesson_spec": spec.meta or spec.title},
        runner_fn=run_article,
        success_fn=article_success,
        update_payload_fn=update_article
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
    doc_url = await format_with_qa("article", lesson_id, spec.title, art)
    if not doc_url:
        logger.error(f"❌ {lesson_id} article export failed")
        return None

    # 4️⃣ Format & export MCQs
    sheets = await format_with_qa("mcq", lesson_id, spec.title, qs_sets)
    if not sheets:
        logger.error(f"❌ {lesson_id} mcq export failed")
        return None

    return lesson_id, doc_url, sheets
