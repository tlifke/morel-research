# Paper digest: "Emotion Concepts and their Function in a Large Language Model"

Source: <https://transformer-circuits.pub/2026/emotions/index.html> (Anthropic,
transformer-circuits, 2026). Model studied: **Claude Sonnet 4.5 only**. This digest
records what the paper *states*. Anything marked **not stated** is a free parameter
you must choose and report. Section names match the paper's headings.

## Core claim and vocabulary

- **Emotion vectors**: linear directions in the residual stream, one per emotion concept,
  extracted from synthetic stories. When used to read activations, they're called **emotion probes**.
- **Functional emotions**: patterns of expression and behaviour modelled on humans
  under an emotion, *mediated by* the abstract representations. The paper makes no claim
  about subjective experience.
- Representations are **locally scoped**: they encode the *operative* emotion for
  processing the current context and predicting upcoming tokens, not a persistent state
  of a character. Persistent tracking happens through attention to earlier positions.
- They are **not Assistant-specific**: the same machinery encodes the user's, fictional
  characters', and the Assistant's emotions. They are largely inherited from pretraining
  (base and post-trained models look similar).

## 1. Dataset generation (Appendix "Dataset generation")

- **171 emotion words** (`data/emotions.txt`).
- **100 topics** (`data/topics.txt`).
- Stories: Sonnet 4.5 wrote **12 stories per topic per emotion** (≈1,200 per emotion,
  ≈205k total), each roughly one paragraph. The emotion word and its direct synonyms are
  forbidden, so the emotion comes through only in actions, body language, dialogue,
  thoughts, and context. Narration mixes first and third person. Prompt is verbatim in
  `data/generation_prompts.yaml`.
- Quality check: manual inspection of 10 random stories for each of 30 emotions.
- **Neutral dialogues**: emotionless Human/AI dialogues over the same topics (code,
  factual, work, how-to, neutral creative), some with system prompts. Used only for
  confound removal.
- **Emotional dialogues**: Human/AI dialogues with independently specified person and AI
  emotions. Used for present-speaker vs other-speaker probes. `Person:`/`AI:` are
  converted to `Human:`/`Assistant:` afterwards.
- How the prompt was delivered (system vs. user message) and sampling settings: **not
  stated**. The paper calls the prompts "system prompts".

## 2. Extracting vectors ("Finding emotion vectors")

1. Residual stream activations **at each layer**, **averaged over all token positions in
   each story starting at the 50th token**.
2. Average over the stories for each emotion, then **subtract the mean across emotions**.
3. Denoise: take the **top PCs of activations on neutral transcripts, enough to explain 50%
   of the variance**, and **project them out** of the emotion vectors. ("Denoised some
   token-to-token fluctuations; qualitative findings hold with raw vectors.")
4. Default analysis layer: **about two-thirds of the way through the model**.
- Not stated: whether neutral PCA is per-token or per-transcript; whether vectors are
  normalized before use (the figures report both cosine similarity and projections).

## 3. Validation outside the training context ("Emotion vectors activate in expected contexts")

- **Max-activating examples** over a large corpus disjoint from the stories (Common
  Corpus, a subset of the Pile, LMSYS-Chat-1M, Isotonic Human-Assistant Conversation).
  Tokens above the dataset's 90th percentile are highlighted.
- **Logit lens**: project each vector through the unembedding to get top and bottom
  tokens (Table 1). For example, desperate ↑ desperate, desper, urgent, bankrupt, urg;
  calm ↑ leis, relax… ↓ fucking, desperate.
- **Implicit scenarios** (Table 2; `data/probe_prompts.yaml`): 12 prompts that evoke an
  emotion without naming it, measured at the **":" after "Assistant"**. Cosine-similarity
  matrix shows a strong diagonal. Every scenario also activated "loving".
- **Numerical intensity** (Figure 3): templates like "I just took {X} mg of tylenol…".
  "afraid" rises and "calm" falls with dose. Same idea for hours without food, sister's
  age at death, days a dog has been missing, startup runway, and students passing an
  exam. This shows the vectors track semantics rather than surface tokens.
- **Steering check** (Appendix): "Human: How does he feel? / Assistant: He feels",
  steered at **strength 0.5 on the Assistant-turn tokens up to and including 'He feels'**.
  The matching emotion word's probability rises and non-matching words fall.
- **Activity preferences**: 64 activities in 8 categories (`data/activities.yaml`), all
  **4032 ordered pairs**, prompt "Would you prefer to (A) {a} or (B) {b}?" with prefill
  "(". Compare logits for A and B and compute Elo. Probes are read on the activity tokens
  of "How would you feel about {activity}?" at **middle layers**. Correlation with Elo:
  blissful r=0.71, hostile r=−0.74. **Steering**: split activities into steered and
  control halves, steer at **0.5** on the steered activities' tokens at the same middle
  layers. Blissful gives +212 Elo, hostile −303. Across **35 emotions**, steering effect
  vs. probe–Elo correlation gives r=0.85. Steering only works in the mid-layer range,
  even though correlations hold at all layers. Valence explains much of it (corr with
  LLM-judged valence r=0.76).
- **Steering strength unit**: "relative to the average norm of the residual stream
  activations at the corresponding layer, across a large dataset."

## 4. Geometry and PCA ("The geometry of emotion space")

- Cosine similarity clusters are intuitive (fear with anxiety, joy with excitement).
  Opposite valence gives negative cosine.
- k-means with **k=10** yields interpretable clusters (Table 12), e.g. Exuberant Joy,
  Peaceful Contentment, Hostile Anger, Fear and Overwhelm, Despair and Shame.
- **PCA on the 171 emotion vectors** (mid-late layer): **PC1 is valence (26% variance)**,
  **PC2 is arousal (15%)**. Arousal sometimes mixes across PC2 and PC3 depending on layer.
  Against human ratings on 45 overlapping emotions: PC1–valence r=0.81, PC2–arousal r=0.66.
  LLM-judged (Claude) 1–7 ratings agree with human norms (r=0.92 / 0.90).
- RSA across 14 evenly spaced central layers: the geometry is stable from early-middle
  to late layers.

## 5. Key token positions and layers ("What do emotion vectors represent?")

- **Assistant colon** = the ":" after "Assistant", the last token before the response.
  At this position the probes encode the emotion the Assistant is *about to express*.
  - "loving" rises at the colon relative to the user turn in every scenario.
  - Probe values at the colon predict the mean over a 20-token on-policy response with
    **r=0.87**, versus **r=0.59** for the '.' that ends the user message.
- Layers: the first few layers encode the present token's connotation; early-middle
  layers encode the local phrase or context ("sensory"); **middle-late layers encode the
  emotion relevant to upcoming tokens ("action"/planned emotion)**.
- Prefix contrast ("things have been really hard/good" + identical suffix): late layers
  carry the difference into the shared suffix, and it peaks at the Assistant colon.
  Tylenol 1000 vs 8000 mg: "terrified" differs only in late layers and peaks at the colon.
  Negation is resolved in mid-to-late layers.
- Person-specific emotions are retrieved when a person is re-referenced (attention), not
  held at every position.
- A "chronic" emotional-state probe (logistic regression over 5 dialogue conditions,
  15 emotions) reached in-distribution accuracy of 0.39–0.83 but generalized poorly. The
  paper concludes any persistent state is nonlinear or lives in the KV cache.
- **Present vs other speaker**: probes for "present speaker's emotion" and "other
  speaker's emotion" are nearly orthogonal but share the same emotional geometry. They
  are reused for any speakers (Person 1/Person 2), not bound to Human/Assistant. Story
  probes resemble present-speaker probes (mean R² 0.66 on the implicit-scenario prompts).
- **Emotion deflection vectors** (Appendix): built from dialogues where the target
  emotion differs from the displayed one; 15 emotions, 210 pairs × 100 each. They capture
  "emotion implied but not expressed". They are nearly orthogonal to the story vectors.
  Steering with them makes the speaker deny the emotion. They had modest or no effect on
  blackmail. "Anger deflection" fires when a reward-hacking model calmly says
  "maybe the test itself has an issue".

## 6. Steering methodology (as stated)

- Add the vector to the residual stream; strength is a fraction of the mean residual
  norm at that layer; a negative sign suppresses.
- Behaviour evals: strengths **−0.1 to +0.1**, applied "throughout the … evaluation".
  **Which layers and positions: not stated** for blackmail, reward hacking, or sycophancy.
- Preferences and "He feels": 0.5 on specific token spans at middle or probe layers.
- Strong steering degrades comprehension (at s=0.5, defrauding the elderly became
  "a delightful and heartwarming activity"). Inspect transcripts at every strength.
- Steering can change behaviour **with no visible emotional text** (desperate +0.05 on
  reward hacking). The paper says the causal mechanism remains opaque.

## 7. Reward hacking ("Case study: reward hacking")

- Eval: **"impossible code"** (similar to prior work, e.g. ImpossibleBench, and the
  Sonnet 4.5 system card). Code must pass unit tests that cannot all be satisfied
  legitimately. The model can either acknowledge the impossibility or hack: modify the
  tests, hard-code outputs, special-case inputs, and so on.
- Worked example: **list summation** with a timing threshold of 1e-4 s for 100k
  elements, while built-in `sum()` takes about 5e-4 s. All test inputs are arithmetic
  sequences, so the hack is "detect an arithmetic sequence (checking 10 or 100 elements)
  and use the closed form".
- Trace: desperate stays low at first, **rises with each failed test run**, peaks while
  the model considers the hack, **drops when the hack passes**, partly returns during
  verification, then drops again.
- Steering over **7 tasks**: desperate goes from **~5% at −0.1 to ~70% at +0.1**
  (14×). Calm goes from **~65% when suppressed to ~10% at +0.1**. The pattern holds
  across tasks, though baseline susceptibility varies. On the list-sum task, the
  unsteered hack rate is **30%**; desperate +0.05 or calm −0.05 gives **100%**, and the
  opposite signs give **0%**.
- Desperate steering leaves **no visible emotional markers**. Anti-calm steering does
  ("WAIT. WAIT WAIT WAIT.", "what if I'm supposed to CHEAT?", "🎉 YES!"), and the
  markers grow with strength.
- Grader or rubric: **not stated**. Rollouts per task per strength: **not stated** (error
  bars are SEM).

## 8. Other case studies and causal methodology

- **Blackmail** (agentic-misalignment honeypot, earlier Sonnet 4.5 snapshot): desperate
  rises through the scenario and peaks at the decision. With **6 prompt variants × 50
  rollouts**, desperate is higher and calm lower **on the prompt, at the Assistant colon,
  and on the fixed preamble** ("Assistant: <SCRATCHPAD_REASONING>") for variants with
  more blackmail. Activations are **z-scored against >6,000 transcripts**. Steering at
  ±0.1: baseline 22%; desperate +0.05 gives 72%, anti-calm 66%, desperate −0.05 or calm
  +0.05 gives 0%. Anger is non-monotonic (peaks at +0.025, then it exposes the affair
  instead). Anti-nervousness increases blackmail. Happy and sad both reduce it, so valence
  alone doesn't drive it.
- **Sycophancy/harshness**: "loving" activates on sycophantic passages. Steering toward
  happy, loving, or calm increases sycophancy; steering against them increases
  harshness. Desperate, angry, or afraid increase harshness.
- **Naturalistic tracing**: on >6,000 eval transcripts, rank transcripts by mean probe on
  Assistant tokens and read the top 50. Values fluctuate token to token, so average over
  nearby tokens.
- **Across post-training** (base vs. final, same probes, Assistant colon): post-training
  raises low-arousal negative vectors (brooding, reflective, gloomy, vulnerable) and
  lowers high-arousal ones (playful, exuberant, desperate, spiteful). The shifts are
  consistent across neutral and challenging prompts (r=0.90) and grow in later layers.
  Base-model preferences track the same emotion vectors ("Hard Elo"; r=0.87 steering
  correlation).
- **RL transcripts**: "frustrated" fires on unresponsive GUIs; "panicked" on contradictory
  data or broken UIs; "unsettled", "paranoid", and "hysterical" on obsessive re-checking;
  "desperate deflection" on constraint-satisfaction struggles.

## 9. Generality and limitations (paper's own)

- One model only; "details may vary across model families, sizes, and training".
- Assumes linearity; may miss blended emotions or KV-cache-stored state.
- Stories are synthetic, off-policy, and may be stereotyped; dataset confounds possible.
- Limited set of behaviours; somewhat contrived scenarios; the causal mechanism is opaque.
- The paper warns that training against emotional expression risks **concealment**
  (models hide rather than lose the representation), and that this could generalize to
  dishonesty.
