# Data Model (as built)

Source of truth: `models.py`. Schema created via `Base.metadata.create_all`
(no Alembic migrations in this MVP).

## Mermaid erDiagram (as actually built)

```mermaid
erDiagram
    RUNS ||--o{ ANSWERS : "judged by"
    QUESTIONS ||--o{ ANSWERS : "answered in"
    RUNS ||--o{ COMPARISONS : "run_a or run_b"
    RUNS ||--o{ WRITTEN_FEEDBACK : "critiqued in"
    RUNS ||--o{ LAUNCH_EVENTS : "launched as"

    RUNS {
        string id PK "run dir name"
        string study
        string condition
        string model
        string spec "nullable"
        string tag "nullable"
        string run_dir
        string workspace_dir
        string session_file "nullable"
        int tokens_input
        int tokens_output
        int tokens_reasoning
        int tokens_cache_read
        int tokens_cache_write
        float estimated_cost_usd "nullable"
        string pricing_source "nullable"
        bool audit_clean
        jsonb audit_violations "nullable"
        datetime imported_at
    }
    QUESTIONS {
        int id PK
        string code UK
        string text
        string description "nullable"
        string answered_by "agent|human|both"
        string value_type "bool|int_1_5|text"
        bool active
        int sort_order
        datetime created_at
    }
    ANSWERS {
        int id PK
        string run_id FK
        int question_id FK
        string judge "agent|human"
        jsonb value "bool|int|string per value_type"
        text evidence "nullable"
        string judge_model "nullable, agent rows"
        text notes "nullable"
        datetime created_at
    }
    LAUNCH_EVENTS {
        int id PK
        string run_id FK
        text command
        int port "nullable"
        string mode "http|desktop|static"
        datetime started_at
        bool healthy "null = still starting"
        text log_excerpt "nullable"
    }
    COMPARISONS {
        int id PK
        string run_a_id FK
        string run_b_id FK
        string better "a|b|tie"
        jsonb dimensions "nullable"
        text notes "nullable"
        datetime created_at
    }
    WRITTEN_FEEDBACK {
        int id PK
        string run_id FK "nullable"
        string anchor_type "run|file|tool_call"
        jsonb anchor_ref "nullable"
        text text
        datetime created_at
    }
```

## Constraints

- `answers`: UNIQUE `(run_id, question_id, judge)` — one answer per
  judge per question per run. POSTs upsert within a judge.
- `questions.code`: UNIQUE.
- `comparisons`: application-level check that `run_a_id != run_b_id`
  (Pydantic validator; not a DB constraint).
- **answered_by enforcement** (application-level, in `api.py`): an answer
  with `judge="agent"` is rejected with HTTP 403 when the question's
  `answered_by == "human"`. Human rows may answer any active question.
- **value validation** (application-level, `_validated_value`):
  `bool` → must be JSON bool; `int_1_5` → int in [1..5] (bools rejected);
  `text` → coerced to string. Violations → HTTP 422.
- Inactive questions reject new answers (HTTP 409).

## Generalist notes

- Rubric questions are rows, not schema. New studies/tasks add question
  rows (UI: /questions) without migrations.
- `runs.condition`, `runs.tag` are free-text labels; nothing in the schema
  is study-010-specific except the seed data (imported idempotently) and
  the `runs.study` default.


## launch_events (SPEC 9 addendum)

One row per live-app launch attempt (written at launch; `healthy` resolved
when the launcher's health probe settles — null while starting).

| column | type | notes |
|---|---|---|
| id | int PK | |
| run_id | FK runs | |
| command | text | resolved or overridden launch command |
| port | int nullable | allocated port (8450+); may differ from the app's hardcoded port |
| mode | text | `http` (URL probe) \| `desktop` (process-alive, GUI on host) \| `static` (http.server) |
| started_at | timestamptz | |
| healthy | bool nullable | null = pending resolution |
| log_excerpt | text nullable | last ~40 lines of the app's output |

Health resolution requires the launched process to still be alive when a
URL probe succeeds (guards against unrelated servers squatting on
README-declared ports).
