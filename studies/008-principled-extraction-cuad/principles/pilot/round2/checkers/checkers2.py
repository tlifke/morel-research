import sys
from pathlib import Path

PILOT = Path(__file__).resolve().parents[2]
if str(PILOT) not in sys.path:
    sys.path.insert(0, str(PILOT))

from checkers import lexicons as L  # noqa: E402
from checkers.checkers import (  # noqa: E402
    Checker,
    d01,
    d02,
    d03,
    d04,
    d05,
    d06,
    d07,
    d08,
    g01,
    g02,
    g03,
    g04,
    g05,
    g06,
    g07,
    g08,
    _gold,
    _present,
)
from checkers.textutil import cached_sentences, normalise  # noqa: E402

from . import lexicons2 as L2

CORPUS = {"derivative_shared_ids": None}


def shared_substring_ids(texts, window=400):
    grams = {}
    for cid, text in texts.items():
        body = normalise(text)
        grams[cid] = {hash(body[i : i + window]) for i in range(0, max(0, len(body) - window + 1))}
    ids = set()
    keys = list(grams)
    for i, a in enumerate(keys):
        for b in keys[i + 1 :]:
            if grams[a] & grams[b]:
                ids.add(a)
                ids.add(b)
    return ids


def set_corpus(texts, window=400):
    CORPUS["derivative_shared_ids"] = shared_substring_ids(texts, window)
    return CORPUS["derivative_shared_ids"]


def p03(instance, category, cue=L2.DERIVATIVE_CUE_STRICT, head=2000, require_shared=True):
    opening = instance.title + "\n" + instance.text[:head]
    if not cue.search(opening):
        return False
    if not require_shared:
        return True
    shared = CORPUS["derivative_shared_ids"]
    if shared is None:
        raise RuntimeError("set_corpus() must be called before p03 is evaluated")
    return instance.contract_id in shared


def p05(instance, category):
    return True


def p09(instance, category, ceiling=L2.CEILING_CUE):
    for _, _, sentence in cached_sentences(instance.text):
        if L.QUANTITY_TOKEN.search(sentence) and ceiling.search(sentence):
            return True
    return False


def p12(instance, category, categories=L2.SINGLE_VALUE_CATEGORIES):
    if category not in categories:
        return False
    return _present(instance, category)


def p17(instance, category, tail=L2.CONFLICTS_TAIL, distance=200):
    if not _present(instance, category):
        return False
    text = instance.text
    for match in tail.finditer(text):
        lo = max(0, match.start() - distance)
        hi = min(len(text), match.end() + distance)
        if L2.GOVERNING_CUE.search(text[lo:hi]):
            return True
    return False


def p20(instance, category, heading=L2.ATTACHMENT_HEADING, block=L2.EXECUTION_BLOCK):
    label = _gold(instance, category)
    if not label or not label.spans:
        return False
    text = instance.text
    marker = block.search(text)
    if not marker:
        return False
    return bool(heading.search(text, marker.end()))


def p21(instance, category, block=L2.EXECUTION_BLOCK, date=L.DATE_LITERAL):
    if not _present(instance, category):
        return False
    text = instance.text
    marker = block.search(text)
    if not marker:
        return False
    return bool(date.search(text, marker.end()))


MATCHED = {
    "p01": "g06",
    "p02": "d06",
    "p04": "g08",
    "p06": "g04",
    "p07": "g07",
    "p08": "g02",
    "p10": "d01",
    "p11": "g05",
    "p13": "d05",
    "p14": "d04",
    "p15": "d03",
    "p16": "d08",
    "p18": "d02",
    "p19": "d07",
    "p22": "g01",
    "p23": "g03",
}

FRESH = ("p03", "p05", "p09", "p12", "p17", "p20", "p21")


REGISTRY = {
    "p01": Checker(
        "p01",
        ["Revenue/Profit Sharing"],
        g06,
        "faithful",
        {"narrow_admin": {"administration": L.ADMINISTRATION_NARROW}},
    ),
    "p02": Checker("p02", ["Agreement Date"], d06, "faithful", {"head4000": {"head": 4000}}),
    "p03": Checker(
        "p03",
        [],
        p03,
        "closest_faithful",
        {
            "cue_only_no_shared_text": {"require_shared": False},
            "wide_cue_no_shared_text": {"cue": L2.DERIVATIVE_CUE, "require_shared": False},
            "wide_derivative_cue": {"cue": L2.DERIVATIVE_CUE},
            "head6000": {"head": 6000},
        },
    ),
    "p04": Checker(
        "p04",
        ["Agreement Date"],
        g08,
        "tightened",
        {"head_only": {"tail": 0}, "wide_window": {"head": 6000, "tail": 6000}},
    ),
    "p05": Checker("p05", [], p05, "faithful", {}),
    "p06": Checker(
        "p06", ["Governing Law"], g04, "faithful", {"wide_venue": {"venue": L.VENUE_WIDE}}
    ),
    "p07": Checker("p07", ["Agreement Date"], g07, "faithful", {}),
    "p08": Checker("p08", [], g02, "faithful", {"marker_omitted_caps": {"marker": "<OMITTED>"}}),
    "p09": Checker(
        "p09",
        ["Volume Restriction"],
        p09,
        "faithful",
        {
            "narrow_ceiling": {"ceiling": L2.CEILING_CUE_NARROW},
            "wide_ceiling": {"ceiling": L2.CEILING_CUE_WIDE},
        },
    ),
    "p10": Checker("p10", ["Agreement Date"], d01, "faithful", {"len60": {"max_len": 60}}),
    "p11": Checker("p11", ["Revenue/Profit Sharing"], g05, "faithful", {}),
    "p12": Checker(
        "p12",
        list(L2.SINGLE_VALUE_CATEGORIES),
        p12,
        "faithful",
        {"agreement_date_only": {"categories": ("Agreement Date",)}},
    ),
    "p13": Checker(
        "p13",
        ["Minimum Commitment", "Volume Restriction"],
        d05,
        "faithful",
        {"lower_only": {"upper": L.LOWER_CUE}, "upper_only": {"lower": L.UPPER_CUE}},
    ),
    "p14": Checker(
        "p14",
        ["Minimum Commitment"],
        d04,
        "faithful",
        {
            "widened_verbs": {"verbs": L.NON_PURCHASE_VERB_WIDE},
            "widened_floor_and_verbs": {
                "verbs": L.NON_PURCHASE_VERB_WIDE,
                "floor": L.FLOOR_CUE_WIDE,
            },
        },
    ),
    "p15": Checker(
        "p15",
        ["Minimum Commitment", "Revenue/Profit Sharing"],
        d03,
        "faithful",
        {"instance_text": {"source": "text"}},
    ),
    "p16": Checker("p16", ["Minimum Commitment"], d08, "faithful", {}),
    "p17": Checker(
        "p17",
        ["Governing Law"],
        p17,
        "faithful",
        {
            "wide_tail": {"tail": L2.CONFLICTS_TAIL_WIDE},
            "distance400": {"distance": 400},
            "distance60": {"distance": 60},
        },
    ),
    "p18": Checker(
        "p18", [], d02, "faithful", {"overlap_any": {"min_iou": 0.0}, "iou80": {"min_iou": 0.8}}
    ),
    "p19": Checker("p19", [], d07, "faithful", {"wide_furniture": {"furniture": L.FURNITURE_WIDE}}),
    "p20": Checker(
        "p20",
        [],
        p20,
        "faithful",
        {
            "strict_heading": {"heading": L2.ATTACHMENT_HEADING_STRICT},
            "narrow_execution_block": {"block": L2.EXECUTION_BLOCK_NARROW},
        },
    ),
    "p21": Checker(
        "p21",
        ["Agreement Date"],
        p21,
        "closest_faithful",
        {"narrow_execution_block": {"block": L2.EXECUTION_BLOCK_NARROW}},
    ),
    "p22": Checker(
        "p22",
        [],
        g01,
        "faithful",
        {"value_categories_included": {"categories": L.YES_NO_CATEGORIES + L.VALUE_CATEGORIES}},
        list(L.YES_NO_CATEGORIES),
    ),
    "p23": Checker("p23", [], g03, "faithful", {"soft_j80": {"threshold": 0.8}}),
}
