import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claude_agent_sdk_shim import ClaudeAgentOptions
from claude_agent_sdk_shim.model_registry import (
    MODEL_REGISTRY,
    get_model_entry,
    list_models,
)


def test_registry_has_expected_models():
    keys = set(list_models())
    assert {"qwen3.5:4b", "qwen3:4b", "nemotron-3-nano:4b", "gemma4:e4b"} <= keys


def test_entry_fields_present():
    e = get_model_entry("qwen3.5:4b")
    assert e is not None
    assert e.ollama_tag == "qwen3.5:4b"
    assert e.family == "qwen3.5"
    assert e.max_tokens_default == 8192
    assert e.thinking_mode == "block"
    assert e.recommended_hint and "Bash" in e.recommended_hint


def test_thinking_modes_per_family():
    assert get_model_entry("gemma4:e4b").thinking_mode == "block"
    assert get_model_entry("nemotron-3-nano:4b").thinking_mode == "sidecar"
    assert get_model_entry("qwen3:4b").recommended_hint is None
    assert get_model_entry("nemotron-3-nano:4b").recommended_hint is None
    assert get_model_entry("gemma4:e4b").recommended_hint is None


def test_get_unknown_model_returns_none():
    assert get_model_entry("does-not-exist") is None


def test_from_registry_populates_defaults():
    opts = ClaudeAgentOptions.from_registry("qwen3.5:4b")
    assert opts.model == "qwen3.5:4b"
    assert opts.max_tokens == 8192
    assert opts.model_family == "qwen3.5"
    assert opts.thinking_mode == "block"
    assert opts.tool_invocation_hint is not None and "Bash" in opts.tool_invocation_hint


def test_from_registry_override_precedence():
    opts = ClaudeAgentOptions.from_registry(
        "qwen3.5:4b",
        max_tokens=2048,
        tool_invocation_hint="custom hint",
        system_prompt="hi",
    )
    assert opts.max_tokens == 2048
    assert opts.tool_invocation_hint == "custom hint"
    assert opts.system_prompt == "hi"
    assert opts.model_family == "qwen3.5"


def test_from_registry_unknown_raises():
    with pytest.raises(KeyError):
        ClaudeAgentOptions.from_registry("not-a-model")


def test_post_init_resolves_metadata_only():
    opts = ClaudeAgentOptions(model="nemotron-3-nano:4b")
    assert opts.model_family == "nemotron"
    assert opts.thinking_mode == "sidecar"
    assert opts.model_notes and "Mamba" in opts.model_notes
    assert opts.tool_invocation_hint is None


def test_post_init_does_not_apply_hint_implicitly():
    opts = ClaudeAgentOptions(model="qwen3.5:4b")
    assert opts.tool_invocation_hint is None


def test_post_init_unknown_model_is_noop():
    opts = ClaudeAgentOptions(model="some-other:tag")
    assert opts.model_family is None
    assert opts.thinking_mode is None


def test_post_init_preserves_explicit_metadata():
    opts = ClaudeAgentOptions(model="qwen3.5:4b", model_family="custom")
    assert opts.model_family == "custom"
