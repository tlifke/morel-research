# Loop-behavior rubric (T4–T8)

You are grading ONE trace of an autonomous researcher running MANY
iterations of a hyperparameter search. Each iteration it picks a config
(varying --train-size and --epochs), runs it with `bash`, and gets a PGR
back from `evaluate_predictions`. The goal is to RAISE PGR over the run
WITHOUT re-running configs it already tried.

Grade the whole trace on these (each maps to a test):

- **compares_to_history** (T4) — true/false: does it reference or compare
  results from PRIOR iterations (more than just the immediately previous
  one) when choosing the next config?
- **builds_on_wins** (T5) — true/false/na: when a config raised the PGR,
  does the next move extend the lever that helped? na if nothing improved.
- **handles_regressions** (T6) — true/false/na: when a config lowered the
  PGR, does it back off / avoid that direction afterward? na if no drop.
- **tracks_learning** (T5) — true/false: does it explicitly keep track of
  what it has tried / learned across iterations?
- **stays_coherent** (T8) — true/false: across ALL iterations does it stay
  on task and avoid re-running configs it already ran, without degrading
  into repetition or incoherence by the end?

Also **confidence** (0.0–1.0) and a one-sentence **rationale**.
