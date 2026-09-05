# API (as built)

Base URL: `http://localhost:8300`. Interactive docs: `/docs` (OpenAPI).
All request/response bodies are JSON, validated by the Pydantic schemas in
`schemas.py`.

## Import

| Method | Path | Notes |
|---|---|---|
| POST | `/api/import` | Rescan `data/runs/**`. Upserts runs (keyed by run-id dir), seeds the 5 study-010 questions. Returns `ImportResult` `{runs_found, runs_upserted, runs_skipped[], questions_seeded[]}`. |

## Runs

| Method | Path | Notes |
|---|---|---|
| GET | `/api/runs?condition=&model=&tag=` | All filters optional (model is substring match). Returns `RunOut[]`. |
| GET | `/api/runs/{id}` | Single `RunOut`. 404 if unknown. |
| GET | `/api/runs/{id}/trace` | Parsed session JSONL: `{header, custom, events[]}`; events are chronological `{kind:"message", role, index, blocks[]}`. 404 if session file missing. |

## Workspace files

| Method | Path | Notes |
|---|---|---|
| GET | `/api/runs/{id}/files` | Workspace tree; `contract_text/` collapsed to `{type:"collapsed_dir", count}`. |
| GET | `/api/runs/{id}/files/content?path=` | File text. **403** on any path resolving outside the workspace (`../`, absolute). **413** > 2MB. |
| GET | `/api/runs/{id}/preview-file?path=` | Images/HTML for the preview tab. HTML served with CSP `default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; font-src data:`. No size cap (agent apps may inline the dataset). |

## Questions (rubric as data)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/questions` | All, ordered. |
| POST | `/api/questions` | Create. 409 on duplicate `code`. |
| PATCH | `/api/questions/{id}` | Partial update (text/description/answered_by/value_type/active/sort_order). |

## Answers

| Method | Path | Notes |
|---|---|---|
| GET | `/api/runs/{id}/answers` | All answers for a run, both judges. |
| POST | `/api/runs/{id}/answers` | Upsert one answer `(run, question, judge)`. Errors: 403 agent answering `answered_by:"human"` question; 409 inactive question; 422 invalid value for `value_type`; 404 unknown run/question. |

Request body: `{question_id, judge: "agent"|"human", value, evidence?, judge_model?, notes?}`.

## Comparisons

| Method | Path | Notes |
|---|---|---|
| GET | `/api/comparisons` | Newest first. |
| POST | `/api/comparisons` | `{run_a_id, run_b_id, better: "a"|"b"|"tie", dimensions?, notes?}`. 422 if run_a == run_b; 404 unknown runs. |

## Written feedback

| Method | Path | Notes |
|---|---|---|
| GET | `/api/feedback?run_id=` | Newest first; optional run filter. |
| POST | `/api/feedback` | `{run_id?, anchor_type: "run"|"file"|"tool_call", anchor_ref?, text}`. |

## Agent judge trigger

| Method | Path | Notes |
|---|---|---|
| POST | `/api/runs/{id}/judge` | Spawns `agent_judge.py <run_id>` as a background subprocess (pid file + `judge.log` in the run dir). Returns immediately `{ok, message, pid}`. |
| GET | `/api/runs/{id}/judge/status` | `{running, done, ok, log_tail}` from pid + `judge.done` marker. |

## Exports (SPEC 7 shapes)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/export/sft?run_ids=a,b,c` | `{format:"sft", renderer:"tml_v0", effort:0.9, examples:[{run_id, messages}]}` — messages are the full chronological trace (user/assistant/toolResult). 400 if no run_ids. |
| GET | `/api/export/dpo` | One entry per comparison with `better != "tie"`: `{run_a, run_b, better, prompt:[user events], chosen:[assistant events], rejected:[assistant events]}`. |
| GET | `/api/export/reward` | Human-answered runs: `{run_id, answers:{code:value}, score, trace_ref}`. Score placeholder = mean over human-answered questions (bool→0/1, int_1_5→x/5, text excluded); formula documented in code. |
| GET | `/api/export/summary` | Judgment state across all runs (per-run agent/human answered question-id sets, comparison/feedback flags). |

## Misc

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | `{status:"ok"}` after a DB round-trip. |
