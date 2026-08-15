import re

from . import lexicons as L
from .textutil import near

EQUITY_NOUN = re.compile(
    r"shares? of (?:common |preferred |capital )?(?:stock|shares)|"
    r"\bwarrants?\b|equity interest|unregistered shares|shares of the (?:company|issuer)",
    re.I,
)

PERCENT_OR_REDACTED = re.compile(
    r"\d+(?:\.\d+)?\s*%|\bpercent\b|\bpercentage\b|\[\*+\]\s*%|\[\s*\*+\s*\]\s*%|"
    r"\b\d{1,3}\s*/\s*\d{1,3}\b",
    re.I,
)

REVENUE_TERM_WIDE = re.compile(
    r"revenue|profit|\bsales\b|margin|gross receipts|net receipts|\bincome\b|"
    r"\bproceeds\b|purchase price|net assets|\bturnover\b|\brebate\b",
    re.I,
)

REVENUE_ENTITLEMENT_VERB = re.compile(
    r"\b(?:share|shares|split|distribut\w*|entitled to (?:all |a )?)\b[^.;]{0,60}"
    r"(?:revenue|profit|\bsales\b|income|proceeds)",
    re.I,
)

BASED_ON_REVENUE = re.compile(
    r"(?:based (?:up)?on|according to|equal to|a function of|calculated on)[^.;]{0,60}"
    r"(?:revenue|profit|\bsales\b|income|margin|proceeds|net assets)",
    re.I,
)


def g05_entitlement_signal(span_text):
    if near(L.PERCENT_TOKEN, L.REVENUE_TERM, span_text, 60):
        return "percentage_of_revenue"
    if L.PER_UNIT.search(span_text):
        return "per_unit"
    if L.EQUITY.search(span_text):
        return "equity"
    return None


def g05_span_passes(span_text):
    return g05_entitlement_signal(span_text) is not None


def g05_entitlement_signal_repaired(span_text):
    if near(PERCENT_OR_REDACTED, REVENUE_TERM_WIDE, span_text, 60):
        return "percentage_of_revenue"
    if L.PER_UNIT.search(span_text):
        return "per_unit"
    if BASED_ON_REVENUE.search(span_text):
        return "based_on_revenue"
    if REVENUE_ENTITLEMENT_VERB.search(span_text):
        return "revenue_entitlement"
    if EQUITY_NOUN.search(span_text):
        return "equity"
    return None


def g06_administration_only(span_text):
    if not L.ADMINISTRATION.search(span_text):
        return False
    return not g05_span_passes(span_text)
