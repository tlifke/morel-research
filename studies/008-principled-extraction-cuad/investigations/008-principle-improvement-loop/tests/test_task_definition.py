from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

INV = Path(__file__).resolve().parents[1]
STUDY = INV.parents[1]
sys.path.insert(0, str(STUDY / "scripts"))

import contracteval_prompt as cep

TD = INV / "task_definition" / "v1.json"
BUILDER = INV / "scripts" / "build_task_definition.py"

PINNED_SHA = "dd568b11b83a2d017f2f0211a56064bb1c4400281372f9ebf7a7c2dd5d86bd81"


def load():
    return json.loads(TD.read_text())


def test_content_sha_is_pinned():
    assert load()["content_sha256"] == PINNED_SHA


def test_content_sha_covers_the_content():
    d = load()
    body = {"version": d["version"], "instruction_text": d["instruction_text"], "questions": d["questions"]}
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    assert digest == d["content_sha256"]


def test_instruction_text_is_contracteval_verbatim():
    d = load()
    assert d["instruction_text"] == cep.SYSTEM_PROMPT
    assert hashlib.sha256(cep.SYSTEM_PROMPT.encode()).hexdigest() == cep.SYSTEM_PROMPT_SHA256


def test_questions_are_cuad_verbatim():
    d = load()
    src = json.loads((STUDY / "data/raw/CUADv1.json").read_text())
    seen = {}
    for doc in src["data"]:
        for para in doc["paragraphs"]:
            for qa in para["qas"]:
                seen[qa["id"].split("__")[-1]] = qa["question"]
    assert d["questions"] == {c: seen[c] for c in d["questions"]}


def test_all_41_categories_present():
    d = load()
    categories = json.loads((STUDY / "data/processed/categories.json").read_text())
    assert list(d["questions"]) == categories["all"]
    assert len(d["questions"]) == 41


def test_answer_format_never_reaches_the_model():
    d = load()
    reaches_model = d["instruction_text"] + "".join(d["questions"].values())
    assert "answer_format" not in reaches_model
    assert "Yes/No" not in reaches_model
    assert any("answer_format" in e["what"] for e in d["excluded"])


def test_rebuild_is_byte_identical():
    before = TD.read_bytes()
    subprocess.run([sys.executable, str(BUILDER)], check=True)
    assert TD.read_bytes() == before
