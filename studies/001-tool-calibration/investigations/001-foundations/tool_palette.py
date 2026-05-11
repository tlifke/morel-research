"""Tool palette for the matched-pair tool-calibration study.

Five tools, frozen. Each is callable in principle but the study only
needs detection of the call — no real execution is required, since
matched-pair grading is based on whether the model decides to call,
not on tool output correctness.

The signatures and one-line docstrings below are the authoritative
spec; mirror them in the JSON manifest (`tool_palette.json`) before
running any experiment.

Design principles (from the source brief, frozen 2026-05-11):

1. No external state required.
2. Cover qualitatively different cognitive moments:
   compute-I-can't-do, look-up-I-don't-know,
   transform-deterministically.
3. Five tools, no more, no fewer.
4. Each tool's signature must be unambiguous — the model should
   never be confused about *how* to call it, only *whether* to.
"""

from __future__ import annotations


def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression and return the exact result.

    Examples:
        calculator("47*83")
        calculator("sqrt(2)")
    """
    raise NotImplementedError("Detection-only tool; no execution required.")


def python_execute(code: str) -> str:
    """Run a snippet of Python and return its stdout. Use when the
    `calculator` tool is insufficient (loops, string manipulation,
    multi-step computation).

    Examples:
        python_execute("print(sum(range(1, 101)))")
        python_execute("import math; print(math.factorial(20))")
    """
    raise NotImplementedError("Detection-only tool; no execution required.")


def datetime_now() -> str:
    """Return the current date and time as an ISO-8601 string.
    Takes no arguments.

    Examples:
        datetime_now()
    """
    raise NotImplementedError("Detection-only tool; no execution required.")


def unit_convert(value: float, from_unit: str, to_unit: str) -> str:
    """Convert a numeric quantity between two units. Both unit names
    are case-insensitive plain strings (e.g. "kg", "lb", "meters",
    "ft", "celsius", "fahrenheit").

    Examples:
        unit_convert(180, "cm", "in")
        unit_convert(72, "fahrenheit", "celsius")
    """
    raise NotImplementedError("Detection-only tool; no execution required.")


def knowledge_lookup(query: str) -> str:
    """Look up a fact in an external knowledge base. Stand-in for web
    search; returns a short string answer for the query. Use when the
    answer is a discrete fact (date, name, value) you may not reliably
    know.

    Examples:
        knowledge_lookup("capital of Mongolia")
        knowledge_lookup("year the Eiffel Tower was completed")
    """
    raise NotImplementedError("Detection-only tool; no execution required.")


# Convenience: the canonical ordered tuple of tool names.
TOOLS = (
    "calculator",
    "python_execute",
    "datetime_now",
    "unit_convert",
    "knowledge_lookup",
)
