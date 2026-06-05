import argparse
import json
from datetime import datetime
from pathlib import Path

from opentelemetry import trace as otel_trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

INFER = {
    "bash": "EXECUTE", "evaluate_predictions": "MEASURE", "read": "OBSERVE",
    "glob": "ORIENT", "write": "RECORD", "share_finding": "REPORT", "edit": "RECORD",
}
KIND = {
    "EXECUTE": "TOOL", "MEASURE": "TOOL", "OBSERVE": "TOOL", "RECORD": "TOOL",
    "ORIENT": "TOOL", "SUBSTRATE": "TOOL", "REASON": "LLM", "REPORT": "LLM",
    "INPUT": "AGENT", "END": "AGENT",
}


def ns(ts):
    if not ts:
        return None
    try:
        return int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() * 1e9)
    except ValueError:
        return None


def move_of(rec):
    k = rec["kind"]
    if k == "input":
        return "INPUT"
    if k == "thinking":
        return "REASON"
    if k == "tool_use":
        return rec.get("move") or INFER.get(rec.get("name", ""), "TOOL")
    if k == "tool_result":
        return "SUBSTRATE"
    if k == "assistant_text":
        return "REPORT"
    return "END"


def payload(rec):
    k = rec["kind"]
    if k == "tool_use":
        return json.dumps(rec.get("arguments", {}))
    return rec.get("text", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace")
    ap.add_argument("--endpoint", default="http://localhost:6006/v1/traces")
    ap.add_argument("--project", default="researcher-harness")
    args = ap.parse_args()

    records = [json.loads(l) for l in Path(args.trace).read_text().splitlines() if l.strip()]
    meta = next((r for r in records if r.get("kind") == "meta"), {})
    steps = [r for r in records if r.get("kind") != "meta"]

    provider = TracerProvider(resource=Resource.create({"service.name": args.project, "openinference.project.name": args.project}))
    provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint=args.endpoint)))
    tracer = provider.get_tracer("researcher-harness")

    times = [ns(r.get("ts")) for r in steps]
    valid = [t for t in times if t]
    root_start = valid[0] if valid else None
    root_end = valid[-1] if valid else None

    root = tracer.start_span(
        f"researcher-iteration · {meta.get('scenario', '')}".strip(" ·"),
        start_time=root_start,
        attributes={
            "openinference.span.kind": "AGENT",
            "model": meta.get("model", "?"),
            "substrate": meta.get("substrate", "?"),
            "scenario": meta.get("scenario", ""),
            "input.value": meta.get("first_user", ""),
        },
    )
    ctx = otel_trace.set_span_in_context(root)
    for i, rec in enumerate(steps):
        mv = move_of(rec)
        start = times[i]
        end = times[i + 1] if i + 1 < len(times) and times[i + 1] else start
        span = tracer.start_span(
            f"{mv}" + (f" · {rec.get('name')}" if rec.get("kind") == "tool_use" else ""),
            context=ctx,
            start_time=start,
            attributes={
                "openinference.span.kind": KIND.get(mv, "CHAIN"),
                "move": mv,
                "step.kind": rec["kind"],
                "input.value": payload(rec) if rec["kind"] in ("tool_use", "input") else "",
                "output.value": payload(rec) if rec["kind"] in ("tool_result", "assistant_text", "thinking") else "",
                "tool.name": rec.get("name", ""),
            },
        )
        span.end(end_time=end)

    root.end(end_time=root_end)
    provider.force_flush()
    print(f"ingested {len(steps)} move-spans from {args.trace} into Phoenix project '{args.project}'")


if __name__ == "__main__":
    main()
