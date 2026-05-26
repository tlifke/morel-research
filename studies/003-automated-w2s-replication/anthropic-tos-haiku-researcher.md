---
title: Anthropic ToS check — Claude Haiku 4.5 as researcher agent
study: studies/003-automated-w2s-replication
created: 2026-05-25
updated: 2026-05-25
---

# Anthropic ToS / AUP check: Haiku 4.5 as W2S researcher agent

## 1. Top-line verdict

**Yellow.** The use case is compatible with the Usage Policy and Commercial
Terms *provided* (a) we are not training a model that "competes" with Claude
and (b) the model-distillation clause is read narrowly to exclude using
Claude as an orchestrator that drives training of an unrelated, smaller
open-source model. The one clause that could plausibly bite — "Utilization
of inputs and outputs to train an AI model … without prior authorization"
— is broad enough that a sustained run warrants a quick written
confirmation from Anthropic before publication, even though the spirit of
the rule is plainly aimed at Claude-clone distillation, not at using Claude
to design Qwen experiments.

## 2. Per-concern verdicts

### (a) Agentic / automated use

**Green.** The Usage Policy (effective 2025-09-15) does not prohibit
agentic loops, code execution, or shell access. It only forbids
"Intentionally bypass[ing] capabilities, restrictions, or guardrails
established within our products" and coordinating malicious activity across
accounts. Anthropic ships the Claude Agent SDK explicitly for this pattern.
Commercial Terms (effective 2025-06-17) likewise impose no agentic-use
carve-out.

### (b) Model-training restrictions

**Yellow, leaning green.** The AUP forbids "Utilization of inputs and
outputs to train an AI model (e.g., 'model scraping' or 'model
distillation') without prior authorization from Anthropic." Commercial
Terms §D.4 separately forbids using the Services "to build a competing
product or service, including to train competing AI models."

Reading these together: the *competing-model* clause is about Claude
substitutes, which a Qwen-0.5B→Qwen-4B W2S pseudo-label loop is not. The
*scraping/distillation* clause is broader and on its face could be read to
cover *any* use of Claude outputs in a training pipeline. In practice it
targets distillation of Claude itself, and Anthropic's own February 2026
public statements distinguish legitimate self-distillation and downstream
research from "illicit" Claude-cloning. Our setup uses Claude as a
*driver/orchestrator* — its outputs are code and experimental plans, not
training labels for the student. The student's labels come from Qwen-0.5B.
Still, "without prior authorization" is the operative phrase; if any Claude
text ends up in a training corpus (even indirectly, e.g. as a generated
prompt for the teacher), we should get written sign-off.

### (c) Publication of results

**Green.** Neither the Commercial Terms nor the AUP restricts publication
of research findings derived from Claude-driven experiments. The AUP's
"high-risk use cases" disclosure rule applies to journalistic/media
auto-publishing pipelines, not to research papers. Standard practice
(disclose that Claude was used) covers us.

### (d) Rate limits for sustained runs

**Green at Tier 3+.** Haiku 4.5 limits (from docs.anthropic.com /
platform.claude.com rate-limits page):

| Tier | RPM   | ITPM       | OTPM    | Cumulative deposit to advance |
|------|-------|------------|---------|-------------------------------|
| 1    | 50    | 50k        | 10k     | $5                            |
| 2    | 1,000 | 450k       | 90k     | $40                           |
| 3    | 2,000 | 1,000k     | 200k    | $200                          |
| 4    | 4,000 | 4,000k     | 800k    | $400                          |

A 24h single-agent run at, say, 1 turn/sec with ~5k input / ~1k output is
~60 RPM, 300k ITPM, 60k OTPM — comfortably under Tier 3. Nine parallel
agents would push us past Tier 2 ITPM but stay well inside Tier 3. Prompt
caching does **not** count cached reads toward ITPM on Haiku 4.5, so
effective throughput is materially higher than the raw numbers suggest.

### (e) Subscription / API credits

The user is correct, with a wrinkle. **Effective 2026-06-15**, Anthropic
splits subscription billing: a new "Agent SDK credit" is granted monthly,
metered at standard API list prices, for Claude Agent SDK / `claude -p` /
GitHub Actions / third-party agent traffic. Interactive Claude Code, chat,
and Cowork keep drawing from the regular subscription pool. Credits:

| Plan       | Monthly Agent SDK credit |
|------------|--------------------------|
| Pro        | $20                      |
| Max 5x     | $100                     |
| Max 20x    | $200                     |

No rollover. Overage continues at API rates if "usage credits" is enabled,
otherwise traffic is rejected until the next cycle. Users must **claim**
the credit via an email Anthropic is sending before June 15. Announcement
emailed 2026-05-13.

For our budget math: Max 20x ($200/mo subscription + $200/mo Agent SDK
credit) is the relevant tier; everything beyond the $200 credit bills at
standard Haiku 4.5 rates. The subscription does not subsidize API usage —
it provides a fixed allotment.

## 3. Recommendation

1. Run on the **API directly** (org account, Tier 3) rather than through a
   Pro/Max subscription. The new credit pool is small relative to a
   sustained multi-agent W2S replication; arbitrage is over.
2. Pre-deposit $200 cumulative to reach Tier 3 before the first long run.
3. Enable prompt caching aggressively on the agent system prompt and
   shared scratchpad; cached reads don't count against ITPM for Haiku 4.5.
4. Before publishing PGR numbers, file a short note with Anthropic Trust &
   Safety (support form) describing the setup. The phrase that needs
   blessing: "Claude Haiku 4.5 is used as the researcher agent; its outputs
   drive experiments that fine-tune Qwen-4B from Qwen-0.5B pseudo-labels.
   Claude outputs are not themselves training labels." Ask explicitly
   whether this is in scope of the AUP distillation clause.

## 4. Open questions for Anthropic

- Does the AUP's "model scraping or model distillation" clause apply when
  Claude outputs are orchestration artifacts (code, plans, critiques)
  rather than training labels for the student model?
- Is "prior authorization" granted by standard ToS acceptance for
  *research* uses, or does it require an explicit per-project sign-off?
- Are there reporting expectations (e.g., disclosure section, account
  type) for publishing a one-pager replicating Anthropic's own paper?
- Does Priority Tier or a research-access program apply at our scale?

## 5. Citations

- Anthropic Usage Policy (AUP), effective 2025-09-15.
  <https://www.anthropic.com/legal/aup> — accessed 2026-05-25.
- Anthropic Commercial Terms of Service, effective 2025-06-17, §B, §D.4.
  <https://www.anthropic.com/legal/commercial-terms> — accessed 2026-05-25.
- API Rate Limits documentation, Anthropic.
  <https://platform.claude.com/docs/en/api/rate-limits> — accessed 2026-05-25.
- Subscription billing split announcement coverage (2026-05-13 email;
  2026-06-15 effective): The New Stack, InfoWorld, VentureBeat, Zed blog.
  <https://thenewstack.io/anthropic-agent-sdk-credits/>,
  <https://www.infoworld.com/article/4171274/anthropic-puts-claude-agents-on-a-meter-across-its-subscriptions.html>,
  <https://zed.dev/blog/anthropic-subscription-changes> — accessed 2026-05-25.
  Primary source is the email to Max subscribers; no consolidated public
  Anthropic blog post was located.
- Anthropic statement on legitimate vs. illicit distillation, 2026-02.
  <https://www.anthropic.com/news/detecting-and-preventing-distillation-attacks>
  — accessed 2026-05-25.
