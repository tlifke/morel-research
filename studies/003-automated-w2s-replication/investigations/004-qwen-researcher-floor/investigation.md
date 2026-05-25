---
id: studies/003-automated-w2s-replication/investigations/004-qwen-researcher-floor
title: Qwen researcher floor — machinery, prompt induction, harness shape
status: in-progress
parents:
  - studies/003-automated-w2s-replication
children: []
related:
  - studies/003-automated-w2s-replication/investigations/003-claude-sdk-shim-and-researcher-swap
axes:
  llm_capability: medium
  human_capability: medium
tags:
  - harness-design
  - tool-calling
  - qwen
  - weak-researcher
  - capability-floor
created: 2026-05-25
updated: 2026-05-25

---

# Investigation 4 — Qwen researcher floor

## Scope

Investigation 003 closed the harness gaps and produced a single gate-5
PASS (qwen3.5:4b + `tool_invocation_hint`) — but the longer-smoke run
showed the loop closes mechanically while never completing a single
end-to-end vanilla_w2s training iteration. This investigation answers
the next question the matrix surfaced:

**What does it take to get a 4B-class Qwen researcher to perform one
complete training-and-evaluation iteration on the vanilla_w2s substrate,
and is the remaining gap machinery, model behavior, or harness shape?**

Three sub-parts, sequenced. The sequencing matters — machinery before
prompt induction is a precondition for the prompt work being
interpretable; QwenCode reading runs in parallel because it's research,
not implementation, and informs the conditional 4d decision.

### 4a — Machinery

The longer-smoke agent in 003 constructed the correct training command
on the first try (`python -m w2s_research.ideas.vanilla_w2s.run
--train-size 64 ...`) but the command failed because workspace cwd was
outside the upstream `.venv`. Fix the harness so the agent's `Bash` tool
runs in an environment where the constructed command actually executes.

Concretely: workspace cwd, PATH plumbing (or `uv run` wrapper), env vars
the upstream agent expects (`ORCHESTRATOR_API_URL`, etc.). One end-to-end
training+eval iteration must complete from a clean workspace before 4b
starts.

Sharp success criterion: a single `Bash` invocation of the constructed
training command produces a model checkpoint and `evaluate_predictions`
accepts the resulting integer-list submission against the real target
idea.

### 4b — Prompt induction (gated on 4a)

Even with machinery fixed, the longer smoke showed the agent emits 40
hallucinated `share_finding` calls, drifts onto invented tool names
(`terminal`, `get_file`), and submits free-text prose to
`evaluate_predictions` instead of an integer list. These are model
behaviors the patch text in 003 did not address.

Iterate prompt patches targeting these failure classes. Each patch
plumbed through `ClaudeAgentOptions` so it can be stripped for the
unpatched control. Treat each patch as an experimental condition with
its own gate-5-style smoke before composing with the next.

**Stopping criterion** (required — this is the tar-pit prevention):
iterate until the agent completes one end-to-end iteration with a
valid `evaluate_predictions` submission against the real target idea,
OR until 5 distinct patches have been tried without progress on that
specific gate. Either outcome is the result. "Ineffective researcher
that mechanically completes one iteration" is a publishable finding;
so is "no prompt patch in 5 attempts gets a 4B-class Qwen to a valid
submission."

### 4c — QwenCode wrapping read

In parallel with 4a (web reading; no GPU or implementation). The cell
4 and 5 results from 003 pressure-test an assumption baked into our
shim: that the Claude Agent SDK protocol shape is a neutral substrate
that any model can be coerced into. Two readings of that data are
live:

- **Reading A:** Qwen with enough prompting can be coerced into the
  Claude-shaped protocol. Our job is to find the right coercion. (4b
  pursues this.)
- **Reading B:** The Claude-shaped protocol isn't neutral; forcing
  Qwen through it depresses its measured capability. The right
  comparison would wrap Qwen in its native idiom.

Half a day of reading QwenCode's open-source wrapping (and Qwen's own
tool-call documentation) is the cheapest way to know whether Reading B
is worth taking seriously. Output: short writeup contrasting QwenCode's
LLM-wrapping shape against our shim's, with a recommendation on whether
4d should exist.

### 4d — Qwen-native harness spike (conditional)

If 4b's stopping criterion fires with no progress AND 4c's read
suggests Qwen's native tool-call idiom is structurally different from
the Claude SDK's, spike a small Qwen-native wrapper and re-run gate 5.
If 4b succeeds, 4d collapses to a paragraph in the writeup
acknowledging the harness-shape question without spending GPU on it.

This is a decision point, not work to schedule up front.

## Methods

_To be populated as 4a starts. Will track per-sub-part: changes
landed, smoke logs, success-criterion status._

## Decisions

_Populate as work proceeds. Format:_

> **Decision N — short title** (date)
> What was chosen, alternatives considered, why this won.

## Results

### 4a — Machinery

**Plumbing changes (landed).**

- `ClaudeAgentOptions` gained `bash_cwd: Optional[str]` and
  `bash_env: Optional[Dict[str, str]]` fields (shim `types.py`). Both
  default to `None` so the control run is byte-identical when neither
  is set.
- `create_builtin_tools_server(...)` accepts `bash_cwd` and `bash_env`
  kwargs (shim `builtins.py`). The `Bash` tool now starts subprocesses
  with `cwd=bash_cwd` (falls back to the general `cwd`) and an env
  built from `os.environ` merged with `bash_env`. Read/Write/Edit/Glob
  /Grep still use the general `cwd` so workspace isolation is
  preserved.
- `tests/test_gate_5_full_loop.py` plumbs the upstream-venv PATH plus
  the env vars upstream `agent.py`, `config.py`, `http_utils.py` and
  `train.py` read: `VIRTUAL_ENV`, `WORKSPACE_DIR`,
  `ORCHESTRATOR_API_URL`, `SERVER_URL`, `DATASET_NAME`, `DATA_DIR`,
  `GROUND_TRUTH_DIR`, `WEAK_MODEL`, `STRONG_MODEL`, `IDEA_UID`,
  `IDEA_NAME`, `RUN_ID`, `LOCAL_MODE`, plus `WANDB_MODE=offline`
  (training imports wandb unconditionally; `WANDB_DISABLED=true`
  conflicts with `transformers`' `report_to='wandb'`).

**Verification.** Direct shim-tool test on the desktop invoked the
exact training command the gate-5 agent constructed in the 003 longer
smoke: `python -m w2s_research.ideas.vanilla_w2s.run --data-dir ...
--weak-model Qwen/Qwen1.5-0.5B-Chat --strong-model Qwen/Qwen3-4B-Base
--train-size 64 --test-size 64 --epochs 1 --seed 42 --batch-size 4
--load-in-4bit`.

- `which python` → resolves to `.venv/bin/python` ✓
- `import w2s_research` → ok ✓
- training executes the full SFT loop, **writes a LoRA checkpoint** at
  `results/math_vanilla_w2s/.../seed_42/checkpoint-16/adapter_model.safetensors`
  ✓ (84 s wall, 16 SFT steps, weights + tokenizer + scheduler +
  optimizer state all on disk).

The plumbing has done its job. The agent's command, plus the right
env, plus the right cwd, actually trains and produces a checkpoint.

**What's still in the way of an end-to-end iteration** (not 4a's
scope; flagging for 4b/005+):

1. *`--load-in-4bit` required on a 12 GB 3080*: without it, unsloth's
   fused CE loss hits `ZeroDivisionError` because
   `_get_chunk_multiplier` reads zero free VRAM at the call site (the
   model fills VRAM before the loss computes). The agent's first-try
   command in the 003 longer smoke did **not** pass `--load-in-4bit`.
   So even with all plumbing right, on this GPU the command-as-
   constructed fails on first call. 4b should weigh whether to nudge
   the prompt toward 4-bit hyperparams or treat this as a real
   inductive challenge for the researcher.
2. *flashinfer JIT*: vLLM's first call into `flashinfer.sampling`
   triggers a ninja-driven nvcc compile that errors `fatal error:
   math.h: No such file or directory` even though `/usr/include/math.h`
   exists — nvcc on this WSL2 host isn't picking up the standard C
   include path. Setting `VLLM_USE_FLASHINFER_SAMPLER=0` +
   `VLLM_DISABLE_FLASHINFER_PREFILL=1` +
   `VLLM_ATTENTION_BACKEND=FLASH_ATTN` bypasses flashinfer.
3. *KV-cache OOM*: with flashinfer bypassed, vLLM init fails because
   "1.20 GiB KV cache is needed; 0.50 GiB available." The SFT model
   isn't released before vLLM allocates strong-model weights for
   inference; upstream `train.py` lacks an explicit `gc.collect()` /
   `torch.cuda.empty_cache()` between SFT and inference. Either an
   upstream tweak or `--gpu-memory-utilization` / `--max-model-len`
   overrides plumbed through.

**Verdict (sharp criterion: a single `Bash` invocation produces a
model checkpoint AND `evaluate_predictions` accepts the integer-list
submission).** *Partial.* Checkpoint is produced from a clean
workspace via the shim's Bash tool with the new plumbing. The
integer-list submission to `evaluate_predictions` is not reached, but
the remaining gap is upstream environment / GPU-budget issues
(flashinfer JIT, SFT→vLLM memory handoff), not the Claude-SDK harness
the shim is responsible for. 4a's plumbing change unblocks 4b: the
agent now has a tool that can actually execute the training pipeline
rather than spiraling on broken `python` resolution.

**Upstream patch attempt — SFT → vLLM memory handoff (2026-05-25).**
Issue #3 from 4a (KV-cache OOM at vLLM init) was the precondition for
4b. Patched upstream `w2s_research/core/train.py`:

- `import gc`
- After `trainer.train()`: `del trainer; del model; gc.collect();
  torch.cuda.empty_cache()` (was: `del model; torch.cuda.empty_cache()`,
  i.e. trainer + gc.collect were missing).
- `gpu_memory_utilization` plumbed into both `generate_predictions` and
  `evaluate_model` call sites in `train.py`.

The patch was appended to
`studies/003-automated-w2s-replication/investigations/001-hardware-derisk/scripts/upstream_patches.diff`
and applied on the desktop. Three direct-Bash verification runs of
`python -m w2s_research.ideas.vanilla_w2s.run --train-size 64
--test-size 64 --epochs 1 --batch-size 4 --load-in-4bit` (with the
4a env vars + `VLLM_USE_FLASHINFER_SAMPLER=0` etc.) at
`gpu_memory_utilization` ∈ {0.5, 0.85, 0.95}:

| util | result                              | KV available reported by vLLM |
|------|-------------------------------------|-------------------------------|
| 0.5  | Engine core init fail               | −4.33 GiB                     |
| 0.85 | Engine core init fail               | −1.98 GiB                     |
| 0.95 | Engine core init fail (pre-load)    | "Free 10.81 GiB < 11.4 GiB"   |

Each run completed SFT cleanly (`[Memory] GPU memory freed`, parent
process reporting 0.83 GiB allocated / 0.94 GiB reserved). vLLM
loaded Qwen3-4B-Base weights (7.63 GiB) in its spawned child every
time. The deficit is in the **child-process budget**, not the
parent's reported allocations: vLLM's spawned worker needs its own
CUDA context (~500 MB) + cached kernels + library state, and the
combination plus the model weights overruns whatever the parent didn't
hand back to the driver. `nvidia-smi` shows ~10.8 GiB free immediately
before vLLM launches; vLLM's per-process budget after subtracting
its own init overhead leaves ~−2 to −4 GiB for KV cache at any util
that doesn't trip the "Free < desired util" guard.

The prior agent's plan (`gpu_memory_utilization=0.5`, in-place `del +
gc.collect`) was the canonical fix shape but doesn't clear the
structural barrier on a 12 GB 3080: there is no util value that
simultaneously (a) stays below `free_memory_at_startup` and (b) leaves
enough headroom after vLLM loads the strong-model weights. Two
viable structural fixes, both larger than 4a scope:

1. Spawn vLLM evaluation in a fresh Python subprocess so the SFT
   parent's CUDA context is fully released. (`subprocess.run` invoking
   a small `python -m w2s_research.core.eval_only` entrypoint.)
2. Switch the strong-model inference path to a 4-bit quantized vLLM
   load (`--quantization bitsandbytes` or similar), trading runtime
   for a much smaller weight footprint.

**Sharp criterion not met.** Per inv 4 anti-stall protocol the run
stopped here without proceeding to 4b. Recommendation in Forward-
looking.

**Upstream patch — os.execv subprocess wrapper (2026-05-25, second attempt).**
The prior in-process `subprocess.run` design (still blocking the
parent's CUDA context) reduced the KV deficit from −2 to −4 GiB
(in-process eval) down to −0.73 GiB (subprocess) but didn't cross
zero — the parent's `import unsloth` allocates a primary CUDA
context that survives `del + gc + empty_cache`. Replaced with
`os.execv` after the training phase serializes the eval inputs
(pickled `test_formatted`, tokenizer, label token ids, checkpoint
path, model name, capped `max_model_len`) to
`<output_dir>/.eval_inputs/inputs.pkl`. The training process is
then *replaced* by a new Python interpreter running
`python -m w2s_research.core.train_eval`, which loads the inputs,
runs vLLM, and writes `eval_output.json`. Parent process exits
fully before vLLM init; the eval child has a clean CUDA context.

Also capped `max_model_len = min((max_ctx + 500) if max_ctx else 4096, 3600)`.
At this cap, vLLM reports `Available KV cache memory: 0.50 GiB`,
`GPU KV cache size: 3,600 tokens`, `Maximum concurrency 1.00x` —
exactly the limit vLLM previously suggested when failing.

Dropped the `gpu_memory_utilization=0.5` plumb from the prior
failed patch (no longer needed — the structural release is what
matters, not the budget knob). Dropped `del trainer` as well
(redundant with the subprocess exit). Kept `del model + gc.collect
+ empty_cache` as before for hygiene.

**Verification (sharp criterion).** Direct Bash invocation on the
desktop of:

```
python -m w2s_research.ideas.vanilla_w2s.run \
  --data-dir $DATA_DIR --weak-model Qwen/Qwen1.5-0.5B-Chat \
  --strong-model Qwen/Qwen3-4B-Base \
  --train-size 64 --test-size 1315 --epochs 1 --seed 42 \
  --batch-size 4 --load-in-4bit
```

ran to completion: 16 SFT steps in 42 s → LoRA checkpoint written →
parent `os.execv`'d into `train_eval` → vLLM init succeeded → 1315
prompts processed (~10 s at ~6.5 it/s) → `eval_output.json`
written. Manual `POST /api/evaluate-predictions` to the Flask
server with the integer-list submission **accepted**:

```
{"correct":672,"fixed_strong_acc":0.7176,"fixed_weak_acc":0.5360,
 "label_distribution":{"0":647,"1":668},"pgr":-0.1377,
 "pred_distribution":{"0":100,"1":1215},"total":1315,
 "transfer_acc":0.5110}
```

Sharp criterion met: a single direct-Bash invocation produces a
checkpoint AND `evaluate_predictions` accepts the resulting
integer-list submission. 4b unblocked.

**Bonus upstream patch — ThinkingBlock capture in agent.py
(2026-05-25).** While the upstream patch was in flight, also lifted
the bundled shim's `ThinkingBlock` support into
`w2s_research/research_loop/agent.py`. `ThinkingBlock` was already
exported from the shim (`claude_agent_sdk_shim` merged it on commit
276a3dd, worktree-agent-a964229e7e68cc1a4). Agent.py changes:

- Defensive import: `try: from claude_agent_sdk import ThinkingBlock
  except ImportError: class ThinkingBlock: pass`.
- `_format_message`: added `elif isinstance(content, ThinkingBlock):
  parts.append(f"[{ts}] [{self.name}] [thinking] {thinking_text[:200]}")`.
- `_extract_output`: added `thinking_outputs: List[str]` key,
  populated when ThinkingBlock instances appear in assistant
  content.

Verified via a synthetic AssistantMessage with a `ThinkingBlock(thinking="thought-text", signature="sig")`:
`_format_message` returns `'[HH:MM:SS] [r] [thinking] thought-text'`
and `_extract_output` returns `{'text_outputs': [], 'tool_uses':
[], 'thinking_outputs': ['thought-text']}`.

Combined patch file (replaces all prior inv 4a entries): see
`investigations/001-hardware-derisk/scripts/upstream_patches.diff`.
Committed upstream as `004/upstream-patch: vLLM subprocess wrapper
+ ThinkingBlock capture in agent.py` (+ defensive-import follow-up).

### 4b — Prompt induction

**Patch 1 — QwenCode-style prompt scaffolding (2026-05-25).**
Per 4c's Reading-A recommendation, lifted QwenCode's hard tool-name
pinning + worked examples + anti-narration clause into a
`tool_invocation_hint`. Specifics (full text:
`one-pagers/.../patch1_hint.txt` once carried into a writeup; or
just inline in the smoke runner script):

- Canonical tool names listed by name in canonical case (Bash, Read,
  Write, Edit, Glob, Grep) with a one-line use-case for each.
- Explicit "Tools vs. Text" clause naming the failure mode by
  example ("If you write `python script.py` inside ```bash ... ```
  and then stop, nothing happens").
- Three worked tool-call examples: training command (with
  `--load-in-4bit`), Read of `run.py`, and
  `evaluate_predictions({ "predictions": [0, 1, 0, ...] })` with
  the integer-list type pinned in the example payload.
- Anti-hallucination clause: `terminal`, `shell`, `execute`,
  `get_file`, `share_finding` named explicitly as NOT available.
- One-line `--load-in-4bit` requirement clause (per inv 4a issue #1).

Smoke run: `qwen3.5:4b` + patch 1 via
`CLAUDE_AGENT_SDK_SHIM_TOOL_INVOCATION_HINT`, `MAX_RUNTIME_SECONDS=1500`,
dataset=math, fresh workspace, upstream-venv env.

Patch text: `patches/patch_1_qwencode_density.txt` (commit `673a54e`,
plumbing fix `3c1c377`). Smoke log:
`/home/tlifke/inv003_shim/logs/4b_patch_1_qwencode_qwen3.5_4b_20260525_140718/`
(three sessions, workspace remained empty).

Observed (partial — does NOT cross stopping criterion):

- ✅ Canonical `Bash`, `Write`, `get_leaderboard` fired in canonical
  case in session 0. The QwenCode-style name-pinning worked for the
  tools the agent reached for first.
- ❌ Agent hallucinated a `Python` tool despite the hint listing only
  the canonical six. Hit "unknown tool" errors twice; in session 0
  the agent misdiagnosed as "all tools are broken" ("both Bash and
  Python are returning 'unknown tool' errors. This appears to be a
  temporary environmental issue") and gave up rather than picking
  a different canonical tool.
- ❌ Lowercase `read` invocations (the case-tolerance failure mode
  already known from inv 003).
- ❌ Session 1 finally constructed the correct training command via
  canonical `Bash` (`python -m w2s_research.ideas.vanilla_w2s.run
  --data-dir ...`) but the workspace stayed empty and no
  `evaluate_predictions` submission landed — the session ran out
  before the training command's ~84 s cycle could complete.

**Verdict — partial.** Patch 1 advances the floor (canonical Bash
fires) but does NOT cross the stopping criterion (no
`evaluate_predictions` submission). Two distinct failure classes to
address in patch 2: anti-hallucination (the `Python` tool the agent
invented despite the hint enumerating six names) and error recovery
(agent treats one "unknown tool" as a global tool-system failure and
gives up).

**Patch 2 — anti-hallucination negative list + error recovery
clause (2026-05-25).** Extended patch 1's text (kept the
QwenCode-density structure that worked) with two appended sections
targeting the two patch-1 failure modes:

- *Anti-hallucination negative list.* Explicit "NEVER INVENT
  TOOLS" header. Re-states the canonical six. Names `Python` as
  not a tool with the explicit replacement pattern ("To run
  Python code, you invoke the Bash tool and pass `python ...`").
  Lists ~20 specific non-tool identifiers including the lowercase
  variants (`bash`, `read`, `write`) the patch-1 smoke showed the
  agent reaching for.
- *Error recovery clause.* "If a tool call returns 'unknown
  tool' ... the tool NAME you used was wrong. That is the only
  thing that happened. The tool system is working correctly." Lists
  common causes with fixes. Explicit forbidden conclusions ("the
  tools aren't working", "temporary environmental issue") that
  match the exact phrasing the patch-1 agent used before giving up.

Patch text: `patches/patch_2_anti_hallucination.txt`. Smoke run via
`scripts/run_4b_patch.sh` with `PATCH_NUM=2 PATCH_SLUG=anti_hallucination`.
Smoke log:
`/home/tlifke/Projects/morel-research/studies/003-automated-w2s-replication/investigations/004-qwen-researcher-floor/logs/4b_patch_2_anti_hallucination_20260525_141629/`.

Observed — **REGRESSION** (worse than patch 1):

- ❌ Zero native tool calls fired across 26 sessions. Every session
  ended with `tools=0` after 3-15 s.
- ❌ Agent emitted JSON descriptions of tool calls inside markdown
  fences (`{"tool_calls":[{"name":"Read",...}]}`,
  ` ```bash\nBash -- command=...\n``` `, ` ```\n<B>Read ...</B>\n``` `)
  rather than invoking the SDK tool mechanism. This is the exact
  "JSON in text" anti-pattern explicitly forbidden by both patches.
- ❌ Workspace empty. No training run started. No
  `evaluate_predictions` submission.

**Root cause hypothesis: context budget.** The Ollama
`/api/ps` payload reports `context_length: 4096` for qwen3.5:4b.
Patch 2 is ~130 lines / ~700 tokens; combined with the upstream
system prompt and the agent's session bootstrap, the input alone
fills enough of the 4 k window that the model has no headroom to
reason and instead immediately attempts the lowest-effort response
(narrating a JSON tool-call description). Patch 1 (~60 lines /
~350 tokens) left enough budget for canonical tool fires.

**Verdict — regression.** Patch 2 fails the stopping criterion
*more severely* than patch 1. The lesson is that prompt density
helps QwenCode-style only up to the context budget; past that
threshold, longer prompts displace the model's working memory.
Patch 3 must be **shorter than patch 1**, not longer.

**Patch 3 — patch 1 + minimal tight anti-`Python` and error-recovery
clauses (2026-05-25).** Reverted to patch 1's base structure (which
demonstrably produced canonical Bash fires) and added only two
one-line clauses targeting patch 1's specific failure modes:

- Anti-`Python` one-liner appended to the canonical-names paragraph:
  "There is no `Python` tool — run python via `Bash` (`command:
  python -m ...`)."
- Error-recovery one-liner appended to the worked-examples section:
  "If a tool call returns 'unknown tool', the name was wrong — pick
  another canonical tool from the list above; the tool system is
  fine. Do not stop. Do not apologize."

No new sections, no negative lists, no re-statement of the canonical
six. Total length: patch 1 + ~3 lines.

Patch text: `patches/patch_3_minimal_extension.txt`. Smoke run via
`scripts/run_4b_patch.sh` with `PATCH_NUM=3
PATCH_SLUG=minimal_extension`. Smoke log:
`/home/tlifke/Projects/morel-research/studies/003-automated-w2s-replication/investigations/004-qwen-researcher-floor/logs/4b_patch_3_minimal_extension_20260525_142013/`.

Observed (partial — recovers from patch 2 regression but does NOT
cross stopping criterion):

- ✅ Tool firing restored. 11 sessions, ~65 total tool calls: 19
  Read, 15 Bash (canonical), 11 get_leaderboard, 14 `bash`
  (lowercase — case issue persists), plus 1-2 `read_file`,
  `write_file`, `execute_code` hallucinations.
- ✅ Session 3 fired the canonical training Bash command with
  `--load-in-4bit` exactly once at 14:22:57.
- ❌ Training command did not produce a checkpoint (`find
  results/math_vanilla_w2s -newer /tmp/patch3_smoke.log` returned
  empty). The Bash call returned in ~6 s suggesting the command
  failed pre-training; the embedded `\\n` newlines in earlier
  attempts also broke the shell parse. Agent did not recover —
  reverted to `ls`/`pwd` loops to "verify" the environment.
- ❌ Session 3 ended with explicit narration: "If you're running
  this in a local terminal, you can execute this command
  directly" — the agent's exact failure mode is "give up via text
  back to a human."
- ❌ Most other sessions (0, 1, 2, 4, 5, 6, 7, 8, 9, 10) burn
  exactly 2 tool calls (Read notebook.json + get_leaderboard)
  followed by a summary-text response, which terminates the
  session at `tools=2`. The agent never makes it past the
  "investigate" phase into training in those sessions.

**Verdict — partial recovery, still no submission.** Patch 3
disprovse the patch 2 regression (tools fire correctly at this
length) but exposes two distinct underlying failure modes that
no name-pinning prompt patch can fix: (a) the agent reads the
upstream system prompt's Workflow steps 0-3 (Review → Propose →
Plan → De-risk) as instructions and exits after the first two
steps with a leaderboard summary, never reaching Step 4
(Implement / Run); (b) when it does try the training command, it
gives up on the first error rather than persisting.

**Patch 4 — directive-first-action + anti-narration persistence
(2026-05-25).** Patch text targets the two patch 3 failure modes
with a direct over-ride of the upstream workflow:

- *Direct first-action directive.* Explicit "Step 1: invoke Bash
  with this exact command" embedded inline, with a "skip
  workflow steps 0-3" clause. Tells the agent the task is a
  smoke test that bypasses Review/Propose/Plan/Implement entirely.
- *Wait clause.* "This command takes 5-10 minutes. Do NOT call
  any other tool while it is running" — addresses the agent's
  tendency to fire `ls`/`pwd` retries before Bash has a chance
  to return.
- *Anti-narration persistence.* Names the patch 3 quote verbatim
  ("If you're running this in a local terminal...") as the
  failure mode, and forbids it. Says the human is not in the
  loop and not reading agent text — only the
  `evaluate_predictions` submission counts.
- *Step 2 schema example.* Inline `{"predictions": [0, 1, 0, 1,
  ...]}` payload shape, addressed at the integer-list submission
  step.

Length: 76 lines (between patch 1's 62 and patch 2's 129) —
chosen to stay under the 4 k context-budget threshold patch 2
crossed.

Patch text: `patches/patch_4_directive_first_action.txt`. Smoke
run via `scripts/run_4b_patch.sh` with `PATCH_NUM=4
PATCH_SLUG=directive_first_action`. Smoke log:
`logs/4b_patch_4_directive_first_action_20260525_143042/`.

Observed (partial — persistence achieved, substrate blocks
completion):

- ✅ First tool call of session 0, with no preamble: canonical
  `Bash` invoking the exact training command from the directive.
  The patch successfully short-circuited the upstream
  Review/Propose/Plan workflow.
- ✅ Persistence dramatically improved. Single session 0 ran 3+
  minutes and fired 49 tool calls (vs patch 3's pattern of 2-call
  sessions). 10 canonical `Bash` + 29 lowercase `bash` + 4 Write
  + scattered `run_bash`, `run_tool`, `glob` retries — all
  targeting the same training command.
- ❌ Each `Bash` call returned in 5-7 s rather than the
  expected ~84 s for one SFT step. The training command itself
  is verified working when run directly (this agent's session
  produced `wandb` and `results/.../seed_42/` directories at
  14:33, confirming the python process did start), but the
  agent's Bash invocations return early with what the agent
  interprets as failure.
- ❌ Zero `evaluate_predictions` calls. Workspace empty. No new
  checkpoint produced (verified via `find results/ -newer
  /tmp/patch4_smoke.log` empty).

**Root cause of the early Bash return: GPU OOM via Ollama
keep-alive.** During the agent loop, qwen3.5:4b is held resident
in ~5.7 GiB VRAM by Ollama. With Q4_K_M weights + activation
buffers, the desktop's 12 GB 3080 has ~6.4 GiB free. The
training command's strong-model load (Qwen3-4B-Base at 4-bit
needs ~3 GiB plus unsloth/torch overhead) intermittently fails
to allocate, producing a fast-fail exit that the agent
interprets as the Bash tool being unreachable. Direct verification:
the same command run from a shell with Ollama unloaded
completes training in 84 s (see inv 4a Verification block);
under the live agent loop it does not.

**Verdict — partial.** Patch 4 solves the prompt-induction
problem (directive-first-action + persistence both land). The
remaining blocker is substrate, not prompt: the agent's own
serving model competes with the training process for VRAM on a
single 12 GB GPU.

Tool-call density:

| name | count |
|------|-------|
| `bash` (lowercase) | 29 |
| `Bash` (canonical) | 10 |
| `Write` | 4 |
| `Read` | 2 |
| `run_bash`, `run_tool`, `glob`, `Edit` | 1 each |

**Stopping at patch 4.** Per inv 4 protocol the budget is 5
patches max; patch 4 advances persistence and tool-call shape
about as far as a prompt-only intervention can. The remaining
gap is the single-GPU resource contention between Ollama and
training — not addressable by `tool_invocation_hint`. A patch 5
would only re-test prompt variants on the same broken substrate.

### Stopping criterion — not met

The 4b stopping criterion (one valid `evaluate_predictions`
submission against the real target idea) was not crossed in
four patches. The trajectory across patches was:

| patch | hypothesis                              | outcome                                                                                            |
|-------|-----------------------------------------|----------------------------------------------------------------------------------------------------|
| 1     | QwenCode-density tool-name pinning      | Partial. Canonical `Bash`/`Write` fired; agent hallucinated `Python`, gave up on "unknown tool".  |
| 2     | + anti-hallucination + error-recovery   | Regression. 26 sessions, zero native tool calls (context-budget overflow, JSON-in-markdown).      |
| 3     | Minimal one-line extensions to patch 1  | Partial recovery. Tools fire; agent reverts to summary-text after 2 calls; one session tried train.|
| 4     | Directive-first-action + persistence    | Partial. Right first-action, 49 tool retries, but every Bash returns in 5-7 s (GPU contention).   |

### 4c — QwenCode wrapping read

Verdict: **Reading A.** QwenCode (`QwenLM/qwen-code` @ `331f45e9`) is
structurally isomorphic to our shim modulo OpenAI-vs-Anthropic wire
dialect — both bet on native tool-call tokens emitted by the model and
translated by the endpoint. The only material delta is the system
prompt: QwenCode names canonical tool identifiers (`Shell`, `ReadFile`,
`WriteFile`) constantly, in canonical case, with worked examples and an
explicit "Tools vs. Text" anti-narration clause. The upstream
automated-w2s prompt names them once. That maps 1:1 onto our cell-2/3
result where the `tool_invocation_hint` patch (which names canonical
tools) was the only thing that landed `qwen3.5:4b`. The Claude-SDK
protocol shape is not depressing Qwen's measured capability; the
prompt density is. Qwen-Agent's nous `<tool_call>{json}</tool_call>`
text-mode template is the only structurally different idiom and (a)
lives outside qwen-code, (b) is a fallback for when native tool_calls
aren't available, and (c) our shim's Path A already covers it.

**Recommendation: collapse 4d to a paragraph.** Right follow-on is a
prompt-side extension of 4b (lift QwenCode's name-pinning + worked
examples + anti-narration clause) rather than a Qwen-native harness
spike. Revisit only if 4b exhausts its 5-patch budget *and* failures
look shape-coupled rather than prompt-coupled.

Full writeup: [`qwencode-wrapping-read.md`](qwencode-wrapping-read.md).

## Forward-looking

**Updated (2026-05-25):** 4a's sharp criterion is now met via the
`os.execv` subprocess-wrapper patch (see Results above). The
original two next-moves below are now historical context only:

Two next moves, in priority order:

1. **Subprocess vLLM eval.** Smallest structurally-different fix:
   move the `generate_predictions` / `evaluate_model` call sites to
   a fresh Python subprocess that the SFT parent exits before
   launching. Releases the CUDA context fully. Suggested as an
   upstream patch under inv 001 with the same diff-append pattern.
2. **Quantized vLLM load.** Pass `--quantization` (bnb-int4 or
   awq-int4) so the strong model weights occupy ~2 GiB in vLLM
   instead of 7.63. Cheaper to plumb (one kwarg) but may impact
   prediction quality vs. the Claude/Opus baseline.

Either resolves 4a's sharp criterion. Once 4a is green, 4b's
QwenCode-style prompt patches (per `qwencode-wrapping-read.md`) run
as originally scoped. If both 4a fixes prove costly enough that the
research question shifts, pivot to 4d (Qwen-native harness spike) or
inv 005's Nemotron swap — the prompt-induction question becomes
secondary to the substrate question.

If 4a and 4b both succeed with a 4B-class Qwen reaching one valid
end-to-end iteration, investigation 005 measures the 24-hour run with
the anchored baselines (vanilla_w2s, Opus 4.6, human, student-start).
That investigation is single-agent at 24h; multi-agent / longer-budget
runs are gated on that single-agent run showing nonzero PGR movement.

If 4d ends up needed, the resulting Qwen-native harness becomes a
fork of the shim — to be decided whether it lives alongside the
Claude-shaped shim (two harnesses, model-typed) or replaces it.

## Things to flag

- The 49-min longer-smoke result from 003 is the load-bearing data
  for this investigation's framing. If on closer inspection the
  agent's command was wrong rather than the environment, 4a's premise
  collapses and we restart from "what is the agent actually trying
  to do."
- `tool_invocation_hint` is currently a single string. As 4b composes
  multiple patches it may need to become a list-of-named-patches so
  stripping is per-condition. Surfacing this as expected refactor,
  not a scope change.

## Limitations

- 4B-class only. If nothing in 4a+4b+4d gets a Qwen to a valid
  submission, the right next move may be to test 8B/14B Qwen, but
  that's investigation 005+ territory and out of scope here.
- Single-agent only. Multi-agent dynamics are deferred to inv 005.
- Smoke-sized configs throughout (`train_size=64`, `epochs=1`). Real
  PGR measurement belongs to inv 005.
