r"""ID scheme for prompt records in the tool-calibration corpus.

Format:
    {tool}-{domain}-{difficulty}-{disambiguator}-{NNN}-{shortuuid}
    \________________ pair_id _________________/ \_ instance _/

- Field separator is `-`; within-field separator is `_`. This lets a
  field value contain underscores (e.g. tool=`general_knowledge_lookup`,
  disambiguator=`arsenal_v_city`) without ambiguous parsing.
- All field values are lowercase alphanumeric with optional internal
  underscores.
- `NNN` is a zero-padded three-digit counter within the
  `tool/domain/difficulty/disambiguator` bucket.
- `shortuuid` is the first 8 hex chars of a uuid4. It is the only
  part that distinguishes the two halves of a matched pair; the
  rest is shared between them.

`pair_id` = everything up to and including the `NNN` counter.
`id`      = `pair_id` + `-` + `shortuuid`.

Examples:
    calculator-math-hard-3digit-001-a7f3b2c4
    general_knowledge_lookup-sports-medium-arsenal_v_city-001-e2c8f1a9
    none-general-easy-smalltalk-002-b4d7c2e6
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

# Field value: lowercase alphanumeric with optional internal underscores.
_FIELD = r"[a-z0-9]+(?:_[a-z0-9]+)*"

PAIR_ID_REGEX = re.compile(
    rf"^{_FIELD}-{_FIELD}-{_FIELD}-{_FIELD}-[0-9]{{3}}$"
)
PROMPT_ID_REGEX = re.compile(
    rf"^{_FIELD}-{_FIELD}-{_FIELD}-{_FIELD}-[0-9]{{3}}-[0-9a-f]{{8}}$"
)
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
            f"{self.tool}-{self.domain}-{self.difficulty}-"
            f"{self.disambiguator}-{self.counter:03d}"
        )

    @property
    def id(self) -> str:
        return f"{self.pair_id}-{self.shortuuid}"


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
    return f"{tool}-{domain}-{difficulty}-{disambiguator}-{counter:03d}"


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
    return f"{pair_id}-{shortuuid}"


def parse_prompt_id(prompt_id: str) -> PromptIdParts:
    """Inverse of make_prompt_id. Returns structured fields.

    Raises:
        ValueError: if prompt_id doesn't match the full pattern.
    """
    if not PROMPT_ID_REGEX.fullmatch(prompt_id):
        raise ValueError(
            f"prompt_id={prompt_id!r} does not match PROMPT_ID_REGEX"
        )
    pair_id, shortuuid = prompt_id.rsplit("-", 1)
    rest, counter_str = pair_id.rsplit("-", 1)
    tool, domain, difficulty, disambiguator = rest.split("-", 3)
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
    pid = make_pair_id("calculator", "math", "hard", "3digit", 1)
    fid = make_prompt_id(pid, shortuuid="a7f3b2c4")
    parts = parse_prompt_id(fid)
    assert parts.id == fid, parts
    assert parts.pair_id == pid, parts
    assert parts.tool == "calculator"
    assert parts.difficulty == "hard"
    assert parts.counter == 1

    # Long-tool-name and control-prompt round-trip checks.
    for tool, dom, diff, disamb in [
        ("general_knowledge_lookup", "sports", "medium", "arsenal_v_city"),
        ("user_knowledge_lookup", "personal", "easy", "wedding_anniversary"),
        ("none", "general", "easy", "smalltalk"),
    ]:
        pp = make_pair_id(tool, dom, diff, disamb, 1)
        assert is_valid_pair_id(pp), pp
        ff = make_prompt_id(pp, shortuuid="0123abcd")
        parsed = parse_prompt_id(ff)
        assert parsed.tool == tool, parsed
        assert parsed.domain == dom, parsed
        assert parsed.difficulty == diff, parsed
        assert parsed.disambiguator == disamb, parsed
        print(f"round-trip ok: {ff}")
    print(f"pair_id  = {pid}")
    print(f"id       = {fid}")
    print(f"parsed   = {parts}")
