# File: core/agents.py
from agents import Runner, Agent
from config import MODEL_THINK, MODEL_HEAVY, MODEL_LIGHT
from utils.prompt_loader import _load_prompt, _inject_guides

brainstormer = Agent(
    name="Brainstormer",
    model=MODEL_THINK,
    instructions=_load_prompt("brainstormer.md"),
)
reviewer = Agent(
    name="Reviewer",
    model=MODEL_LIGHT,
    instructions=_load_prompt("reviewer.md"),
)
lesson_writer = Agent(
    name="Lesson Writer",
    model=MODEL_HEAVY,
    instructions=_load_prompt("lesson_writer.md"),
)
problem_generator = Agent(
    name="Problem Generator",
    model=MODEL_HEAVY,
    instructions=_load_prompt("problem_generator.md"),
)
qa_agent = Agent(
    name="QA Agent",
    model=MODEL_LIGHT,
    instructions=_load_prompt("qa_agent.md"),
)
formatter = Agent(
    name="Formatter",
    model=MODEL_LIGHT,
    instructions=_inject_guides(_load_prompt("formatter.md")),
)
format_qa_agent = Agent(
    name="Format QA Agent",
    model=MODEL_LIGHT,
    instructions=_inject_guides(_load_prompt("format_qa_agent.md")),
)
