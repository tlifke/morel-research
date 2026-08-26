"""Step 3: parameterized derive via Tinker; provenance fixed."""
import sys,os,json,argparse
sys.path.insert(0,"studies/008-principled-extraction-cuad")
sys.path.insert(0,"studies/008-principled-extraction-cuad/investigations/008-principle-improvement-loop")
from harness.backends.tinker_backend import TinkerBackend

def derive(discrepancy_path, snippet_path, out_path, model="Qwen/Qwen3.5-9B"):
    d=json.load(open(discrepancy_path))
    snippet=open(snippet_path).read() if snippet_path else ""
    backend=TinkerBackend(model=model, separate_reasoning=True, top_p=0.95)
    prompt=f"Errors: {d.get('miss',[])} + hallucinated: {d.get('extra',[])}\nClues:\n{snippet}\nReturn JSON principle with provenance='ground_truth_derived', version (e.g. 'derived-001'), id, statement, type (constraint/procedure/preference/disambiguation/absence/other), target_categories (list), citation_required (bool), trigger_guidance (string)."
    res=backend.sample([{"role":"user","content":prompt}], None, 1.0, 0, 32768)
    text=res.text; start=text.find("{"); end=text.rfind("}")
    data=json.loads(text[start:end+1]) if start!=-1 and end!=-1 else {}
    data["provenance"]="ground_truth_derived"
    if "version" not in data or not data.get("version"):
        data["version"]="derived-001"
    open(out_path,"w").write(json.dumps(data,indent=2))
    return data, res.text

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--discrepancy",required=True); ap.add_argument("--snippet",default=None); ap.add_argument("--out",required=True); ap.add_argument("--model",default="Qwen/Qwen3.5-9B")
    args=ap.parse_args()
    print(json.dumps(derive(args.discrepancy,args.snippet,args.out,args.model)[0],indent=2))
