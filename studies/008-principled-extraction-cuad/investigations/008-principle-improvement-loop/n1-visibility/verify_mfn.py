import json
with open('studies/008-principled-extraction-cuad/investigations/008-principle-improvement-loop/runs/n1-principle-mfn/trials.jsonl') as f:
    d = json.load(f)
for dec in d['output']['decisions']:
    if dec['category'] == 'Most Favored Nation':
        print('kind:', dec['kind'])
        print('span (first 120 chars):', dec['spans'][0][:120])
        print('principles_cited:', dec.get('principles_cited'))
        print('explanation present?', bool(dec.get('explanation')))
