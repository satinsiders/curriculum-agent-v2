import asyncio, logging
from typing import Any, Callable, Dict
from core.agents import Agent, Runner, qa_agent
from utils.io_helpers import as_input_items, _jitter, safe_json
from utils.log_helpers import with_lesson_id
from config import RETRY_BACKOFF, MAX_RETRY_DELAY, MAX_LOOPS


#-------------------------------------------------------
#     actual QA loop of calling and running agents
#-------------------------------------------------------

async def looper(
    agent: Agent,
    lesson_id: str,
    kind: str,
    initial_payload: Any,
    runner_fn: Callable[[Any], Any],
    success_fn: Callable[[Any], bool],
    update_payload_fn: Callable[[Any, Any], Any] = None,
) -> Any:
    """
    - runner_fn(payload)              → coroutine that runs your agent(s) via run_with_retry  
    - success_fn(result)              → returns True if we’re done  
    - update_payload_fn(payload, res) → new payload for next iteration  
    """
    logger = with_lesson_id(lesson_id)
    payload = initial_payload
    delay = RETRY_BACKOFF

    for attempt in range(1, MAX_LOOPS + 1):
        logger.info(f"🌀 {agent.name} {kind} attempt {attempt}/{MAX_LOOPS}")
        result = await runner_fn(payload)

        # 1️⃣ Run the success check (sync or async)
        ok = success_fn(result)
        if asyncio.iscoroutine(ok):
            ok = await ok
        if ok:
            logger.info(f"✅ {agent.name} {kind} succeeded on attempt {attempt}")
            return result

        # 2️⃣ Last attempt → give up
        if attempt == MAX_LOOPS:
            # run one more QA on the last result
            try:
                last_qa = safe_json(
                    (await run_with_retry(qa_agent, {"payload": result}, lesson_id)).final_output
                )
                fb = last_qa.get("feedback", "").lower()
            except Exception:
                fb = ""
            # if it’s *only* randomization, accept the draft
            if "randomiz" in fb:
                logger.warning(
                    f"⚠️ [{lesson_id}-{kind}] failed QA only due to answer-choice randomization; accepting last result"
                )
                return result
            # otherwise, real failure
        
            logger.error(f"❌ {agent.name} {kind} failed after {MAX_LOOPS} attempts")
            return None

        # 3️⃣ Compute a new payload for the next iteration (sync or async)
        if update_payload_fn:
            new_payload = update_payload_fn(payload, result)
            if asyncio.iscoroutine(new_payload):
                payload = await new_payload
            else:
                payload = new_payload

        # 4️⃣ Sleep before retrying
        await asyncio.sleep(_jitter(delay))
        delay = min(delay * 2, MAX_RETRY_DELAY)


#------------------------------------------------------------------
#     make one agent call reliable against transient failures
#     (network hiccups, rate-limits, JSON parse-errors, etc.)
#------------------------------------------------------------------
async def run_with_retry(
    agent: Agent,
    payload: Any,
    lesson_id: str,
    **kw,
) -> Any:
    logger = with_lesson_id(lesson_id)
    delay = RETRY_BACKOFF

    for attempt in range(1, MAX_LOOPS + 1):
        try:
            # one “bare” call; no info-level logs on success
            return await Runner.run(agent, as_input_items(payload), **kw)
        except Exception as exc:
            # warn on each failure
            logger.warning(
                f"[API] ⚠️  {agent.name} call failed "
                f"[API] (attempt {attempt}/{MAX_LOOPS}): {exc}"
            )
            if attempt == MAX_LOOPS:
                # error if we can't recover
                logger.error(f"[API] ❌  {agent.name} failed after {attempt} attempts")
                raise
            # back off then retry
            await asyncio.sleep(_jitter(delay))
            delay = min(delay * 2, MAX_RETRY_DELAY)
