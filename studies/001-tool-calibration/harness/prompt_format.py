"""Prompt formatting for Gemma 3 IT.

Gemma 3 instruction-tuned models expect a specific turn structure:

    <bos><start_of_turn>user
    {SYSTEM PROMPT}

    {USER PROMPT}<end_of_turn>
    <start_of_turn>model

Gemma 3 has no dedicated `system` role — system text is prepended to
the first user turn. Tool definitions and function-calling
expectations are also injected as natural-language instructions
inside the system text, since Gemma 3 IT doesn't have a separate
`tools` parameter (per the model card / Google AI dev docs).

This module's `build_prompt(record, manifest, system_prompts_dir,
tool_defs)` returns the formatted string ready to send to the
inference backend.
"""

from __future__ import annotations

import json
from pathlib import Path


def load_system_prompt_manifest(manifest_path: Path) -> dict[str, dict]:
    """Load `system_prompts/manifest.json` into an id→entry dict."""
    data = json.loads(manifest_path.read_text())
    return {entry["id"]: entry for entry in data["prompts"]}


def load_system_prompt_body(
    manifest_entry: dict, system_prompts_dir: Path
) -> str:
    return (system_prompts_dir / manifest_entry["template"]).read_text().strip()


_TOOL_BLOCK_INSTRUCTIONS = """
When you decide to use a tool, emit a code block tagged `tool_code`
containing the function call. Wait for the tool result (delivered as
a `tool_output` block) before producing your final reply. If no tool
is appropriate, answer directly.

Example:

```tool_code
calculator(expression="3 * 17")
```
""".strip()


def build_prompt(
    record: dict,
    *,
    system_body: str,
    include_tool_block_instructions: bool = True,
) -> str:
    """Build the Gemma 3 IT-formatted prompt for one record.

    `system_body` is the loaded template text for record's
    `system_prompt_id`. `include_tool_block_instructions` appends a
    short note teaching the model the `tool_code` / `tool_output`
    convention so a no-system-instruction Ollama setup still elicits
    the right output shape.
    """
    system_text = system_body
    if include_tool_block_instructions:
        system_text = system_text + "\n\n" + _TOOL_BLOCK_INSTRUCTIONS

    return (
        "<bos><start_of_turn>user\n"
        f"{system_text}\n\n{record['user_prompt']}<end_of_turn>\n"
        "<start_of_turn>model\n"
    )
