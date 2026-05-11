"""datetime_now — returns the fixed runtime anchor (Decision 18)."""

from .runtime import RUNTIME_ANCHOR


def datetime_now() -> str:
    return RUNTIME_ANCHOR
