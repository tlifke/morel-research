import json
from functools import cached_property
from pathlib import Path

from pydantic import BaseModel

STUDY = Path(__file__).resolve().parent.parent
PROCESSED = STUDY / "data" / "processed"
RAW = STUDY / "data" / "raw"

SPLITS = ("harness_val", "test", "principle_train", "principle_val", "model_train", "scratch")


class GoldSpan(BaseModel):
    start: int
    end: int
    text: str


class GoldLabel(BaseModel):
    category: str
    is_impossible: bool
    spans: list[GoldSpan]


class Instance(BaseModel):
    contract_id: str
    title: str
    text: str
    n_tokens: int
    split: str
    gold: dict[str, GoldLabel]


class CuadDataset:
    def __init__(self, processed_dir=PROCESSED, raw_dir=RAW, categories=None):
        self._processed = Path(processed_dir)
        self._raw = Path(raw_dir)
        self._categories_override = list(categories) if categories else None

    @cached_property
    def _manifest(self):
        return json.loads((self._processed / "manifest.json").read_text())

    @cached_property
    def _catalog(self):
        return json.loads((self._processed / "categories.json").read_text())

    @cached_property
    def _records(self):
        rows = {}
        with open(self._processed / "instances.jsonl") as fh:
            for line in fh:
                row = json.loads(line)
                rows[row["contract_id"]] = row
        return rows

    @cached_property
    def _text(self):
        texts = {}
        for article in json.loads((self._raw / "CUADv1.json").read_text())["data"]:
            texts[article["title"]] = article["paragraphs"][0]["context"]
        return texts

    @property
    def texts(self):
        return self._text

    def record(self, contract_id):
        return self._records.get(contract_id)

    def split_file(self, split):
        if split not in SPLITS:
            raise ValueError(f"unknown split {split!r}; expected one of {SPLITS}")
        return self._processed / "splits" / f"{split}.txt"

    def all_contract_ids(self):
        return sorted(self._records)

    @property
    def categories(self):
        return list(self._categories_override or self._catalog["subset"])

    @property
    def all_categories(self):
        return list(self._catalog["all"])

    def contract_ids(self, split):
        if split not in SPLITS:
            raise ValueError(f"unknown split {split!r}; expected one of {SPLITS}")
        return (self._processed / "splits" / f"{split}.txt").read_text().split("\n")[:-1]

    def gold(self, contract_id):
        record = self._records[contract_id]
        text = self._text[contract_id]
        out = {}
        for category in self.categories:
            entry = record["gold"][category]
            out[category] = GoldLabel(
                category=category,
                is_impossible=entry["is_impossible"],
                spans=[
                    GoldSpan(start=start, end=end, text=text[start:end])
                    for start, end in entry["spans"]
                ],
            )
        return out

    def get_instance(self, contract_id):
        record = self._records[contract_id]
        return Instance(
            contract_id=contract_id,
            title=record["title"],
            text=self._text[contract_id],
            n_tokens=record["n_tokens"],
            split=record["split"],
            gold=self.gold(contract_id),
        )

    def load_instances(self, split):
        return [self.get_instance(cid) for cid in self.contract_ids(split)]
