"""Step 1: parameterized compare."""
import json, sys, argparse
GOLD = {"Document Name","Parties","Agreement Date","Effective Date","Expiration Date",
        "Governing Law","Insurance","Most Favored Nation","Non-Compete","Non-Disparagement",
        "Termination For Convenience","Anti-Assignment","Cap On Liability"}

def compare(trial_path, out_path=None):
    d=json.load(open(trial_path))
    pred={dec['category'] for dec in d['output']['decisions'] if dec['kind']=='extraction'}
    tp=len(pred&GOLD); fp=len(pred-GOLD); fn=len(GOLD-pred)
    R=tp/(tp+fn) if (tp+fn) else 0; P=tp/(tp+fp) if (tp+fp) else 0
    F1=2*P*R/(P+R) if (P+R) else 0; F2=5*P*R/(4*P+R) if (4*P+R) else 0
    res={"R":round(R,3),"P":round(P,3),"F1":round(F1,3),"F2":round(F2,3),
         "tp":tp,"fp":fp,"fn":fn,"pred":sorted(pred),"miss":sorted(GOLD-pred),"extra":sorted(pred-GOLD),
         "run_id":d.get("run_id"),"trial_id":d.get("key",{}).get("trial_id")}
    if out_path: json.dump(res, open(out_path,"w"))
    return res

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--trial", required=True); ap.add_argument("--out", default=None)
    args=ap.parse_args()
    print(compare(args.trial, args.out))
