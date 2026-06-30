import html
import json
import sys
from pathlib import Path

import render_society as rs

INK, MUT, LINE, BG = "#111827", "#64748b", "#e5e7eb", "#f8fafc"


def esc(s):
    return html.escape(str(s if s is not None else ""))


def region_grid(reg):
    mx = max(reg.values()) or 1
    def cell(key, corner=False):
        v = reg.get(key, 0)
        t = v / mx
        bg = "#%02x%02x%02x" % (round(255 - t * 131), round(255 - t * 197), round(255 - t * 18))
        bd = "border:2px solid #0d9488" if corner else f"border:1px solid {LINE}"
        tag = "<div style='font-size:9px;color:#0d9488'>corner</div>" if corner else ""
        return f'<td style="{bd};background:{bg};text-align:center;padding:7px 12px;font-weight:700">{v}{tag}</td>'
    return ('<table style="border-collapse:collapse;font-size:12px;margin:4px 0">'
            f'<tr><td></td><td style="color:{MUT};font-size:10px;text-align:center">low bs</td><td style="color:{MUT};font-size:10px;text-align:center">high bs</td></tr>'
            f'<tr><td style="color:{MUT};font-size:10px">high lr</td>{cell("HL")}{cell("HH", True)}</tr>'
            f'<tr><td style="color:{MUT};font-size:10px">low lr</td>{cell("LL")}{cell("LH")}</tr></table>')


def card(run):
    summ = json.load(open(run / "loop_summary.json"))
    steps = json.load(open(run / "steps.json")) if (run / "steps.json").exists() else {}
    tr = summ["trajectory"]
    cfg = summ.get("config", {})
    reg = summ.get("regions", {})
    hl = [h for h in (steps.get("hyp_ledger") or []) if h.get("level") == "high"]
    title = {"correct": "Seed: 1 CORRECT hypothesis", "4regions": "Seed: 4 region hypotheses"}.get(cfg.get("hyp_seed"), "Capped generation (no seed)")
    frozen = " · frozen" if cfg.get("hyp_freeze") else ""
    dlr, dbs = len({t["lr"] for t in tr}), len({t["bs"] for t in tr})
    mxlr = max((t["lr"] for t in tr), default=0)
    corner = "✅" if summ["reached_corner"] else "❌"
    hyp_html = "".join(f'<li>{esc(h.get("claim"))} <span style="color:{MUT}">[{esc(h.get("status"))}]</span></li>' for h in hl) or "<li style='color:#64748b'>(none)</li>"
    return f'''<div style="background:white;border:1px solid {LINE};border-radius:12px;padding:14px;width:500px">
      <div style="font-weight:800;font-size:14px">{esc(title)}{esc(frozen)}</div>
      <div style="color:{MUT};font-size:12px;margin-bottom:6px">budget {summ["budget"]} · caps {cfg.get("max_high")}H/{cfg.get("max_narrow_per")}N · {summ["model_calls"]} calls</div>
      {rs.grid_svg(tr)}
      <div style="display:flex;gap:16px;align-items:flex-start;margin-top:8px">
        <div style="font-size:12px">
          <div>reached corner: <b>{corner}</b></div>
          <div>final regret: <b>{summ["final_regret"]:.4f}</b></div>
          <div>distinct lr/bs: <b>{dlr}/{dbs}</b> · max lr <b>{mxlr:.2e}</b></div>
          <div>best: <span style="font-family:ui-monospace,monospace">lr {summ["best_config"]["lr"]:.2e} · bs {summ["best_config"]["bs"]}</span></div>
        </div>
        <div><div style="font-size:10px;color:{MUT}">experiments per region</div>{region_grid(reg)}</div>
      </div>
      <div style="font-size:11px;color:{MUT};margin-top:8px;text-transform:uppercase;letter-spacing:.04em">high-level hypotheses</div>
      <ul style="font-size:12px;margin:4px 0;padding-left:18px">{hyp_html}</ul>
    </div>'''


def main(dirs):
    cards = "".join(card(Path(d)) for d in dirs)
    H = f'''<!doctype html><html><head><meta charset="utf-8"><title>Society — run comparison</title>
<style>body{{margin:0;background:{BG};color:{INK};font-family:ui-sans-serif,system-ui,sans-serif}}
.wrap{{max-width:1090px;margin:0 auto;padding:26px 22px 70px}} h1{{font-size:21px;margin:0 0 4px}}
.row{{display:flex;flex-wrap:wrap;gap:14px}}</style></head><body><div class="wrap">
<h1>Society — diagnostic comparison</h1>
<div style="color:{MUT};font-size:13px;margin-bottom:16px">Each panel: regret-heatmap grid (green=optimum, red=worst), region-coverage 2×2 (the high-lr/high-bs corner is the optimum region), and the governing high-level hypotheses. Read the grids and region tables directly.</div>
<div class="row">{cards}</div></div></body></html>'''
    out = Path(dirs[0]).parent / "compare_diagnostic.html"
    out.write_text(H)
    print(f"wrote {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
