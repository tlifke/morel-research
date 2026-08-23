import hashlib
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(STUDY / "scripts"))

import contracteval_prompt as cep


def sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def test_user_template_matches_upstream_bytes():
    assert sha(cep.USER_TEMPLATE) == cep.USER_TEMPLATE_SHA256


def test_system_prompt_matches_upstream_bytes():
    assert sha(cep.SYSTEM_PROMPT) == cep.SYSTEM_PROMPT_SHA256


def test_context_line_keeps_trailing_space():
    assert cep.USER_TEMPLATE.startswith("Context: \n")


def test_render_shape():
    msgs = cep.render("CTX", "Q")
    assert [m["role"] for m in msgs] == ["system", "user"]
    assert msgs[1]["content"] == "Context: \n```\nCTX\n```\nQuestion:\n```\nQ\n```\n"


def test_declination_detection_is_substring_anywhere():
    assert cep.is_declination("No related clause.")
    assert cep.is_declination("  `no related clause`  ")
    assert cep.is_declination("After review, there is no related clause here.")
    assert not cep.is_declination("The term shall commence on the Effective Date.")


def test_declination_yields_no_spans():
    assert cep.response_to_spans("No related clause.") == []


def test_spans_split_on_blank_lines():
    raw = "First sentence here.\n\nSecond sentence here."
    assert cep.response_to_spans(raw) == ["First sentence here.", "Second sentence here."]


def test_spans_split_on_single_newlines_when_no_blank_lines():
    raw = "First sentence here.\nSecond sentence here."
    assert cep.response_to_spans(raw) == ["First sentence here.", "Second sentence here."]


def test_spans_strip_code_fence_and_bullets():
    raw = "```\n- First one.\n- Second one.\n```"
    assert cep.response_to_spans(raw) == ["First one.", "Second one."]


def test_empty_response_yields_no_spans():
    assert cep.response_to_spans("") == []
    assert cep.response_to_spans(None) == []
