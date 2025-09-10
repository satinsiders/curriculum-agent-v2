import sys
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ──────────────────────────────
# PATH & MODELS
# ──────────────────────────────
ROOT = Path(__file__).parent
PROMPTS_DIR = ROOT / "prompts"

MODEL_THINK = os.getenv("MODEL_THINK", "o3")
MODEL_HEAVY = os.getenv("MODEL_HEAVY", "gpt-4.1")
MODEL_LIGHT = os.getenv("MODEL_LIGHT", "o4-mini")

# ──────────────────────────────
# WORKFLOW CONFIG
# ──────────────────────────────
MAX_LOOPS = 4
MAX_PARALLEL_LESSONS = int(os.getenv("MAX_PARALLEL_LESSONS", "15"))
RETRY_BACKOFF = 2
MAX_RETRY_DELAY = 30

# ──────────────────────────────
# LOGGING
# ──────────────────────────────
# 1️⃣ A “safe” Formatter that always ensures record.lesson_id exists.
class SafeFormatter(logging.Formatter):
    def format(self, record):
        # If no adapter gave us a lesson_id, default to "N/A"
        if not hasattr(record, "lesson_id"):
            record.lesson_id = "N/A"
        return super().format(record)

# 2️⃣ Build our single handler
fmt = "%(asctime)s %(levelname)-8s %(name)s [%(lesson_id)s] | %(message)s"
datefmt = "%Y-%m-%d %H:%M:%S"

handler = logging.StreamHandler()                   # write to stdout/stderr
handler.setFormatter(SafeFormatter(fmt=fmt, datefmt=datefmt))

# 3️⃣ Configure the root logger
root = logging.getLogger()
root.handlers.clear()                               # ditch any defaults
root.addHandler(handler)
root.setLevel(os.getenv("LOGLEVEL", "INFO"))
