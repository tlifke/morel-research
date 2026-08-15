from __future__ import annotations

import argparse
import sys
import threading
import webbrowser
from pathlib import Path

import uvicorn

from . import record_types, sidecars
from .service import Config
from .server import create_app

APP_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = APP_DIR / "fixtures" / "candidates.sample.yaml"


def build_config(args: argparse.Namespace) -> Config:
    source = Path(args.source).expanduser().resolve()
    if not source.exists():
        sys.exit(f"candidates file not found: {source}")
    db = Path(args.db).expanduser().resolve() if args.db else APP_DIR / "state" / "review.sqlite3"
    export = (
        Path(args.export).expanduser().resolve()
        if args.export
        else source.with_name(source.stem + ".reviewed.yaml")
    )
    prefer = sidecars.round_subdirs(source)
    pairs = (
        Path(args.pairs).expanduser().resolve()
        if args.pairs
        else sidecars.discover(source.parent, sidecars.PAIR_NAMES, prefer)
    )
    footprint = (
        Path(args.footprint).expanduser().resolve()
        if args.footprint
        else sidecars.discover(source.parent, sidecars.FOOTPRINT_NAMES, prefer)
    )
    cross_source = (
        Path(args.cross_source).expanduser().resolve()
        if args.cross_source
        else sidecars.discover(source.parent, sidecars.CROSS_SOURCE_NAMES, prefer)
    )
    critiques = (
        Path(args.critiques).expanduser().resolve()
        if args.critiques
        else sidecars.discover(source.parent, sidecars.CRITIQUE_NAMES, prefer)
    )
    if args.pairs and not pairs.exists():
        sys.exit(f"pairs file not found: {pairs}")
    if args.footprint and not footprint.exists():
        sys.exit(f"footprint file not found: {footprint}")
    if args.cross_source and not cross_source.exists():
        sys.exit(f"cross-source file not found: {cross_source}")
    if args.critiques and not critiques.exists():
        sys.exit(f"critiques file not found: {critiques}")
    return Config(
        source=source,
        db=db,
        record_type=args.record_type,
        reviewer=args.reviewer,
        export_path=export,
        pairs_path=pairs,
        footprint_path=footprint,
        cross_source_path=cross_source,
        critiques_path=critiques,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="principle-review")
    parser.add_argument("source", nargs="?", default=str(DEFAULT_SOURCE))
    parser.add_argument("--record-type", default=record_types.DEFAULT_TYPE,
                        choices=sorted(record_types.REGISTRY))
    parser.add_argument("--reviewer", default="tyler")
    parser.add_argument("--db", default=None)
    parser.add_argument("--export", default=None)
    parser.add_argument("--pairs", default=None)
    parser.add_argument("--footprint", default=None)
    parser.add_argument("--cross-source", default=None)
    parser.add_argument("--critiques", default=None)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8823)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)

    config = build_config(args)
    app = create_app(config)
    url = f"http://{args.host}:{args.port}/"
    if not args.no_browser:
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
