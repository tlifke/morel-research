"""Step 2: parameterized diagnose on document."""
import re, argparse, json

def diagnose(document_path, categories_path=None, out_path=None):
    text=open(document_path).read()
    cats=json.load(open(categories_path)) if categories_path else ["Most Favored Nation","License Grant","Competitive Restriction Exception"]
    # Keyword mapping for common category-to-clause links (document-agnostic)
    kw = {"Most Favored Nation":["other sponsor","greater value","most favored"],
          "Competitive Restriction Exception":["endorsement","competition","exclusive"],
          "License Grant":["license","grant","assignment","intellectual property"],
          "Non-Transferable License":["non-transferable","transfer","assignment"]}
    clauses={}
    splits=re.split(r'\n(?=\d+\.|Section \d+\.)', text)
    for cat in cats:
        targets = kw.get(cat, [cat.lower()])
        snippets=[]
        for s in splits:
            s_low = s.lower()
            if any(t.lower() in s_low for t in targets):
                snippets.append(s[:400])
        clauses[cat]=snippets[:2] if snippets else ["(no direct clause match; search by keyword)"]
    if out_path: json.dump(clauses, open(out_path,"w"))
    return clauses

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--doc",required=True); ap.add_argument("--categories",default=None); ap.add_argument("--out",default=None)
    args=ap.parse_args()
    print(json.dumps(diagnose(args.doc,args.categories,args.out),indent=2))
