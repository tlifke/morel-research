# Backlog — deliberately deferred infrastructure

Items we decided not to build yet, with why and the trigger to revisit.
This file is itself the stopgap for item 2: agent memory (including
non-Anthropic and weaker models) is not a durable store, so deferred ideas
live here in the repo where any agent can read them.

1. **Second-pass reviewer agent** — an AI pass that checks decompositions
   against resources, goals, and standing principles before human review.
   *Deferred because:* study 005 inv 002 showed a Critic doesn't reliably
   beat improving the core agent's specification; Tyler + the interactive
   frontier agent currently fill this role. *Revisit when:* gate reviews
   become the human bottleneck, or drafting contracts stabilize enough
   that compliance checking is mechanical. *Refinement (2026-07-27):*
   its job is flagging judgment calls (e.g. round-3 006's budget-driven
   meta-agent choice), not enforcing them via drafting prompts —
   overtuning the drafter is wasted effort. Fuel: the principles corpus
   from item 6.

2. **Idea backlog inside the ticketing system** — a first-class backlog
   (ideas → draft tickets) with the same progressive-disclosure render as
   tickets. *Deferred because:* v0 scope. *Revisit when:* ideas start
   getting lost, or a second investigation adopts the ticket system.

3. **Resource-elicitation Skill** — collecting resources/constraints
   inherently requires human interaction; today it happens
   conversationally and lands in `resources.md`. Encode the elicitation
   as a Skill (interview script + file update) so any agent can run it,
   and later embed it in the platform. *Revisit when:* resources.md goes
   stale or a non-interactive agent needs to refresh it.

4. **Progressive-disclosure + reviewer-toggle conventions into the
   platform frontend** — dropdown detail per ticket and a
   default-off reviewer layer, both validated in the round-2/3 review
   pages. *Revisit when:* the morel-primordia frontend starts.

5. **Human-needed wrongness feedback** — a mechanism for Tyler to mark a
   ticket's `human_needed` declaration (or assignee hypothesis) as wrong,
   captured as structured signals for future delegation modeling.
   *Revisit when:* tickets begin executing and provenance records exist
   to attach the signal to.

6. **Approve/reject principles corpus** — every gate decision and
   review-flag resolution records what was chosen and why (first entry:
   round-3 006 meta-agent — reviewer note initially called it a failure;
   Tyler reclassified it as a legitimate choice misaligned with the
   replication, review-layer territory). Over time the corpus trains a
   classifier or prompts an LLM reviewer, and doubles as documentation of
   our choices. *Revisit when:* ~10+ recorded decisions exist.
