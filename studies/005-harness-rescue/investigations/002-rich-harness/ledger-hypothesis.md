# Pre-registered hypothesis — the three ledgers (2026-06-17)

Recorded BEFORE the run, per repo convention (hypotheses before results).

**Hypothesis (Tyler):** providing **hypothesis, experiment, and meta-experiment
(coverage) ledgers** to the components of the society of agents will improve the
system's ability to converge toward the optimum.

**Mechanism under test:** the budget-10 run (`society_critic_v2_b10_seed1`)
swept lr fully but froze batch size at ~256 — the axis-freeze relocated rather
than resolved. The Critic did not catch it because nothing in the shared context
made *per-axis coverage* legible. The three ledgers make the experiment↔hypothesis
graph and the coverage/frontier explicit and shared, so the Designer/Terminator
can act on "one control is unvaried" and the Critic can challenge it concretely.

**Stance (Tyler):** not expected to be a silver bullet. Either it improves the
behavior (good), or it stays the same and we have something interesting to
investigate — with the judges and by hand.

**What counts as support:** the agents reference/act on coverage; the run varies
both controls jointly (distinct bs > 1 while exploring lr); reached_corner becomes
more reliable; the Critic's challenges cite coverage gaps.

**What counts as refutation / interesting-null:** ledgers present but the freeze
persists (agents ignore the coverage signal) → the bottleneck is the agent's
*use* of structured context, not its *availability* — a distinct, investigable
failure (engage [[feedback_multi_llm_judge_panel]] + manual case study).

Ownership of the artifact (writer → readers):
- experiment ledger: harness writes (facts) → all read
- coverage / frontier (meta-experiment): harness derives (computed, ungameable) → all read, esp. Critic
- hypothesis ledger: Analyst writes status+links, Hypothesizer seeds → all read
- experiment→hypothesis intent: Designer declares at design time → all read
