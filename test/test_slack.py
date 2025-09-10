# test_slack.py
import os
import asyncio
from dotenv import load_dotenv, find_dotenv
import httpx
import logging

# 1) Load .env (or warn if missing)
dotenv_path = find_dotenv()
if not dotenv_path:
    print("⚠️  No .env file found; SLACK_WEBHOOK will be empty")
else:
    load_dotenv(dotenv_path, override=True)

# 2) Optional: bump logging to DEBUG
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")

async def test_slack():
    webhook = os.getenv("SLACK_WEBHOOK")
    logging.debug(f"Using webhook: {webhook!r}")
    if not webhook:
        print("❌ SLACK_WEBHOOK not set in environment")
        return

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(webhook, json={"text": "✅ This is a test message from test_slack.py"})
    print(f"Response status: {resp.status_code}")
    print(f"Response body:   {resp.text}")

if __name__ == "__main__":
    asyncio.run(test_slack())

