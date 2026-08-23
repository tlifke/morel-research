from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(STUDY / "scripts"))

import contracteval_prompt as cep

RAW = STUDY / "data/raw/CUADv1.json"
CATEGORIES = STUDY / "data/processed/categories.json"
OUT = Path(__file__).resolve().parents[1] / "task_definition" / "v1.json"

VERSION = "v1"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def canonical_questions() -> dict[str, str]:
    src = json.loads(RAW.read_text())
    out: dict[str, str] = {}
    for doc in src["data"]:
        for para in doc["paragraphs"]:
            for qa in para["qas"]:
                category = qa["id"].split("__")[-1]
                question = qa["question"]
                if category in out and out[category] != question:
                    raise ValueError(f"question text is not canonical for {category}")
                out[category] = question
    return out


def main() -> None:
    categories = json.loads(CATEGORIES.read_text())
    questions = canonical_questions()

    expected = set(categories["all"])
    if set(questions) != expected:
        raise ValueError(f"category mismatch: {set(questions) ^ expected}")

    body = {
        "version": VERSION,
        "instruction_text": cep.SYSTEM_PROMPT,
        "questions": {c: questions[c] for c in categories["all"]},
    }
    content_sha = sha(json.dumps(body, sort_keys=True, ensure_ascii=False))

    payload = {
        **body,
        "content_sha256": content_sha,
        "provenance": {
            "instruction_text": {
                "source": cep.UPSTREAM_SOURCE,
                "sha256": cep.SYSTEM_PROMPT_SHA256,
                "verbatim": True,
            },
            "questions": {
                "source": "CUAD v1 (data/raw/CUADv1.json), the question string CUAD ships per category",
                "verbatim": True,
                "note": "each question embeds CUAD's own category description after 'Details:'",
                "attribution": categories["attribution"],
            },
        },
        "adaptations": [
            {
                "what": "absence signalling",
                "upstream": 'the literal reply "No related clause."',
                "here": "an AbsenceClaim record for the category in TaskOutput",
                "why": "the upstream convention is specific to one free-text reply per question; "
                       "this harness emits one structured decision per category in a single response",
                "note": "the frozen instruction_text still contains the upstream sentence verbatim, so "
                        "the wrapper's OUTPUT FORMAT block reconciles it explicitly and forbids emitting "
                        "the phrase as extracted text. Left in the frozen text on purpose: editing it "
                        "would break the verbatim claim and the hash pin.",
            },
            {
                "what": "question packaging",
                "upstream": "one call per (contract, question), 41 calls per contract",
                "here": "one call per contract carrying all 41 questions and returning 41 decisions",
                "why": "the harness contract is one decision per category per contract (D-14). The "
                       "question and instruction text are unchanged; only the number of calls differs. "
                       "The cost of this repackaging is measured, not assumed - see the "
                       "ContractEval-native calibration arm.",
            },
        ],
        "excluded": [
            {
                "what": "CUAD's per-category answer_format field",
                "why": "ContractEval's prompt does not use it, and it states Yes/No for most categories "
                       "while CUAD's gold is text spans. Including it reintroduces the answer-granularity "
                       "defect already measured in this study (nine of twelve targets instructed to answer "
                       "yes/no). Excluded deliberately, not by oversight.",
            }
        ],
        "scaffolding": {
            "what": "the JSON output contract (TaskOutput: extractions, absent, explanation, principles_cited)",
            "status": "harness scaffolding, not part of the task definition",
            "invariant": "identical across every arm of every rung, so it cannot confound a principle delta",
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
