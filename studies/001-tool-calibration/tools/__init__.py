"""Tool execution layer for study 001 (tool-calibration).

Each tool is a callable matching the signature in
`investigations/001-foundations/tool_palette.py`. Unlike the palette
definitions (which raise NotImplementedError), these return real
values. Used by the A2 calibration harness and downstream phases.

Conventions:
- `datetime_now` always returns a fixed value tied to RUNTIME_ANCHOR
  (Decision 18: tool reproducibility for grading).
- `general_knowledge_lookup` reads `kb/general_knowledge_real.json` by
  default (Decision 19: verified KB is canonical). Pass
  `source="fabricated"` to query the fabricated KB instead.
- All lookups return the shape `{"results": [...]}` per Decision 8.
"""

from .runtime import RUNTIME_ANCHOR
from .calculator import calculator
from .python_execute import python_execute
from .datetime_now import datetime_now
from .unit_convert import unit_convert
from .general_knowledge_lookup import general_knowledge_lookup
from .user_knowledge_lookup import user_knowledge_lookup

__all__ = [
    "RUNTIME_ANCHOR",
    "calculator",
    "python_execute",
    "datetime_now",
    "unit_convert",
    "general_knowledge_lookup",
    "user_knowledge_lookup",
]
