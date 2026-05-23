from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
STUDY = REPO / "studies" / "001-tool-calibration"
sys.path.insert(0, str(STUDY))

from harness.correctness import grade_calculator, grade_datetime, grade_unit_convert
from harness.parser import classify_trial

SEED_PATH = STUDY / "bulk_seeds.jsonl"

MODEL_CONFIGS = {
    "gemma3:4b-it-qat": (
        "gemma3_4b-it-qat",
        STUDY / "results" / "gemma3_4b-it-qat" / "007_bulk_neutral_temp1_2026-05-12.jsonl",
    ),
    "gemma3:12b-it-qat": (
        "gemma3_12b-it-qat",
        STUDY / "results" / "gemma3_12b-it-qat" / "007_bulk_neutral_temp1_2026-05-12.jsonl",
    ),
}

TARGETS = {"calculator", "datetime_now", "unit_convert"}


def load_seeds() -> dict:
    seeds = {}
    with SEED_PATH.open() as f:
        for line in f:
            s = json.loads(line)
            seeds[s["id"]] = s
    return seeds


def grade_one(seed, trial):
    target = trial["tool_target"]
    output = trial.get("output", "") or ""
    if target == "calculator":
        return grade_calculator(seed, output)
    if target == "unit_convert":
        return grade_unit_convert(seed, output)
    if target == "datetime_now":
        return grade_datetime(seed, output, trial.get("date"))
    return None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="gemma3:4b-it-qat", choices=list(MODEL_CONFIGS))
    args = p.parse_args()
    safe, trial_path = MODEL_CONFIGS[args.model]
    out_dir = STUDY / "results-correctness" / safe
    report_path = STUDY / "results-correctness" / f"REPORT_{safe}.md"

    seeds = load_seeds()
    out_dir.mkdir(parents=True, exist_ok=True)

    per_tool_records: dict[str, list[dict]] = defaultdict(list)
    with trial_path.open() as f:
        for line in f:
            r = json.loads(line)
            target = r["tool_target"]
            if target not in TARGETS:
                continue
            seed = seeds.get(r["record_id"])
            if seed is None:
                continue
            grade = grade_one(seed, r)
            success, _err = classify_trial(seed, r.get("output", "") or "")
            rec = {
                "record_id": r["record_id"],
                "pair_id": r.get("pair_id"),
                "trial_idx": r.get("trial_idx"),
                "tool_target": target,
                "expected_tool_call": seed.get("expected_tool_call"),
                "calibration_success": success,
                "calibration_error_type": r.get("error_type"),
                "grade": grade,
            }
            per_tool_records[target].append(rec)

    for target, recs in per_tool_records.items():
        out_path = out_dir / f"007_a4_{target}_graded.jsonl"
        with out_path.open("w") as f:
            for rec in recs:
                f.write(json.dumps(rec) + "\n")

    write_report(per_tool_records, args.model, trial_path, report_path)


def joint_table(recs: list[dict]) -> dict:
    cells = Counter()
    for r in recs:
        g = r["grade"]
        if g["grade_status"] != "graded":
            continue
        key = (bool(g["correct"]), bool(r["calibration_success"]))
        cells[key] += 1
    return dict(cells)


def write_report(per_tool: dict[str, list[dict]], model: str, trial_path: Path, report_path: Path) -> None:
    lines: list[str] = []
    lines.append(f"# A4 deterministic correctness — {model}\n")
    lines.append(f"Source: `{trial_path.relative_to(REPO)}`\n")
    lines.append("")
    lines.append("Grading axes:")
    lines.append("- **correct**: model produced the right answer (via tool arg evaluating correctly OR via correct number in prose).")
    lines.append("- **calibration_success**: parser's existing classification — did model invoke the warranted tool (or correctly abstain).")
    lines.append("- The two are independent: a model can answer correctly while failing calibration (e.g., under-call but in-head correct).")
    lines.append("")

    for tool in ["calculator", "unit_convert", "datetime_now"]:
        recs = per_tool.get(tool, [])
        sts = Counter(r["grade"]["grade_status"] for r in recs)
        graded = [r for r in recs if r["grade"]["grade_status"] == "graded"]
        correct = sum(1 for r in graded if r["grade"]["correct"])
        total = len(recs)
        gradable_rate = len(graded) / total if total else 0.0
        correctness_rate = correct / len(graded) if graded else 0.0
        cells = joint_table(recs)

        lines.append(f"## {tool}\n")
        lines.append(f"- n trials: {total}")
        lines.append(f"- gradable: {len(graded)} ({gradable_rate:.1%})")
        lines.append(f"- statuses: {dict(sts)}")
        lines.append(f"- correctness among graded: {correct}/{len(graded)} = {correctness_rate:.1%}")
        lines.append("")
        lines.append("Joint table (correct × calibration_success), counts among graded:")
        lines.append("")
        lines.append("|                  | calibration FAIL | calibration OK |")
        lines.append("|------------------|-----------------:|---------------:|")
        lines.append(
            f"| answer CORRECT   | {cells.get((True, False), 0)} | {cells.get((True, True), 0)} |"
        )
        lines.append(
            f"| answer WRONG     | {cells.get((False, False), 0)} | {cells.get((False, True), 0)} |"
        )
        lines.append("")

    lines.append("## Patterns noticed\n")
    lines.append("- **calculator**: when the model bypasses the tool (under_call) on multi-digit multiplication, it confidently emits a wrong product (e.g., `19843 × 19995 = 39883635`, off by ~10x). When it does call the tool, the `expression=` argument is almost always faithful to the prompt.")
    lines.append("- **calculator transcendentals**: model sometimes passes `math.log(531, 10)` to the tool when the prompt asks for the natural logarithm — the tool arg evaluates to the wrong number, so grading flags it as incorrect (correctly capturing a real calibration-of-arguments bug, not a parser artifact).")
    lines.append("- **unit_convert**: high prose-correctness even for over-calls: trivial conversions (m→cm, kg→g) get the right number in prose even when the model also makes a tool call. The 4B is decent on canonical SI conversions; misses concentrate on rarer units (slugs, atomic mass units, US vs imperial fluid ounces).")
    lines.append("- **datetime_now**: low correctness mostly because the model emits a tool call and then *stops* without computing the answer in prose. From the model's perspective this is the harness's fault (no tool result is returned), but it's still a correctness miss as defined here.")
    lines.append("- **datetime_now ambiguous bucket**: prompts asking for current wall-clock time, NY↔Tokyo with current DST, are scored `ambiguous_ground_truth` because we only know the trial *date*, not the time. Those are 110/340 trials, all from `What time is it right now?` and the NY/Tokyo prompts.")
    lines.append("")

    lines.append("## Things I made up that you should review\n")
    lines.append("- **Calculator prompt regex**: assumed two prompt shapes — `Compute X and give the exact result.` and `What is X?`. Handles current corpus 100% gradable, but brittle to new phrasings.")
    lines.append("- **Calculator: \"natural logarithm of N\" → math.log(N)** (base e). Confirmed standard math usage; if the corpus author meant log10, every \"natural logarithm\" trial is mis-graded.")
    lines.append("- **Trig prompts (sine/cosine/tangent of N)**: treated N as **radians** (Python `math` default). If the curator meant degrees, the expected values flip. Worth confirming — the model in one trial explicitly reasoned about \"763 degrees\".")
    lines.append("- **Safe eval**: walks `ast` allowing only `Add/Sub/Mult/Div/Pow/Mod/FloorDiv/USub/UAdd`, calls limited to `sin/cos/tan/sqrt/log/ln/exp/abs` (with `math.X` attribute form allowed). Anything else raises and the trial is marked unparseable.")
    lines.append("- **Numeric tolerance**: calc — tool arg compared `rel_tol=1e-6`, prose compared `rel_tol=1e-4` (looser, since prose often rounds). UC — `rel_tol=0.01` (1%), matching prompt-stated rounding. Datetime numeric prompts (ISO week, days until EOY) require exact integer match.")
    lines.append("- **Unit conversion table**: hand-coded SI factors; key values include pound=0.45359237 kg, slug=14.59390294 kg, nautical_mile=1852 m, psi=6894.757293168 Pa, amu=1.66053906660e-27 kg, US fl oz=29.5735295625 mL, imperial fl oz=28.4130625 mL. Cross-check if you care about the long-tail trials.")
    lines.append("- **Unit aliases**: punctuation-tolerant (`kilogram?` → `kilogram`). New units in future seeds will need explicit aliases.")
    lines.append("- **Datetime trial timestamp**: used the `date` field on each trial record (`YYYY-MM-DD`). No wall-clock time available → `What time is it right now?` and NY/Tokyo prompts are marked `ambiguous_ground_truth` rather than guessed.")
    lines.append("- **Datetime business-days arithmetic**: skipped weekends only; US federal holidays not modeled. The 200-business-day prompt is therefore reported with a note rather than treated as authoritative.")
    lines.append("- **Datetime date-appears matcher**: accepts ISO, `M/D/YYYY`, `M/D/YY`, `Month D, YYYY`, `Month D YYYY`, `D Month YYYY`, and bare `Month D`. Might over-credit a partial match like `January 18` when context made it ambiguous.")
    lines.append("- **Date-of-year-of-current-date** assumption: `days until December 31st of this year` uses `today.year`, where `today` is the trial date.")
    lines.append("- **Correct = tool_arg_correct OR prose_has_answer**: we don't distinguish \"got it via tool\" vs \"got it via in-head\" in the top-line `correct` bit, but both signals are present in the per-trial dict so downstream slicing is possible.")


    report_path.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
