"""Runtime anchor for tool execution.

Per Decision 18, datetime_now and any other runtime-dependent tools
must return values tied to a fixed anchor so that grading runs
performed at different wall-clock times stay comparable. The anchor
is the date the seed corpus was authored.
"""

RUNTIME_ANCHOR = "2026-05-11T12:00:00Z"
