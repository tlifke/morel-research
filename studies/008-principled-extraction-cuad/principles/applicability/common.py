import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
WORK = HERE / "work"
FROZEN = HERE / "frozen"

if str(STUDY / "scripts") not in sys.path:
    sys.path.insert(0, str(STUDY / "scripts"))

from cuad_dataset import CuadDataset  # noqa: E402


def config():
    return yaml.safe_load((HERE / "config.yaml").read_text())


def working_set():
    return yaml.safe_load((STUDY / "principles" / "working_set.yaml").read_text())


def principles():
    return {rec["id"]: rec for rec in working_set()["principles"]}


def category_definitions():
    import csv

    fold = {
        " ": " ",
        "‘": "'",
        "’": "'",
        "‚": "'",
        "“": '"',
        "”": '"',
        "„": '"',
    }

    def normalize(text):
        for bad, good in fold.items():
            text = text.replace(bad, good)
        return " ".join(text.split())

    out = {}
    path = STUDY / "data" / "raw" / "category_descriptions.csv"
    with open(path, encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            name = row["Category (incl. context and answer)"].split(": ", 1)[1].strip()
            description = row["Description"].split(": ", 1)[1].strip()
            out[normalize(name).lower()] = normalize(description)
    return out, normalize


def dataset():
    return CuadDataset()


def eligible_categories(record, categories):
    scope = record.get("scope") or []
    return [c for c in categories if not scope or c in scope]


def questions_for(record_ids, principles_by_id, categories):
    out = []
    for pid in record_ids:
        for category in eligible_categories(principles_by_id[pid], categories):
            out.append((pid, category))
    return out


def manifest():
    return json.loads((WORK / "manifest.json").read_text())


def load_responses():
    rows = {}
    for path in sorted((WORK / "responses").glob("*.json")):
        rows[path.stem] = json.loads(path.read_text())
    return rows


def clip(text, cap):
    if len(text) <= cap["max_chars"]:
        return text, False
    head = text[: cap["head_chars"]]
    tail = text[-cap["tail_chars"] :]
    return head + "\n\n[... middle of contract omitted for labelling ...]\n\n" + tail, True
