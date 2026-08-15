import re

CEILING_CUE = re.compile(
    r"\bexceed(?:s|ing)?\b|in excess of|\bno more than\b|\bmaximum\b", re.I
)

CEILING_CUE_NARROW = re.compile(r"\bexceed(?:s|ing)?\b|in excess of", re.I)

CEILING_CUE_WIDE = re.compile(
    r"\bexceed(?:s|ing)?\b|in excess of|\bno more than\b|\bmaximum\b|"
    r"\bup to\b|\bcap(?:ped|s)?\b|\bceiling\b|\bnot to exceed\b|\blimit(?:ed|s)? to\b",
    re.I,
)

CONSEQUENCE_CUE = re.compile(
    r"\bfees?\b|\bprices?\b|\bcharges?\b|\brates?\b|\bconsent\b|\bapprovals?\b", re.I
)

DERIVATIVE_CUE = re.compile(
    r"\bamendment\b|\bamend(?:ed|ing|s)?\b|\baddendum\b|amended and restated", re.I
)

DERIVATIVE_CUE_STRICT = re.compile(
    r"\bamendment\b|\baddendum\b|amended and restated", re.I
)

CONFLICTS_TAIL = re.compile(
    r"without regard to (?:the )?(?:conflicts?|choice) of laws?|"
    r"without regard to (?:the )?(?:conflicts?|choice)[- ]of[- ]laws?|"
    r"excluding its conflicts? of laws?|"
    r"without (?:giving|regard to the giving of) effect to (?:any )?"
    r"(?:conflicts?|choice) of laws?",
    re.I,
)

CONFLICTS_TAIL_WIDE = re.compile(
    r"without regard to[^.;]{0,80}(?:conflicts?|choice)[- ]of[- ]?laws?|"
    r"excluding[^.;]{0,40}conflicts?[- ]of[- ]?laws?|"
    r"without giving effect to[^.;]{0,80}(?:conflicts?|choice)[- ]of[- ]?laws?|"
    r"\bnotwithstanding[^.;]{0,40}conflicts?[- ]of[- ]?laws?",
    re.I,
)

GOVERNING_CUE = re.compile(
    r"(?:govern\w*|construed|interpreted|enforced)[^.;]{0,80}\blaws?\b|"
    r"\blaws?\b[^.;]{0,80}(?:govern\w*|construed|interpreted)",
    re.I,
)

EXECUTION_BLOCK = re.compile(
    r"IN WITNESS WHEREOF|"
    r"ha(?:s|ve) caused this (?:Agreement|Amendment|Contract)[^.;]{0,80}to be executed|"
    r"ha(?:s|ve) executed this (?:Agreement|Amendment|Contract)|"
    r"^\s*By:\s*_{3,}",
    re.I | re.M,
)

EXECUTION_BLOCK_NARROW = re.compile(r"IN WITNESS WHEREOF", re.I)

ATTACHMENT_HEADING = re.compile(
    r"^[ \t]*(?:EXHIBIT|SCHEDULE|ANNEX|APPENDIX|ATTACHMENT)[ \t]+[A-Z0-9][-A-Z0-9.]*\b",
    re.M,
)

ATTACHMENT_HEADING_STRICT = re.compile(
    r"^[ \t]*(?:EXHIBIT|SCHEDULE|ANNEX|APPENDIX)[ \t]+[A-Z0-9][-A-Z0-9.]*[ \t]*$",
    re.M,
)

SINGLE_VALUE_CATEGORIES = ("Agreement Date", "Governing Law", "Expiration Date")
