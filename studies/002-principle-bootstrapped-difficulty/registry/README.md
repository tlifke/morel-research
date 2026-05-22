# Principle registry

Append-only log of `AuditablePrinciple` instances. The schema is defined
by `../models.py`; this directory holds the data.

## Files

- `principles.jsonl` — append-only log. Each line is one
  `AuditablePrinciple` serialized to JSON. New versions of an existing
  principle are *new rows* with new uuids; the `provenance.parent_uuid`
  links the lineage. Never edit prior rows in place — that would break
  reproducibility of experiment configs that cite the old uuid.

## Slug conventions

- `DIF#####` — difficulty principles (predict that a task is hard for
  the target model in some way).
- `CAL#####` — calibration principles (guide when to call a tool given a
  recognized difficulty).
- `SCO#####` — scope / refusal principles (when to abstain entirely).
- Add new prefixes as new categories arise; document here.

Zero-padded to five digits to leave room.

## Lifecycle

A principle moves through states (see `PrincipleStatus` in `models.py`):

```
proposed -> under_test -> { validated | regressed | retired }
```

Transitions are decided in experiment summaries, not by editing the
registry directly. The current state of each principle is the latest row
with that uuid lineage.
