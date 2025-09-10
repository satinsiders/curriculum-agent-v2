# File: utils/prompt_loader.py
from config import PROMPTS_DIR

def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SystemExit(f"❌ Prompt file missing: {path}") from exc

FORMAT_GUIDE     = _load_prompt("format_guide.md")
FORMAT_GUIDE_MCQ = _load_prompt("format_guide_mcq.md")

def _inject_guides(template: str) -> str:
    return (
        template
        .replace("{FORMAT_GUIDE}", FORMAT_GUIDE)
        .replace("{FORMAT_GUIDE_MCQ}", FORMAT_GUIDE_MCQ)
    )
