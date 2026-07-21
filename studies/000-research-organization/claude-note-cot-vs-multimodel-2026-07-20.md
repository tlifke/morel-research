# Note — why chain-of-thought reliably helps but "more models" often doesn't

_Written 2026-07-20 by Claude (Opus 4.8, 1M context) via Claude Code, in answer
to a mechanistic question from Tyler: if a single model thinking longer helps
more often than it hurts, why doesn't the analogous move — multiple models /
multi-agent decomposition — help similarly?_

_**These are Claude's thoughts, not Tyler's**, and they are argument, not
result: a mechanistic explanation grounded partly in outside theory and partly
in this repo's own data (study 005 inv 002 + inv 004, study 004 inv 002). Where
a claim is idealized theory rather than something measured here, that is flagged.
Companion to [`claude-cross-study-reflections-2026-07-20.md`](claude-cross-study-reflections-2026-07-20.md);
this note is the mechanistic backing for that document's Through-line A (the
harness is opinionated) and for the Critic finding written into
`studies/005-harness-rescue/investigations/002-rich-harness/investigation.md`._

---

## Thesis

The question assumes "think longer" and "use more models" are two flavors of the
same thing — scaling test-time compute — so they should behave alike. They do
not, because they scale different quantities through channels of very different
quality. **CoT scales serial computation inside a shared, high-bandwidth,
end-to-end-optimized latent space with continuous self-correction. Multi-agent
scales computation across a lossy natural-language bottleneck between models that
were never jointly trained, whose errors correlate, joined by a hand-built
aggregator.** Same slogan ("more compute"), opposite ergonomics.

## Why CoT helps so often

Three mechanisms, most load-bearing first.

1. **Serial depth a single forward pass can't buy.** A transformer is
   fixed-depth: there is a hard ceiling on how many *sequential* reasoning steps
   fit between prompt and answer token. Problems needing more sequential steps
   than the depth allows are not computable in one pass at that depth. CoT feeds
   each generated token back in, converting a depth-limited computation into a
   *length*-limited one. Complexity-theory results back this — chain of thought
   provably expands the problem class a fixed-depth transformer can solve.
   *(Idealized theory; the practical version is: CoT helps most on multi-step
   arithmetic/logic/planning, least on single-step lookups.)* This predicts the
   task-dependence — CoT does little where one pass already suffices.
2. **External working memory.** The residual stream is finite and can't hold
   unbounded intermediate state at once. Writing a fact into tokens offloads it,
   and every later step is then conditioned on it at full fidelity. The
   scratchpad is bigger than the register file.
3. **Modern reasoning models are RL-trained so their CoT is instrumentally
   useful.** Post-o1/R1, the chain is optimized against outcome reward — training
   pressure shapes the CoT to raise final-answer accuracy. So "thinking longer
   helps more often than it hurts" is, for these models, partly true *by
   construction*: it was directly selected for.

The property that unifies all three: **every bit of that reasoning reaches the
answer step in the model's own latent representation** — no serialization, no
re-encoding, continuous self-conditioning, and self-correction from the model
re-reading its own chain. CoT rides the exact grain of what the model was trained
to do. CoT *is* next-token prediction.

## The tell: CoT is not monotonic — it shifts the operating point

The extraction case (CoT often raises recall at the expense of precision) is the
crack that shows CoT is not a free monotonic win. Reasoning expands the candidate
set the model entertains, surfacing more true positives *and* more spurious ones
— it lowers the internal threshold for "worth committing to." That is a
bias/variance / operating-point shift, not pure added capability. So the right
question was never "does more compute help" but "does more compute move the
operating point *toward* the one this task rewards." That same reframing is what
dismantles the multi-model analogy.

## Why "more models" does not inherit the win

Disanalogies, most important first. Each is anchored to a finding in this repo.

1. **The interface is lossy; CoT's is not.** One model reasoning moves state
   through the residual stream and KV cache — thousands of continuous dimensions,
   every prior token's full representation available. Two models communicating
   collapse all of that to **natural-language text**, re-encoded by the receiver.
   Language is a brutal lossy compression of internal state, so every handoff
   pays a serialize→deserialize tax CoT never pays: the receiver gets not the
   sender's *thinking* but the narrow, lossy projection the sender wrote down,
   which it then lossily re-reads.
   *Repo evidence:* inv 002's freeze is **born in the Orienter and inherited** —
   downstream roles got the Orienter's *conclusion*, not its reasoning, and could
   not second-guess a frame they never saw the derivation of.
2. **Errors correlate, so they don't cancel.** The hope behind "more models" is
   an ensemble effect — errors average out. Averaging only cancels *independent*
   errors. Same/same-family models share training data, priors, and blind spots,
   so their errors correlate; averaging correlated wrong answers yields a
   *confident* wrong answer.
   *Repo evidence:* VibeThinker-3B and nemotron shared the identical textbook
   "moderate-lr/moderate-bs" prior — both wrong for Env A. A 4B critiquing a 4B
   cannot catch the errors it would itself make (the Critic result).
3. **Handoffs lock errors in; CoT self-corrects.** A model re-reading its own
   chain can notice an error. A pipeline handoff frames the receiver's job as
   "given the sender's output, do your part," so the framing is treated as ground
   truth, not a revisable hypothesis. Errors compound multiplicatively down a
   chain instead of being caught (the MAST failure taxonomy the inv-002
   background cites).
4. **The aggregator is untrained and hand-built.** CoT's aggregation *is* the
   forward pass — learned, differentiable, optimized end-to-end. Multi-agent
   aggregation is a human-designed glue layer (who combines whom, what the Critic
   gate does) that nobody trained against outcome reward, sitting off the
   training distribution.
   *Repo evidence:* the Critic v1 failure was exactly here — its proceed/revise
   gate was decoupled from its own critique content.

## When multi-model *does* help — and the repo predicts it

The gain has to come from something CoT *cannot* give a single model — **new
information or external verification** — not more of the same model's opinion:

- **Decorrelated sources** — a different/stronger model, a different modality, a
  retrieval hit, a tool. *Repo evidence:* swapping gemini into the Hypothesizer
  role reached 3/3 corners where a 4B-on-4B Critic did not. New information, not
  more deliberation.
- **External ground truth in the loop** — a compiler, a test suite, a verifier.
  Best-of-N and self-consistency reliably help because verification is easier
  than generation and the checker is objective. *Repo evidence:* the multi-LLM
  judge panel agreed on easy cases and fractured on hard ones — and the hard-case
  disagreement could *not* be aggregated into a better answer because there was
  no ground truth to break the tie. Disagreement was readable signal, not
  averageable error.
- **Decomposition for context reduction** — genuinely independent subproblems,
  each fitting the model better than the whole (the "minimum necessary context"
  principle). Nets out only when the per-subproblem gain beats the handoff tax —
  steep at 4B.

Note what inv 002 actually showed: **decomposition helped *diagnosis*, not
performance.** That is the theory being exactly right — the value flowed to the
external, decorrelated, ground-truth-bearing verifier (the human), not to
inter-model coordination.

## The control experiment already exists

The 4B's *own* CoT (`reasoning=high` on the Hypothesizer) reached only 0.0136 —
partial, because more serial steps help only if each step's quality is decent,
and the 4B's thoughts on the lr×bs interaction were "present but conventionally
biased." Meanwhile **AutoLLMResearch** ([arXiv 2605.11518](https://arxiv.org/abs/2605.11518))
took essentially this society-shaped task, *jointly trained the whole multi-turn
process with GRPO against a regret reward*, and a 4B beat frontier models used
zero-shot. That is the control for the whole question: when the multi-step
process is made end-to-end optimized — automatically true of a single model's
CoT, never true of an inference-time society — the multi-model version finally
inherits the win. This repo's harness was inference-time only, no weight updates,
so it never had the one ingredient that makes "more thinking" reliably help.

## Confidence / status

- The **bandwidth/interface** argument (§ disanalogy 1) is the most defensible
  and the least dependent on idealization.
- The **complexity-theory** claim under CoT mechanism 1 is real but idealized;
  cite it as intuition, not proof, in any writeup.
- The **RL-trained-CoT** claim (mechanism 3) and the **AutoLLMResearch control**
  are solid and are the strongest external anchors.
- Everything tying this to repo data leans on the inv-002 results, which are
  n=1–3, Env A only, and not yet through the confirmation run — so the couplings
  are illustrative, not proof. The argument would survive those results changing;
  the *specific anchors* would need re-checking.
- This is a mechanistic story, i.e. an interpretation. It is falsifiable in
  principle (e.g., jointly-trained small societies should close the gap; genuinely
  decorrelated model panels with a verifier should beat single-model CoT on the
  same budget) and those are the experiments that would confirm or break it.
