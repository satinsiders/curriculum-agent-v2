import logging
from logging import LoggerAdapter, getLogger

_base_logger = getLogger(__name__)

def with_lesson_id(lesson_id: str) -> LoggerAdapter:
    """
    Returns a LoggerAdapter that injects 'lesson_id' into all log records.
    """
    return LoggerAdapter(_base_logger, {"lesson_id": lesson_id})
