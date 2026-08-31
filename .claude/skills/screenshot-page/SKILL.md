---
name: screenshot-page
description: Render a web page to PNGs so you can actually look at it. Use whenever you need to see what something looks like rather than reason about its source — after building or editing an HTML page, a Plotly dashboard, a React/Next.js view or any figure; when checking whether a layout, style or fix actually worked; when a user asks "what does it look like", "is it rendering right", "screenshot the page", "look at the page", "check the rendering", "see how it turned out". Works on a local file path or a URL on a dev server. You cannot see a page by reading its markup — render it and read the image.
---

# screenshot-page

You have no browser. Reading HTML or JSX tells you nothing about what renders —
clipped text, overlapping elements, a stylesheet that failed to load and wrong
visual nesting are all invisible in source. This skill turns a page into PNGs
you can look at with `read`.

## The two steps

```bash
uv run capture.py \
  --target <url-or-path> --out <dir> --label shot
```

Then **`read` the PNG paths it prints.** That is the point — capturing without
reading accomplishes nothing. `read` sends images as attachments, so you see the
page directly.

`--target` takes a local file path (`./view.html`, an exported figure) or a URL
(`http://localhost:3000/page` — start the dev server first).

## Seeing hidden content

If content is behind interaction, capture a second state. `--js` runs before the
screenshot:

```bash
uv run capture.py \
  --target ./view.html --out /tmp/cap --label expanded \
  --js "document.querySelectorAll('details').forEach(d=>d.open=true)"
```

Use it to expand collapsed sections, open a tab, dismiss a cookie banner or
overlay. **Always do this when content is collapsed by default** — otherwise you
are looking at a stack of closed bars and learning nothing about what is inside
them.

## Flags

| Flag | Default | Notes |
|---|---|---|
| `--target` | required | file path or URL |
| `--out` | required | directory for PNGs |
| `--label` | `shot` | filename stem; use it to distinguish states |
| `--width` | `1280` | viewport width; drop it to check responsive layout |
| `--js` | — | JS snippet, or path to a `.js` file, run before capture |
| `--wait` | `0` | extra ms after load, for slow apps |
| `--tile` | `2000` | tall pages are sliced into `-01`, `-02`, … |
| `--max-tiles` | `6` | cap; it tells you on stderr when it drops tiles |

## Reading the output

**Check stderr.** Two messages matter:

- `content overflows horizontally (Npx wide at a 1280px viewport)` — the page is
  wider than the viewport. That is a real defect, not a capture artifact. The
  capture deliberately clips to the viewport so you see what a reader sees, with
  the cut-off visible, rather than zooming out to fit.
- `... = N tiles; keeping first N` — the page was too tall to capture fully and
  content was dropped. Say so rather than reporting on a page you only half saw.

Tall pages arrive as several PNGs. Read them in order; they are consecutive
vertical slices of one page.

## Requirements

Playwright drives your installed Chrome (`channel="chrome"`), so no browser
download is needed — but Chrome must be installed.

**Your model must support image input.** If it does not, `read` silently omits
the image and substitutes `[Current model does not support images...]`. If you
see that note, stop and tell the user — their model's `input` array in
`models.json` needs `"image"` added. Do not carry on as if you had seen the page.
