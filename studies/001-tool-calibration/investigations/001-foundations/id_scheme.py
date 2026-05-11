"""ID scheme for prompt records in the tool-calibration corpus.

Format:
    {tool}_{domain}_{difficulty}_{disambiguator}_{NNN}_{shortuuid}
    \________________ pair_id _________________/ \_ instance _/

- All slug segments are lowercase alphanumeric (and underscores).
- `NNN` is a zero-padded three-digit counter within the
  `tool/domain/difficulty/disambiguator` bucket.
- `shortuuid` is the first 8 hex chars of a uuid4. It is the only
  part that distinguishes the two halves of a matched pair; the
  rest is shared between them.

`pair_id` = everything up to and including the `NNN` counter.
`id`      = `pair_id` + `_` + `shortuuid`.

Examples:
    calc_arith_hard_3digit_001_a7f3b2c4
    knowledge_facts_easy_capital_002_e2c8f1a9
    datetime_relative_medium_workday_003_b4d7c2e6
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

# Segment that may appear in a slug field.
_SLUG_SEGMENT = r"[a-z0-9]+(?:_[a-z0-9]+)*"

PAIR_ID_REGEX = re.compile(rf"^{_SLUG_SEGMENT}_[0-9]{{3}}$")
PROMPT_ID_REGEX = re.compile(rf"^{_SLUG_SEGMENT}_[0-9]{{3}}_[0-9a-f]{{8}}$")
_KEBAB_REGEX = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")

VALID_DIFFICULTIES = ("trivial", "easy", "medium", "hard", "extreme")


@dataclass(frozen=True)
class PromptIdParts:
    """Parsed view of a prompt id."""

    tool: str
    domain: str
    difficulty: str
    disambiguator: str
    counter: int
    shortuuid: str

    @property
    def pair_id(self) -> str:
        return (
            f"{self.tool}_{self.domain}_{self.difficulty}_"
            f"{self.disambiguator}_{self.counter:03d}"
        )

    @property
    def id(self) -> str:
        return f"{self.pair_id}_{self.shortuuid}"


def make_pair_id(
    tool: str,
    domain: str,
    difficulty: str,
    disambiguator: str,
    counter: int,
) -> str:
    """Compose a pair_id from its segments. Validates each segment.

    Raises:
        ValueError: if any segment is not lowercase snake-kebab or
            if `difficulty` is outside the canonical set.
    """
    for name, segment in (
        ("tool", tool),
        ("domain", domain),
        ("difficulty", difficulty),
        ("disambiguator", disambiguator),
    ):
        if not _KEBAB_REGEX.fullmatch(segment):
            raise ValueError(
                f"{name}={segment!r} is not a valid slug segment "
                "(lowercase a-z, 0-9, and _; cannot start or end with _)."
            )
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(
            f"difficulty={difficulty!r} is not in {VALID_DIFFICULTIES}"
        )
    if not 0 <= counter <= 999:
        raise ValueError(f"counter={counter} must fit in three digits")
    return f"{tool}_{domain}_{difficulty}_{disambiguator}_{counter:03d}"


def make_prompt_id(pair_id: str, *, shortuuid: str | None = None) -> str:
    """Build a full prompt id from a pair_id and (optionally) a fixed
    shortuuid. If `shortuuid` is None, a fresh uuid4-derived 8-char
    suffix is generated.

    Raises:
        ValueError: if pair_id doesn't match PAIR_ID_REGEX, or if
            shortuuid is supplied but malformed.
    """
    if not PAIR_ID_REGEX.fullmatch(pair_id):
        raise ValueError(f"pair_id={pair_id!r} does not match PAIR_ID_REGEX")
    if shortuuid is None:
        shortuuid = uuid.uuid4().hex[:8]
    elif not re.fullmatch(r"[0-9a-f]{8}", shortuuid):
        raise ValueError(
            f"shortuuid={shortuuid!r} must be 8 lowercase hex chars"
        )
    return f"{pair_id}_{shortuuid}"


def parse_prompt_id(prompt_id: str) -> PromptIdParts:
    """Inverse of make_prompt_id. Returns structured fields.

    Raises:
        ValueError: if prompt_id doesn't match the full pattern.
    """
    if not PROMPT_ID_REGEX.fullmatch(prompt_id):
        raise ValueError(
            f"prompt_id={prompt_id!r} does not match PROMPT_ID_REGEX"
        )
    pair_id, shortuuid = prompt_id.rsplit("_", 1)
    rest, counter_str = pair_id.rsplit("_", 1)
    tool, domain, difficulty, disambiguator = rest.split("_", 3)
    return PromptIdParts(
        tool=tool,
        domain=domain,
        difficulty=difficulty,
        disambiguator=disambiguator,
        counter=int(counter_str),
        shortuuid=shortuuid,
    )


def is_valid_prompt_id(prompt_id: str) -> bool:
    return bool(PROMPT_ID_REGEX.fullmatch(prompt_id))


def is_valid_pair_id(pair_id: str) -> bool:
    return bool(PAIR_ID_REGEX.fullmatch(pair_id))


if __name__ == "__main__":
    # Smoke test.
    pid = make_pair_id("calc", "arith", "hard", "3digit", 1)
    fid = make_prompt_id(pid, shortuuid="a7f3b2c4")
    parts = parse_prompt_id(fid)
    assert parts.id == fid, parts
    assert parts.pair_id == pid, parts
    assert parts.tool == "calc"
    assert parts.difficulty == "hard"
    assert parts.counter == 1
    print(f"pair_id  = {pid}")
    print(f"id       = {fid}")
    print(f"parsed   = {parts}")
