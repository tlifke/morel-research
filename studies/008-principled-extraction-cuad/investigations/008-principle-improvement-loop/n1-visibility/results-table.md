# n=1 principle comparison — GAINSCOINC sponsorship agreement

| Arm | Target category | Target present | Cited | R | P | F1 | F2 | tp/fp/fn | Verdict (n=1) |
|---|---|---|---|---|---|---|---|---|---|
| empty | Most Favored Nation | No | No | 0.92 | 0.80 | 0.86 | 0.90 | 12/3/1 | Baseline; missing target |
| mfn | Most Favored Nation | **Yes** | **Yes** | 1.00 | 0.65 | 0.79 | 0.90 | 13/7/0 | **Working on target**; precision cost |
| no-infer-competitive | Competitive Restriction Exception | No | No | 0.92 | 0.92 | 0.92 | 0.92 | 12/1/1 | **Not working**; target still absent (needs absence directive) |
| license-vs-sponsorship | License Grant | **Yes** | **Yes** | 1.00 | 0.81 | 0.90 | 0.96 | 13/3/0 | **Strongest**; high F2, cited, precise |

Notes:
- Gold positive for this contract (from mvp_slice): 13 categories.
- Metric definition: category-level R/P/F1/F2 vs gold set (full span-level needs harness.is_match).
- Cited = `principles_cited` non-empty in trial output.
- Recommendation for ladder: test mfn + license-vs-sponsorship with 3 repeats; redesign no-infer-competitive as absence rule.
