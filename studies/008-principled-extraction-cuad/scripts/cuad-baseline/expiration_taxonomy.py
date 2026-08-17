import argparse
import json
import re
from pathlib import Path

STUDY = Path(__file__).resolve().parents[2]
RAW = STUDY / "data" / "raw" / "CUADv1.json"
SPLITS = STUDY / "data" / "processed" / "splits"
OVERRIDES = Path(__file__).with_name("expiration_taxonomy_overrides.json")

MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|"
    "November|December|Jan\\.|Feb\\.|Mar\\.|Apr\\.|Jun\\.|Jul\\.|Aug\\.|"
    "Sept?\\.|Oct\\.|Nov\\.|Dec\\."
)
CALENDAR = re.compile(
    r"(?:" + MONTHS + r")\s*,?\s*\d{0,2}\s*,?\s*\d{4}\b"
    r"|\b\d{1,2}\s*(?:st|nd|rd|th)?\s*(?:day\s+of\s+)?(?:" + MONTHS + r")\s*,?\s*\d{4}\b"
    r"|\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    re.I,
)
NUMWORD = (
    "one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|"
    "fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|twenty-four|"
    "thirty|thirty-six|forty|forty-five|sixty|ninety|one hundred eighty"
)
DURATION = re.compile(
    r"\b(?:" + NUMWORD + r"|\d{1,3})\s*(?:\(\s*\d{1,3}\s*\)\s*)?"
    r"(?:calendar\s+|consecutive\s+)?(?:year|month|day|week|quarter)s?\b"
    r"|\b(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|"
    r"\d{1,3}\s*(?:st|nd|rd|th))\s*(?:\(\s*\d{1,3}\s*(?:st|nd|rd|th)?\s*\)\s*)?"
    r"anniversary",
    re.I,
)
EVENT = re.compile(
    r"unless\s+(?:sooner\s+|earlier\s+|otherwise\s+)?terminated"
    r"|until\s+terminated"
    r"|until\s+(?:such\s+time\s+as\s+)?(?:it\s+|this\s+Agreement\s+)?is\s+terminated"
    r"|shall\s+(?:not\s+be|never\s+be)\s+termina"
    r"|not\s+be\s+terminable|non-?terminable|irrevocab|perpetu"
    r"|until\s+the\s+(?:expiration|termination)\b"
    r"|remain\s+in\s+(?:full\s+force|effect)\s+(?:and\s+effect\s+)?(?:until|unless)"
    r"|continue\s+in\s+(?:full\s+)?force\s+(?:and\s+effect\s+)?(?:until|unless)"
    r"|terminated\s+by\s+either\s+party",
    re.I,
)

END_CUE = re.compile(
    r"\b(?:until|through|thru|to|expir\w*|terminat\w*|end|ends|ending|"
    r"no\s+event\s+beyond)\b",
    re.I,
)

ORDER = ["calendar_date", "duration", "event", "other"]


def classify(text):
    if CALENDAR.search(text):
        return "calendar_date"
    if DURATION.search(text):
        return "duration"
    if EVENT.search(text):
        return "event"
    return "other"


def terminal_date(text):
    for m in CALENDAR.finditer(text):
        if END_CUE.search(text[: m.start()]):
            return True
    return False


def load_split(name):
    if name == "test":
        raise SystemExit("test split is sealed until G4")
    return [
        l.strip()
        for l in SPLITS.joinpath(name + ".txt").read_text().splitlines()
        if l.strip()
    ]


def build(splits):
    overrides = (
        json.loads(OVERRIDES.read_text()) if OVERRIDES.exists() else {}
    )
    raw = json.loads(RAW.read_text())
    by_title = {d["title"]: d for d in raw["data"]}
    rows = []
    for split in splits:
        for title in load_split(split):
            d = by_title[title]
            for q in d["paragraphs"][0]["qas"]:
                if q["id"].rsplit("__", 1)[-1] != "Expiration Date":
                    continue
                for i, a in enumerate(q["answers"]):
                    key = f"{title}#{i}"
                    auto = classify(a["text"])
                    rows.append(
                        {
                            "split": split,
                            "contract": title,
                            "qid": q["id"],
                            "span_index": i,
                            "text": a["text"],
                            "class_auto": auto,
                            "class": overrides.get(key, auto),
                            "overridden": key in overrides,
                            "terminal_date": terminal_date(a["text"]),
                        }
                    )
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", nargs="+", default=["harness_val", "principle_train"])
    ap.add_argument("--out")
    ap.add_argument("--dump", action="store_true")
    args = ap.parse_args()

    rows = build(args.splits)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(rows, indent=2) + "\n")

    for split in args.splits:
        sub = [r for r in rows if r["split"] == split]
        counts = {c: sum(1 for r in sub if r["class"] == c) for c in ORDER}
        contracts = {
            c: len({r["contract"] for r in sub if r["class"] == c}) for c in ORDER
        }
        print(
            split,
            "spans",
            len(sub),
            "contracts",
            len({r["contract"] for r in sub}),
            counts,
            "contracts_by_class",
            contracts,
        )
    if args.dump:
        for r in rows:
            print(
                f"[{r['class']}]{'*' if r['overridden'] else ''} "
                f"{r['contract'][:44]} :: {r['text'][:200]!r}"
            )


if __name__ == "__main__":
    main()
