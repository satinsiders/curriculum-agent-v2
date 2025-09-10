import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

import asyncio
from core.formatter import run_with_retry
from core.agents import formatter

async def main():
    payload = {
        "type": "article",
        "lesson_id": "SMOKE01",
        "title": "Smoke Test",
        "content": "Raw **bold** text → needs formatting."
    }
    out = await run_with_retry(formatter, payload)
    print("Formatter output:", out.final_output)

if __name__ == "__main__":
    asyncio.run(main())
