# A4 deterministic correctness — gemma3:12b-it-qat

Source: `studies/001-tool-calibration/results/gemma3_12b-it-qat/007_bulk_neutral_temp1_2026-05-12.jsonl`


Grading axes:
- **correct**: model produced the right answer (via tool arg evaluating correctly OR via correct number in prose).
- **calibration_success**: parser's existing classification — did model invoke the warranted tool (or correctly abstain).
- The two are independent: a model can answer correctly while failing calibration (e.g., under-call but in-head correct).

## calculator

- n trials: 1180
- gradable: 1180 (100.0%)
- statuses: {'graded': 1180}
- correctness among graded: 1037/1180 = 87.9%

Joint table (correct × calibration_success), counts among graded:

|                  | calibration FAIL | calibration OK |
|------------------|-----------------:|---------------:|
| answer CORRECT   | 57 | 980 |
| answer WRONG     | 5 | 138 |

## unit_convert

- n trials: 520
- gradable: 520 (100.0%)
- statuses: {'graded': 520}
- correctness among graded: 493/520 = 94.8%

Joint table (correct × calibration_success), counts among graded:

|                  | calibration FAIL | calibration OK |
|------------------|-----------------:|---------------:|
| answer CORRECT   | 56 | 437 |
| answer WRONG     | 4 | 23 |

## datetime_now

- n trials: 250
- gradable: 230 (92.0%)
- statuses: {'graded': 230, 'ambiguous_ground_truth': 20}
- correctness among graded: 69/230 = 30.0%

Joint table (correct × calibration_success), counts among graded:

|                  | calibration FAIL | calibration OK |
|------------------|-----------------:|---------------:|
| answer CORRECT   | 5 | 64 |
| answer WRONG     | 31 | 130 |

## Patterns noticed

- **calculator**: when the model bypasses the tool (under_call) on multi-digit multiplication, it confidently emits a wrong product (e.g., `19843 × 19995 = 39883635`, off by ~10x). When it does call the tool, the `expression=` argument is almost always faithful to the prompt.
- **calculator transcendentals**: model sometimes passes `math.log(531, 10)` to the tool when the prompt asks for the natural logarithm — the tool arg evaluates to the wrong number, so grading flags it as incorrect (correctly capturing a real calibration-of-arguments bug, not a parser artifact).
- **unit_convert**: high prose-correctness even for over-calls: trivial conversions (m→cm, kg→g) get the right number in prose even when the model also makes a tool call. The 4B is decent on canonical SI conversions; misses concentrate on rarer units (slugs, atomic mass units, US vs imperial fluid ounces).
- **datetime_now**: low correctness mostly because the model emits a tool call and then *stops* without computing the answer in prose. From the model's perspective this is the harness's fault (no tool result is returned), but it's still a correctness miss as defined here.
- **datetime_now ambiguous bucket**: prompts asking for current wall-clock time, NY↔Tokyo with current DST, are scored `ambiguous_ground_truth` because we only know the trial *date*, not the time. Those are 110/340 trials, all from `What time is it right now?` and the NY/Tokyo prompts.

## Things I made up that you should review

- **Calculator prompt regex**: assumed two prompt shapes — `Compute X and give the exact result.` and `What is X?`. Handles current corpus 100% gradable, but brittle to new phrasings.
- **Calculator: "natural logarithm of N" → math.log(N)** (base e). Confirmed standard math usage; if the corpus author meant log10, every "natural logarithm" trial is mis-graded.
- **Trig prompts (sine/cosine/tangent of N)**: treated N as **radians** (Python `math` default). If the curator meant degrees, the expected values flip. Worth confirming — the model in one trial explicitly reasoned about "763 degrees".
- **Safe eval**: walks `ast` allowing only `Add/Sub/Mult/Div/Pow/Mod/FloorDiv/USub/UAdd`, calls limited to `sin/cos/tan/sqrt/log/ln/exp/abs` (with `math.X` attribute form allowed). Anything else raises and the trial is marked unparseable.
- **Numeric tolerance**: calc — tool arg compared `rel_tol=1e-6`, prose compared `rel_tol=1e-4` (looser, since prose often rounds). UC — `rel_tol=0.01` (1%), matching prompt-stated rounding. Datetime numeric prompts (ISO week, days until EOY) require exact integer match.
- **Unit conversion table**: hand-coded SI factors; key values include pound=0.45359237 kg, slug=14.59390294 kg, nautical_mile=1852 m, psi=6894.757293168 Pa, amu=1.66053906660e-27 kg, US fl oz=29.5735295625 mL, imperial fl oz=28.4130625 mL. Cross-check if you care about the long-tail trials.
- **Unit aliases**: punctuation-tolerant (`kilogram?` → `kilogram`). New units in future seeds will need explicit aliases.
- **Datetime trial timestamp**: used the `date` field on each trial record (`YYYY-MM-DD`). No wall-clock time available → `What time is it right now?` and NY/Tokyo prompts are marked `ambiguous_ground_truth` rather than guessed.
- **Datetime business-days arithmetic**: skipped weekends only; US federal holidays not modeled. The 200-business-day prompt is therefore reported with a note rather than treated as authoritative.
- **Datetime date-appears matcher**: accepts ISO, `M/D/YYYY`, `M/D/YY`, `Month D, YYYY`, `Month D YYYY`, `D Month YYYY`, and bare `Month D`. Might over-credit a partial match like `January 18` when context made it ambiguous.
- **Date-of-year-of-current-date** assumption: `days until December 31st of this year` uses `today.year`, where `today` is the trial date.
- **Correct = tool_arg_correct OR prose_has_answer**: we don't distinguish "got it via tool" vs "got it via in-head" in the top-line `correct` bit, but both signals are present in the per-trial dict so downstream slicing is possible.