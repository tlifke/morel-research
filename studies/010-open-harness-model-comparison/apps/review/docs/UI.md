# UI (as built)

Server-rendered Jinja2 + Tailwind CDN + Alpine.js + htmx (no build step).
Screenshots in `apps/review/screenshots/`.

## Layout

Dark slate sidebar (Contract Lab, nav: Runs / Compare / Questions /
Feedback log; export links; OpenAPI docs link) + light main pane.

## Pages

### `/` — Runs index (screenshots/index.png)
Table of all ingested runs: run-id (link), model, condition badge
(clean=emerald, pi=amber), tag, cost, audit status (✅/❌+count), and
per-question answer chips (A=agent answered, H=human answered, per question
in sort order). Filters: none server-side in UI v1 (use API query params);
"Import runs" button (htmx POST /api/import) with inline result line.

### `/runs/{id}` — Run detail (screenshots/run_detail*.png)
Header: condition/model/tag/cost/tokens/audit + "Run agent judge" button
(spawns background judge, live status line, auto-reload when done).
Tabs:
- **Trace**: chronological cards — user (blue), assistant (white, with
  collapsible 💭 thinking, 🔧 tool-call cards with pretty-printed args and
  per-block ⚓ anchor buttons), tool results (indented, error-flagged).
- **Files**: two-pane workspace tree (folders expand; `contract_text/`
  shown as a collapsed count) + code view of the selected file.
- **Preview**: agent-built images inline; HTML in a sandboxed iframe (CSP).
  Python apps are NOT executed here.
- **Judge**: all active questions in sort order. `both` questions show the
  agent answer (collapsible evidence) + agree/disagree radios with an
  override input; `human` questions get direct inputs (yes/no, 1–5 select).
  Notes textarea; "Save human judgment" upserts human answer rows.
- **Feedback**: add written feedback (anchor type + JSON ref + text) and
  the run's existing feedback.

### `/compare` (screenshots/compare.png)
Two run pickers with live summary panes (condition/model/tag/audit/cost/
file list, link to full run) + comparison form (better: A/B/tie, optional
per-dimension JSON, notes). Recorded comparisons listed below.

### `/questions` (screenshots/questions.png)
Rubric-as-data: list with answered_by / value_type / active badges +
create-question form.

### `/feedback` (screenshots/feedback.png)
Three columns: written feedback, comparisons, answers (newest first), with
export links.


## Judge job dashboard (SPEC 10)

- **Runs index**: row checkboxes + "Judge selected (n)" button (creates a
  batch job, redirects to /judging). Judgment matrix below the table: rows =
  runs, columns = active questions; agent answers indigo, human answers
  emerald, disagreement ringed red.
- **/judging dashboard** (sidebar "Judging"): job cards with status badge,
  progress bar, done/failed counts, current run, per-item statuses,
  Pause/Resume/Cancel. Polls /api/judge-jobs every 2.5s; progress updates
  in place, full reload only on a status transition. Display-only — jobs
  run server-side, leaving the page is always safe.
- **Run detail** judge tab links to the dashboard ("batch dashboard →").
