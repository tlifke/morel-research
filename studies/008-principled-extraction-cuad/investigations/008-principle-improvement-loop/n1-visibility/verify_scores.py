"""Category-level R/P/F1/F2 for n=1 vs gold (mvp_slice positive set). Full span-level needs harness.is_match."""
import json
GOLD = {"Document Name","Parties","Agreement Date","Effective Date","Expiration Date",
"Governing Law","Insurance","Most Favored Nation","Non-Compete","Non-Disparagement",
"Termination For Convenience","Anti-Assignment","Cap On Liability"}

def score(trial_path):
    with open(trial_path) as f:
        d=json.load(f)
    pred = {dec['category'] for dec in d['output']['decisions'] if dec['kind']=='extraction'}
    tp = len(pred & GOLD); fp = len(pred - GOLD); fn = len(GOLD - pred)
    R = tp/(tp+fn) if (tp+fn) else 0
    P = tp/(tp+fp) if (tp+fp) else 0
    F1 = 2*P*R/(P+R) if (P+R) else 0
    F2 = 5*P*R/(4*P+R) if (4*P+R) else 0
    return {"R":round(R,3),"P":round(P,3),"F1":round(F1,3),"F2":round(F2,3),
            "tp":tp,"fp":fp,"fn":fn,"pred_n":len(pred)}

for label, path in [
    ("empty", "studies/008-principled-extraction-cuad/investigations/008-principle-improvement-loop/runs/n1-live-empty/trials.jsonl"),
    ("mfn", "studies/008-principled-extraction-cuad/investigations/008-principle-improvement-loop/runs/n1-principle-mfn/trials.jsonl")
]:
    print(label, score(path))
