#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "pillow"]
# ///
"""Capture a rendered UI as PNGs for visual critique.

Target may be a URL (dev server) or a local file path (static HTML, Plotly
export). Writes full-page PNGs to --out, tiling anything taller than --tile,
and prints the written paths one per line.
"""
import argparse
import io
import pathlib
import sys


def resolve(target: str) -> str:
    if "://" in target:
        return target
    p = pathlib.Path(target).expanduser().resolve()
    if not p.exists():
        sys.exit(f"target not found: {p}")
    return p.as_uri()


def load_js(js: str | None) -> str | None:
    if not js:
        return None
    p = pathlib.Path(js).expanduser()
    if p.exists() and p.is_file():
        return p.read_text()
    return js


def tile(png: bytes, out: pathlib.Path, label: str, height: int, limit: int) -> list[pathlib.Path]:
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(io.BytesIO(png))
    w, h = im.size
    if h <= height:
        dest = out / f"{label}.png"
        im.save(dest)
        return [dest]
    tops = list(range(0, h, height))
    if len(tops) > limit:
        print(
            f"note: {label} is {h}px tall = {len(tops)} tiles; keeping first {limit}",
            file=sys.stderr,
        )
        tops = tops[:limit]
    paths = []
    for i, top in enumerate(tops, start=1):
        dest = out / f"{label}-{i:02d}.png"
        im.crop((0, top, w, min(top + height, h))).save(dest)
        paths.append(dest)
    return paths


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="URL or local file path")
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--js", help="JS snippet or path to a .js file, run before capture")
    ap.add_argument("--tile", type=int, default=2000)
    ap.add_argument("--label", default="shot")
    ap.add_argument("--max-tiles", type=int, default=6)
    ap.add_argument("--wait", type=int, default=0, help="extra ms to wait after load")
    args = ap.parse_args()

    url = resolve(args.target)
    script = load_js(args.js)
    out = pathlib.Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("playwright not available; run this with: uv run capture.py ...")

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": args.width, "height": 1200})
        try:
            page.goto(url, wait_until="networkidle", timeout=60_000)
        except Exception:
            page.goto(url, wait_until="load", timeout=60_000)
        if script:
            page.evaluate(script)
        if args.wait:
            page.wait_for_timeout(args.wait)
        height = page.evaluate("document.documentElement.scrollHeight")
        width = page.evaluate("document.documentElement.scrollWidth")
        if width > args.width:
            print(
                f"note: content overflows horizontally ({width}px wide at a "
                f"{args.width}px viewport); capturing what a reader sees",
                file=sys.stderr,
            )
        png = page.screenshot(
            full_page=True,
            clip={"x": 0, "y": 0, "width": args.width, "height": height},
        )
        browser.close()

    for path in tile(png, out, args.label, args.tile, args.max_tiles):
        print(path)


if __name__ == "__main__":
    main()
