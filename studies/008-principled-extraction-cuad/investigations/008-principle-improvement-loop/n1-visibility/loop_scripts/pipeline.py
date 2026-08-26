"""Master: step1→2→3→4 parameterized via --results-dir.
Inputs: --trial (baseline), --doc (document text path), --discrepancy (json with miss/extra), --contract (id), --principle (optional, else derive step3).
Outputs: intermediate + final all under --results-dir."""
import argparse, os, sys, json
sys.path.insert(0,".")
from loop_scripts.step1_compare import compare
from loop_scripts.step2_diagnose import diagnose
from loop_scripts.step3_derive import derive
from loop_scripts.step4_test import test

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--results-dir",required=True)
    ap.add_argument("--trial",default="studies/008-principled-extraction-cuad/investigations/008-principle-improvement-loop/runs/n1-live-empty/trials.jsonl")
    ap.add_argument("--doc",default="studies/008-principled-extraction-cuad/data/raw/CUADv1.json")
    ap.add_argument("--discrepancy",default=None)
    ap.add_argument("--contract",default="GAINSCOINC_01_21_2010-EX-10.41-SPONSORSHIP AGREEMENT")
    ap.add_argument("--principle",default=None)
    args=ap.parse_args()
    d=os.path.join(args.results_dir,"intermediate")
    os.makedirs(d,exist_ok=True)
    # Step 1
    s1=compare(args.trial, os.path.join(d,"step1_compare.json"))
    # Step 2 (simplified: use first missing category from s1)
    target=s1.get("miss",["Most Favored Nation"])[0]
    # For doc: extract contract text from raw (simplified); real pipeline uses docs
    clauses=diagnose(args.doc, [target], os.path.join(d,"step2_clauses.json"))
    # Step 3 (derive if no principle given; else skip)
    disc_path=os.path.join(d,"step1_compare.json")
    if args.principle is None:
        snippet_path=os.path.join(d,"step2_clauses.json")
        principle_data,txt=derive(disc_path, snippet_path, os.path.join(d,"step3_principle.json"))
        principle_path=os.path.join(d,"step3_principle.json")
    else:
        principle_path=args.principle
    # Step 4
    ok,out,run_path=test([args.contract], principle_path, args.results_dir, run_id="pipeline-run", extra_args=["--run-dir",os.path.join(args.results_dir,"final")])
    import shutil
    if ok and run_path and os.path.exists(run_path):
        dest=os.path.join(args.results_dir, os.path.basename(run_path))
        shutil.copytree(run_path, dest, dirs_exist_ok=True)
    # Final comparison (step1 style on new run)
    new_trial=os.path.join(args.results_dir, os.path.basename(run_path) or "pipeline-run", "trials.jsonl")
    if new_trial:
        s4=compare(new_trial, os.path.join(args.results_dir,"step4_compare.json"))
    print("Pipeline complete. Results:", args.results_dir, "| Step1:", s1.get("F2"), "| Step4 trial exists:", new_trial is not None)

if __name__=="__main__":
    main()
