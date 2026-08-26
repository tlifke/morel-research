"""Generalized n=1 verifier: given trial_path, gold_set, target_category, prints R/P/F1/F2 + target status."""
import json, sys, os

def verify(trial_path, gold_path_or_set, target_cat, principle_name=""):
    # gold can be path to mvp_slice or set
    if isinstance(gold_path_or_set, str) and os.path.exists(gold_path_or_set):
        gold = {c["contract_id"] for c in json.load(open(gold_path_or_set))}  # not used directly; use hard gold for GAINSCO
    # For this study: gold positive categories from mvp_slice for GAINSCO
    GOLD = {"Document Name","Parties","Agreement Date","Effective Date","Expiration Date",
            "Governing Law","Insurance","Most Favored Nation","Non-Compete","Non-Disparagement",
            "Termination For Convenience","Anti-Assignment","Cap On Liability"}
    with open(trial_path) as f: d=json.load(f)
    pred = {dec['category'] for dec in d['output']['decisions'] if dec['kind']=='extraction'}
    tp=len(pred&GOLD); fp=len(pred-GOLD); fn=len(GOLD-pred)
    R=tp/(tp+fn) if (tp+fn) else 0; P=tp/(tp+fp) if (tp+fp) else 0
    F1=2*P*R/(P+R) if (P+R) else 0; F2=5*P*R/(4*P+R) if (4*P+R) else 0
    target_present = target_cat in pred
    target_cited = any(dec.get('principles_cited') for dec in d['output']['decisions'] if dec['category']==target_cat)
    print(f"{principle_name:20s} R={R:.2f} P={P:.2f} F1={F1:.2f} F2={F2:.2f} | {target_cat} present={target_present} cited={target_cited} (tp={tp} fp={fp} fn={fn})")

# Compare all three + empty
base = "studies/008-principled-extraction-cuad/investigations/008-principle-improvement-loop/runs"
verify(base+"/n1-live-empty/trials.jsonl", None, "Most Favored Nation", "empty")
verify(base+"/n1-principle-mfn/trials.jsonl", None, "Most Favored Nation", "mfn")
verify(base+"/n1-principle-no-infer-competitive/trials.jsonl", None, "Competitive Restriction Exception", "no-infer-competitive")
verify(base+"/n1-principle-license-vs-sponsorship/trials.jsonl", None, "License Grant", "license-vs-sponsorship")
