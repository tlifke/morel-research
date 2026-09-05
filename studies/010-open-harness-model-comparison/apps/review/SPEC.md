# SPEC — Contract Lab (Study 010 Review App)

Handoff document for implementation. The reviewing human judges agent runs
(study 010: agents building a contract-visualization app under different
harness conditions); feedback is recorded in a form directly convertible to
post-training datasets (SFT, DPO, reward-model training) via export
endpoints.

**Design intent: generalist.** The app is not hardwired to study 010's five
questions — rubric questions are *data* (seeded rows), runs carry their
conditions as metadata, and comparisons ask "which of these attempts was
better" across any runs. Study 010 is the first tenant, not the schema.

**Owner decisions embedded here are final — escalate ambiguities, don't
redesign.**

## 1. Stack (decided)

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2,
  PostgreSQL. Deps go into the repo's `uv` project (`pyproject.toml`):
  `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `psycopg[binary]`,
  `pydantic`, `jinja2`, `python-multipart`.
- **DB provisioning**: `docker-compose.yml` in the app dir running
  `postgres:16` (named volume, port 5433 to avoid clashes);
  `DATABASE_URL` env (default
  `postgresql+psycopg://contractlab:contractlab@localhost:5433/contractlab`).
  Schema via `Base.metadata.create_all` at startup (no Alembic for MVP —
  note in README).
- **Frontend**: Jinja2 templates + Tailwind CSS (CDN) + Alpine.js (CDN) +
  htmx (CDN). No node build step. Clean, modern look: sidebar nav, cards,
  badges, readable monospace for traces.
- **Location / run**: `studies/010-open-harness-model-comparison/apps/review/`,
  entrypoint `main.py`, `uv run uvicorn main:app --port 8300`.
- **Non-goals**: auth, deployment, principle extraction, training code.
  Export endpoints emit JSON only.

## 2. Source data (read-only; never modify)

`studies/010-open-harness-model-comparison/data/runs/<condition>/<model-slug>/<run-id>/`:

- `run-summary.json` — condition, model, spec, tag, tokens, pricing,
  estimatedCostUsd
- `audit.json` — toolCalls, violations[], clean
- `session-*.jsonl` — pi session, one JSON per line. Types of interest:
  `session` (header), `model_change`, `thinking_level_change`, `message`
  (`message.role` = `user`|`assistant`|`toolResult`; assistant `content[]`
  blocks: `text` | `thinking` | `toolCall` with `name`, `arguments`),
  `custom` (`customType` `pi-clean-experiment`: exact systemPrompt + config)
- `workspace/` — the agent's produced app. `workspace/contract_text/` and
  `workspace/contract_ground_truth` are deterministic dataset copies
  (collapse in UI).
- 9 runs exist today (8 matrix + 1 smoke).

**Import job** scans run dirs into Postgres (idempotent, keyed by run dir
name; re-runnable from UI button or CLI).

## 3. Data model

### 3.1 Tables

**`runs`** — one ingested agent run.
| column | type | notes |
|---|---|---|
| id | str PK | run dir name |
| study | str | source study slug (default `010-open-harness-model-comparison`) |
| condition | str | e.g. `clean` \| `pi` (free text — harness condition label) |
| model | str | e.g. `tinker/thinkingmachines/Inkling-Small` |
| spec | str nullable | task spec path used |
| tag | str nullable | free label (`verify`, `noverify`, `smoke`, …) |
| run_dir / workspace_dir / session_file | str | absolute paths |
| tokens_input/output/reasoning/cache_read/cache_write | int | |
| estimated_cost_usd | float nullable | |
| pricing_source | str nullable | |
| audit_clean | bool | |
| audit_violations | JSONB | |
| imported_at | datetime | |

**`questions`** — rubric definitions are DATA. Each question is applicable
to produced artifacts and is flagged with who answers it.
| column | type | notes |
|---|---|---|
| id | int PK | |
| code | str unique | e.g. `docs_describe_launch` |
| text | str | the question as shown |
| description | text nullable | clarifying detail |
| answered_by | str | `agent` \| `human` \| `both` |
| value_type | str | `bool` \| `int_1_5` \| `text` |
| active | bool | deprecate without deleting |
| sort_order | int | display order |
| created_at | datetime | |

**`answers`** — one row per (run, question, judge).
| column | type | notes |
|---|---|---|
| id | int PK | |
| run_id | FK runs | |
| question_id | FK questions | |
| judge | str | `agent` \| `human` |
| value | JSONB | bool / int / str per `value_type` |
| evidence | text nullable | agent: what it did/observed |
| judge_model | str nullable | agent rows |
| notes | text nullable | |
| created_at | datetime | |
Unique constraint: `(run_id, question_id, judge)`.
`both` semantics: agent answers first; human UI shows the agent answer with
agree (adopt) / disagree (override + own value). The human row is the
ground-truth label; the agent row is advisory. API rules: human rows may
answer any question; agent rows only questions with `answered_by in
(agent, both)` — enforced server-side.

**`comparisons`** — pairwise preference between any two runs.
| column | type | notes |
|---|---|---|
| id | int PK | |
| run_a_id / run_b_id | FK runs | |
| better | str | `a` \| `b` \| `tie` |
| dimensions | JSONB nullable | optional per-dimension calls |
| notes | text | free written feedback |
| created_at | datetime | |

**`written_feedback`** — anchored critiques (storage only; NO principle
extraction in this app).
| column | type | notes |
|---|---|---|
| id | int PK | |
| run_id | FK runs nullable | null = general |
| anchor_type | str | `run` \| `file` \| `tool_call` |
| anchor_ref | JSONB | `{path}` or `{message_index, block_index}` |
| text | text | |
| created_at | datetime | |

### 3.2 Seed questions (study 010 tenant; inserted idempotently by import)

| code | text | answered_by | value_type |
|---|---|---|---|
| `docs_describe_launch` | Does the app's documentation tell us how to launch it? | both | bool |
| `launches_per_docs` | Does the app launch properly in compliance with those instructions? | both | bool |
| `launches_at_all` | Does the app launch in general, regardless of documentation? | both | bool |
| `fulfills_functions` | Does the app fulfill the required functions? | human | bool |
| `fulfills_well` | Does the app fulfill those functions well? | human | int_1_5 |

### 3.3 Relationships (mermaid)

```mermaid
erDiagram
    RUNS ||--o{ ANSWERS : "judged by"
    QUESTIONS ||--o{ ANSWERS : "answered in"
    RUNS ||--o{ COMPARISONS : "run_a or run_b"
    RUNS ||--o{ WRITTEN_FEEDBACK : "critiqued in"

    RUNS {
        string id PK
        string study
        string condition
        string model
        string tag
        string run_dir
        bool audit_clean
    }
    QUESTIONS {
        int id PK
        string code UK
        string answered_by "agent|human|both"
        string value_type "bool|int_1_5|text"
        bool active
    }
    ANSWERS {
        int id PK
        string run_id FK
        int question_id FK
        string judge "agent|human"
        jsonb value
        text evidence
    }
    COMPARISONS {
        int id PK
        string run_a_id FK
        string run_b_id FK
        string better "a|b|tie"
        jsonb dimensions
        text notes
    }
    WRITTEN_FEEDBACK {
        int id PK
        string run_id FK "nullable"
        string anchor_type "run|file|tool_call"
        jsonb anchor_ref
        text text
    }
```

### 3.4 Pydantic models
Mirror every table: `RunOut`, `QuestionCreate/Out`, `AnswerCreate/Out`,
`ComparisonCreate/Out`, `WrittenFeedbackCreate/Out`, `ExportSFT`,
`ExportDPO`, `ExportRewardScore`. API request/response validation uses
these; never return raw dicts.

## 4. API endpoints

```
POST /api/import                          # rescan data/runs/**, upsert runs + seed questions
GET  /api/runs?condition=&model=&tag=     # list w/ judgment status counts
GET  /api/runs/{id}                       # summary + audit + per-question answer status
GET  /api/runs/{id}/trace                 # parsed session jsonl
GET  /api/runs/{id}/files                 # workspace tree (contract_text collapsed)
GET  /api/runs/{id}/files/content?path=   # file content; 404 outside workspace
GET  /api/questions                       # list (incl. inactive)
POST /api/questions                       # create (code unique)
PATCH /api/questions/{id}                 # edit text/description/active/sort_order
GET  /api/runs/{id}/answers               # all answers for run
POST /api/runs/{id}/answers               # upsert one answer (judge from body; server enforces answered_by rules)
GET  /api/comparisons ; POST /api/comparisons
GET  /api/feedback?run_id= ; POST /api/feedback
GET  /api/export/sft?run_ids=a,b,c        # §7; explicit selection
GET  /api/export/dpo                      # comparisons -> pairs (ties excluded)
GET  /api/export/reward                   # human answers -> per-run score (formula in code, documented)
GET  /api/export/summary                  # judgment state across runs
```

## 5. Agent judge (module `agent_judge.py`) — CONFIRMED design

Answers every active question with `answered_by in (agent, both)` for a
given run, by actually exercising the artifact.

- Copy run workspace to a fresh temp dir (originals untouched).
- Run a pi session via SDK under the **pi-clean harness** (minimal system
  prompt, no project context/skills/extensions), cwd = temp dir, model
  configurable (default `tinker/thinkingmachines/Inkling-Small`), thinking
  high.
- Judge prompt (fixed, in-code): instructs the agent to read the docs in
  the directory, answer each provided question by actually trying
  (launch the app per docs; if that fails, try other means), run every
  command it claims, and end its final message with a JSON object mapping
  question codes to `{value, evidence}`. Parse robustly (extract last JSON
  block).
- POST one `answers` row per question (judge=`agent`, evidence, judge_model)
  to the API.
- Trigger: CLI `uv run python agent_judge.py <run_id>` + UI button
  (shells out, shows status/spinner; runs take minutes).
- Path audit on the judge session (same logic as training runs); violations
  appended to evidence. Residual-risk note in README.

## 6. UI (pages + key elements)

1. **Runs index** `/` — table (model badge, condition, tag, cost, tokens,
   audit status, per-question answer chips: agent ✓ / human ✓ / –).
   Filters: condition, model, tag. "Import runs" button.
2. **Run detail** `/runs/{id}` — tabs:
   - **Trace**: chronological; assistant text, collapsible thinking,
     tool-call cards (name/args/result), "anchor" button per block →
     written-feedback form pre-anchored.
   - **Files**: workspace tree; code-highlighted viewer; `contract_text/`
     collapsed with count.
   - **App preview**: images rendered inline; HTML via sandboxed iframe
     route (CSP header; never execute python).
   - **Judge**: questions listed in sort order; `both` questions show the
     agent answer + agree/disagree (override input); `human` questions get
     direct inputs (bool toggle / 1–5 selector / text); evidence collapsible
     per agent answer; notes; Save (upserts human rows).
   - **Feedback**: list + add anchored/run-level written feedback.
3. **Compare** `/compare` — pick any two runs (dropdowns with suggested
   pairs: same model different condition; same condition different model),
   side-by-side panes (trace summary / files / preview), comparison form
   (better a/b/tie, optional dimensions, notes). Intent: present what was
   done under different conditions and ask for a preference.
4. **Questions** `/questions` — list with answered_by badges, active
   toggle, create/edit form (keeps the rubric as data, visible).
5. **Feedback log** `/feedback` — all answers, comparisons, written
   feedback, newest first, export links.

## 7. Export shapes (educational; no training code)

- `/api/export/sft?run_ids=a,b,c` →
  `{"format":"sft","renderer":"tml_v0","effort":0.9,"examples":[{"run_id":...,
  "messages":[exact trace message list incl. toolResults]}]}` — selection is
  explicit (human picks the approved runs from the UI).
- `/api/export/dpo` → from comparisons, ties excluded:
  `[{"run_a":...,"run_b":...,"better":...,"prompt":[system,user msgs],
    "chosen":[assistant turns of winner],"rejected":[assistant turns of loser]}]`
- `/api/export/reward` → human answers per run:
  `[{"run_id":...,"answers":{code:value,...},"score":<documented placeholder:
   mean of bool questions as 0/1 and int_1_5 as x/5 over answered human
   questions>,"trace_ref":session path}]`
- JSON projections only; Tinker `Datum` conversion happens outside the app.

## 8. Deliverables & acceptance criteria

Docs (the agent MUST produce these; they are the record used to compare
reality to this plan):

- `docs/DATA_MODEL.md` — tables, columns, constraints, **mermaid erDiagram**
  as actually built
- `docs/API.md` — every route as actually built (method, path, request/response)
- `docs/UI.md` — pages/elements as actually built
- `docs/AS_BUILT.md` — **deviations from SPEC.md** (anything changed,
  skipped, or discovered), explicitly listed

Acceptance:

1. `docker compose up -d && uv run uvicorn main:app --port 8300` serves the
   app; import ingests all 9 runs and seeds the 5 questions.
2. Run detail renders a real trace (tool calls + thinking) from a real
   session file (test against the smoke run).
3. Full judgment round-trip: agent_judge.py produces agent answers for one
   run; human UI pre-fills `both` questions; human rows save; visible in
   feedback log; exports return valid shapes.
4. Comparison round-trip works end to end.
5. `answered_by` enforcement: agent rows rejected for `human`-only
   questions (API test).
6. Path traversal on `/files/content` impossible (test `../`, absolute paths).
7. Screenshots of every page (playwright or similar) in
   `apps/review/screenshots/`.
8. Do not `git commit` — leave the working tree for owner review.

---

## 9. ADDENDUM — Live app launcher (owner request, post-review)

**Goal**: eliminate the asymmetry between static-artifact runs and full-app
runs. Every run's Preview tab converges to: Launch → components go green →
Open app.

### Behavior
- Preview tab shows a **Launch panel** for every run:
  - Detected components (workspace scan): `frontend` (index.html/static
    files), `backend` (server scripts, requirements.txt, package.json),
    `database` (*.db, *.sql, migrations). Chips with per-component state.
  - **Launch command** (auto-resolved, editable text field before launch):
    1. launch command extracted from the run's README/docs (prefer fenced
       code blocks containing `python`/`uv run`/`npm`/`bash`), else
    2. `run.sh` → `bash run.sh`, else `app.py`/`server.py`/`main.py` →
       `python <file>`, else
    3. static-only → `python -m http.server <port>` (uniform experience).
  - **Launch button** → copies workspace to a fresh temp dir, injects
    `PORT=<free port from 8450+>` env, starts subprocess from the temp dir.
  - **Health monitoring**: subprocess alive + HTTP probe
    (`http://localhost:<port>/`) every 1s up to 60s. States: `starting` →
    `healthy` (green) / `failed` (log tail shown). Log tail (last ~40 lines)
    always visible in the panel.
  - When healthy: **Open app ↗** link (`http://localhost:<port>`,
    target=_blank) + **Stop** button.
- Static runs: the same panel works (http.server), so 1:1 comparison holds.

### Backend
- New module `app_launcher.py`: in-process launch manager (dict keyed by
  run_id; subprocess + polling thread; free-port allocation; temp-copy
  creation). One launch per run at a time; Stop kills process + cleans up.
- `launch_events` table (SQLAlchemy + Pydantic mirror):
  id, run_id FK, command, port, started_at, healthy bool, log_excerpt text.
  Written on start and on health resolution. Feeds q2/q3 evidence later.
- API:
  - `POST /api/runs/{id}/launch` body `{command?: str}` → starts; returns event id
  - `GET /api/runs/{id}/launch/status` → `{running, healthy|failed|null, port, url, log_tail, components, command}`
  - `POST /api/runs/{id}/launch/stop`
- Preview tab UI: launch panel above the static preview; panel visible for
  all runs.

### Safety (document in README + AS_BUILT)
Launching runs agent-written code on the host from a temp copy — same trust
level as the agent judge; no sandbox. Original workspace artifacts are
never executed or modified.
