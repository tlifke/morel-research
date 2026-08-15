import re

YES_NO_CATEGORIES = (
    "Anti-Assignment",
    "Cap On Liability",
    "License Grant",
    "Exclusivity",
    "Revenue/Profit Sharing",
    "Minimum Commitment",
    "Volume Restriction",
    "Most Favored Nation",
    "Source Code Escrow",
)

VALUE_CATEGORIES = (
    "Agreement Date",
    "Effective Date",
    "Expiration Date",
    "Governing Law",
    "Parties",
    "Document Name",
)

PILOT_CATEGORIES = (
    "Minimum Commitment",
    "Volume Restriction",
    "Revenue/Profit Sharing",
    "Agreement Date",
    "Governing Law",
)

OMITTED_MARKER = "<omitted>"

VENUE = re.compile(
    r"exclusive jurisdiction|submits? to the jurisdiction|\bvenue\b|"
    r"inconvenient forum|arbitration|courts located in|courts situated in",
    re.I,
)

VENUE_WIDE = re.compile(
    r"exclusive jurisdiction|submits? to the jurisdiction|\bvenue\b|"
    r"inconvenient forum|arbitrat(?:ion|or|e)|courts? (?:located|situated|sitting) in|"
    r"forum non conveniens|consent to the jurisdiction|state or federal courts?",
    re.I,
)

GOVERNING = re.compile(r"(?:govern\w*|construed|interpreted)", re.I)
LAW = re.compile(r"\blaws?\b", re.I)

PAYMENT_TERM = re.compile(r"royalt\w*|commission|revenue|profit|margin|\bfees?\b", re.I)
PERCENT_TOKEN = re.compile(r"\d+(?:\.\d+)?\s*%|\bpercent\b|\bpercentage\b", re.I)
CURRENCY_TOKEN = re.compile(r"\$\s?[\d,]+|\bdollars?\b", re.I)

REVENUE_TERM = re.compile(r"revenue|profit|\bsales\b|margin|gross receipts|net receipts", re.I)
PER_UNIT = re.compile(
    r"per unit|per each|for each\b[^.;]{0,60}\bsold\b|based on the number of|"
    r"per copy|per subscriber|per item",
    re.I,
)
EQUITY = re.compile(r"\bshares?\b|\bwarrants?\b|equity interest|\bstock\b", re.I)

ADMINISTRATION = re.compile(
    r"\breports?\b|statement of account|within\s+\w+\s+days? (?:of|after) the end of|"
    r"\baudit\b|\bobject(?:s|ion|ed)?\b|\bdisput(?:e|es|ed)\b",
    re.I,
)
ADMINISTRATION_NARROW = re.compile(
    r"\breports?\b|statement of account|\baudit\b",
    re.I,
)

ROYALTY_TERM = re.compile(r"revenue|profit|royalt\w*", re.I)

EXECUTION_WORDING = re.compile(r"\bdated\b|\bas of\b|\bentered into\b|\bmade this\b", re.I)
EXECUTION_CUE = re.compile(
    r"\bmade\b|\bentered into\b|\bexecuted\b|\bdated\b|\bday of\b", re.I
)

DATE_LITERAL = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+\d{1,2},\s*\d{4}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b"
)

DATE_LONG = re.compile(
    r"\d{1,2}(?:st|nd|rd|th)?\s+day\s+of\s+\w+,?\s+\d{4}|"
    r"[A-Z][a-z]+\s+\d{1,2},\s*\d{4}"
)

MONTH = (
    r"(?:January|February|March|April|May|June|July|August|September|October|"
    r"November|December)"
)

BLANK = r"(?:_{2,}|\*{2,}|\[\s*\]|\[\*+\]|-{3,})"

DATE_BLANK_PATTERNS = [
    re.compile(r"this\s+" + BLANK + r"\s*(?:day)?\s*of\s+\w+", re.I),
    re.compile(r"\bday\s+of\s+" + BLANK, re.I),
    re.compile(BLANK + r"\s*,?\s*(?:19|20)\d\d\b"),
    re.compile(r"\b(?:19|20)\d\d\b\s*" + BLANK),
    re.compile(MONTH + r"\s+" + BLANK + r",?\s*(?:19|20)\d\d", re.I),
    re.compile(MONTH + r"\s+\d{1,2},?\s*" + BLANK, re.I),
    re.compile(r"\bday\s+of\s+" + MONTH + r"\s*,?\s*" + BLANK, re.I),
]

BARE_DATE_SLOT = re.compile(r"^\s*Dated?\s*:\s*$", re.I | re.M)

FURNITURE = re.compile(
    r"omitted portions of this exhibit|request for confidential treatment|"
    r"^\s*Source:\s.+,\s\d{1,2}/\d{1,2}/\d{4}|^\s*Page \d+",
    re.I | re.M,
)

FURNITURE_WIDE = re.compile(
    r"omitted portions of this exhibit|request for confidential treatment|"
    r"confidential treatment (?:has been )?requested|"
    r"portions of this (?:page|exhibit) have been omitted|"
    r"^\s*Source:\s.+,\s\d{1,2}/\d{1,2}/\d{4}|^\s*Page \d+(?:\s+of\s+\d+)?\s*$|"
    r"^\s*\d{1,3}\s*$",
    re.I | re.M,
)

QUANTITY_TOKEN = re.compile(r"\d|\*{3,}|\[\*+\]")

LOWER_CUE = re.compile(
    r"\bminimum\b|\bat least\b|\bno less than\b|\bnot less than\b|\bwithin\b.{0,40}%", re.I
)
UPPER_CUE = re.compile(
    r"\bmaximum\b|\bup to\b|\bin excess of\b|\bexceed(?:ing|s)?\b|"
    r"\bnot required to\b.{0,40}\bmore than\b|\bno more than\b",
    re.I,
)

FLOOR_CUE = re.compile(r"\bminimum\b|\bat least\b|\bno less than\b", re.I)
FLOOR_CUE_WIDE = re.compile(
    r"\bminimum\b|\bat least\b|\bno less than\b|\bnot less than\b|\bno fewer than\b|"
    r"\bguarantee(?:d|s)?\b|\bfloor\b",
    re.I,
)

NON_PURCHASE_VERB = re.compile(
    r"\b(?:supply|supplies|deliver|delivers|provide|provides|share|shares|"
    r"allocate|allocates|make available|makes available)\b",
    re.I,
)

NON_PURCHASE_VERB_WIDE = re.compile(
    r"\b(?:supply|supplies|deliver|delivers|provide|provides|share|shares|"
    r"allocate|allocates|make available|makes available|"
    r"spend|spends|pay|pays|maintain|maintains|deploy|deploys|employ|employs|"
    r"produce|produces|perform|performs|conduct|conducts|use|uses|devote|devotes|"
    r"sell|sells|generate|generates|achieve|achieves|have access to|access)\b",
    re.I,
)

PURCHASE_VERB = re.compile(r"\b(?:buy|buys|purchase|purchases|order|orders)\b", re.I)

HAS_SHARE = re.compile(r"(?:\d+(?:\.\d+)?\s*%|\bpercent\b)", re.I)
HAS_FLOOR_TOKENS = re.compile(
    r"\bminimum\b|\bat least\b|\bno less than\b|\bguarantee\w*\b|\$\s?[\d,]+", re.I
)

UNDERTAKING_CUE = re.compile(
    r"\bcommits to\b|\bagrees that\b|\bagrees to\b|\bundertakes\b|"
    r"\bshall use\b.{0,40}\befforts\b",
    re.I,
)
