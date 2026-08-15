from dataclasses import dataclass, field

from . import lexicons as L
from .textutil import (
    any_sentence_matches,
    cached_sentences,
    near,
    normalise,
    sentence_containing,
    signature_block,
)


@dataclass
class Checker:
    id: str
    scope: list
    fn: object
    faithful: str
    variants: dict = field(default_factory=dict)
    eligible: list = field(default_factory=list)

    def applies(self, instance, category, **params):
        if self.scope and category not in self.scope:
            return False
        return bool(self.fn(instance, category, **params))


def _gold(instance, category):
    return instance.gold.get(category)


def _present(instance, category):
    label = _gold(instance, category)
    return bool(label) and not label.is_impossible and bool(label.spans)


def g01(instance, category, categories=L.YES_NO_CATEGORIES):
    if category not in categories:
        return False
    return _present(instance, category)


def g02(instance, category, marker=L.OMITTED_MARKER):
    label = _gold(instance, category)
    if not label:
        return False
    return any(marker in span.text for span in label.spans)


def g03(instance, category, threshold=1.0):
    label = _gold(instance, category)
    if not label or not label.spans:
        return False
    mine = {normalise(span.text) for span in label.spans if len(span.text.strip()) > 0}
    if threshold >= 1.0:
        for other, other_label in instance.gold.items():
            if other == category:
                continue
            if mine & {normalise(span.text) for span in other_label.spans}:
                return True
        return False
    for other, other_label in instance.gold.items():
        if other == category:
            continue
        for text in mine:
            tokens = set(text.split())
            if not tokens:
                continue
            for span in other_label.spans:
                theirs = set(normalise(span.text).split())
                if not theirs:
                    continue
                jaccard = len(tokens & theirs) / len(tokens | theirs)
                if jaccard >= threshold:
                    return True
    return False


def g04(instance, category, venue=L.VENUE):
    return any_sentence_matches(instance.text, venue)


def g05(instance, category, payment=L.PAYMENT_TERM, amount=None):
    text = instance.text
    for _, _, sentence in cached_sentences(text):
        if not payment.search(sentence):
            continue
        if L.PERCENT_TOKEN.search(sentence) or L.CURRENCY_TOKEN.search(sentence):
            return True
    return False


def g06(instance, category, administration=L.ADMINISTRATION):
    for _, _, sentence in cached_sentences(instance.text):
        if administration.search(sentence) and L.ROYALTY_TERM.search(sentence):
            return True
    return False


def g07(instance, category):
    return _present(instance, category)


def g08(instance, category, head=3000, tail=3000, patterns=None):
    patterns = patterns or L.DATE_BLANK_PATTERNS
    zones = [instance.text[:head], signature_block(instance.text, tail)]
    for zone in zones:
        for pattern in patterns:
            if pattern.search(zone):
                return True
    return False


def d01(instance, category, max_len=40):
    label = _gold(instance, category)
    if not label or label.is_impossible or not label.spans:
        return False
    for span in label.spans:
        text = span.text.strip()
        if len(text) >= max_len:
            return False
        if not L.DATE_LONG.fullmatch(text.rstrip(".,;")):
            return False
        found = sentence_containing(instance.text, span.start)
        if not found:
            return False
        _, _, sentence = found
        if text not in sentence or len(text) >= len(sentence.strip()):
            return False
    return True


def d02(instance, category, min_iou=1.0):
    label = _gold(instance, category)
    if not label or not label.spans:
        return False
    for other, other_label in instance.gold.items():
        if other == category:
            continue
        for mine in label.spans:
            for theirs in other_label.spans:
                lo = max(mine.start, theirs.start)
                hi = min(mine.end, theirs.end)
                if hi <= lo:
                    continue
                union = max(mine.end, theirs.end) - min(mine.start, theirs.start)
                if union and (hi - lo) / union >= min_iou:
                    return True
                if min_iou <= 0:
                    return True
    return False


def d03(instance, category, source="gold"):
    scope = ("Minimum Commitment", "Revenue/Profit Sharing")
    if source == "gold":
        for target in scope:
            label = _gold(instance, target)
            if not label:
                continue
            for span in label.spans:
                if L.HAS_SHARE.search(span.text) and L.REVENUE_TERM.search(span.text):
                    return True
        return False
    return any_sentence_matches(instance.text, L.HAS_SHARE, L.REVENUE_TERM)


def d04(instance, category, floor=L.FLOOR_CUE, verbs=L.NON_PURCHASE_VERB, distance=200):
    text = instance.text
    for _, _, sentence in cached_sentences(text):
        if not floor.search(sentence):
            continue
        if not near(floor, L.QUANTITY_TOKEN, sentence, distance):
            continue
        if verbs.search(sentence) and not L.PURCHASE_VERB.search(sentence):
            return True
    return False


def d05(instance, category, lower=L.LOWER_CUE, upper=L.UPPER_CUE):
    for _, _, sentence in cached_sentences(instance.text):
        if not L.QUANTITY_TOKEN.search(sentence):
            continue
        if lower.search(sentence) or upper.search(sentence):
            return True
    return False


def d06(instance, category, head=2000, distance=60):
    label = _gold(instance, category)
    if not label or not label.is_impossible:
        return False
    head_text = instance.text[:head]
    for match in L.DATE_LITERAL.finditer(head_text):
        lo = max(0, match.start() - distance)
        if not L.EXECUTION_CUE.search(head_text[lo : match.start()]):
            return True
    return False


def d07(instance, category, furniture=L.FURNITURE):
    label = _gold(instance, category)
    if not label:
        return False
    text = instance.text
    for span in label.spans:
        body = text[span.start : span.end]
        for match in furniture.finditer(body):
            if match.start() > 0 and match.end() < len(body):
                return True
    return False


def d08(instance, category, cue=L.UNDERTAKING_CUE):
    label = _gold(instance, category)
    if not label or not label.is_impossible:
        return False
    for _, _, sentence in cached_sentences(instance.text):
        if cue.search(sentence) and not L.QUANTITY_TOKEN.search(sentence):
            return True
    return False


REGISTRY = {
    "g01": Checker(
        "g01",
        [],
        g01,
        "faithful",
        {"value_categories_included": {"categories": L.YES_NO_CATEGORIES + L.VALUE_CATEGORIES}},
        list(L.YES_NO_CATEGORIES),
    ),
    "g02": Checker("g02", [], g02, "faithful", {"marker_omitted_caps": {"marker": "<OMITTED>"}}),
    "g03": Checker("g03", [], g03, "faithful", {"soft_j80": {"threshold": 0.8}}),
    "g04": Checker("g04", ["Governing Law"], g04, "faithful", {"wide_venue": {"venue": L.VENUE_WIDE}}),
    "g05": Checker("g05", ["Revenue/Profit Sharing"], g05, "faithful", {}),
    "g06": Checker(
        "g06",
        ["Revenue/Profit Sharing"],
        g06,
        "faithful",
        {"narrow_admin": {"administration": L.ADMINISTRATION_NARROW}},
    ),
    "g07": Checker("g07", ["Agreement Date"], g07, "faithful", {}),
    "g08": Checker(
        "g08",
        ["Agreement Date"],
        g08,
        "tightened_per_D19",
        {"head_only": {"tail": 0}, "wide_window": {"head": 6000, "tail": 6000}},
    ),
    "d01": Checker("d01", ["Agreement Date"], d01, "faithful", {"len60": {"max_len": 60}}),
    "d02": Checker("d02", [], d02, "faithful", {"overlap_any": {"min_iou": 0.0}, "iou80": {"min_iou": 0.8}}),
    "d03": Checker(
        "d03",
        ["Minimum Commitment", "Revenue/Profit Sharing"],
        d03,
        "faithful",
        {"instance_text": {"source": "text"}},
    ),
    "d04": Checker(
        "d04",
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
    "d05": Checker(
        "d05",
        ["Minimum Commitment", "Volume Restriction"],
        d05,
        "faithful",
        {"lower_only": {"upper": L.LOWER_CUE}, "upper_only": {"lower": L.UPPER_CUE}},
    ),
    "d06": Checker("d06", ["Agreement Date"], d06, "faithful", {"head4000": {"head": 4000}}),
    "d07": Checker("d07", [], d07, "faithful", {"wide_furniture": {"furniture": L.FURNITURE_WIDE}}),
    "d08": Checker("d08", ["Minimum Commitment"], d08, "faithful", {}),
}
