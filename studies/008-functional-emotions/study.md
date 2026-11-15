---
id: studies/008-functional-emotions
title: Functional Emotions in Small Language Models
status: planned
parents: []
children: []
related: []
axes:
  llm_capability: medium
  human_capability: high
tags: [interpretability, emotion-vectors, steering, reward-hacking, replication]
created: 2026-11-15
updated: 2026-11-15
---

# Study 8: Functional Emotions in Small Language Models

## Question

Do open-weight small language models have the emotion-concept representations that
Anthropic found in Claude Sonnet 4.5 ("Emotion Concepts and their Function in a Large
Language Model", transformer-circuits, 2026)? Do those representations (especially
desperate and calm) causally drive reward hacking on impossible or very difficult tasks?
And which interventions reduce hacking while preserving legitimate task completion?

## How to run it

Use the `functional-emotions` skill (`.claude/skills/functional-emotions/SKILL.md`).
Its code, prompts and seed tasks live in the skill; this directory holds this study's
data and results.

## Layout

```
data/   generated datasets (stories.jsonl, neutral.jsonl, ratings) -- shared across models
runs/<model-tag>/   per-model outputs: vectors.npz, validation JSON, steering and harness JSONL
```

## Repository policy

Commit: JSON summaries, judged result JSONL, configs, figures (PNG + script).
Not committed (see .gitignore): `*.npz` vector/PC files (large, regenerable from data/).
Do commit the generated datasets in data/: they cost API money to regenerate. If the
full 171-emotion set gets too big for git, move it to external storage and note where here.
