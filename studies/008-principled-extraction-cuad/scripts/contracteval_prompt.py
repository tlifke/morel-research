SYSTEM_PROMPT = (
    "You are an assistant with strong legal knowledge, supporting senior lawyers "
    "by preparing reference materials.\n"
    "Given a Context and a Question, extract and return only the sentence(s) from "
    "the Context that directly address or relate to the Question.\n"
    "Do not rephrase or summarize in any way—respond with exact sentences from "
    "the Context relevant to the Question. If a relevant sentence contains "
    "unrelated elements such as page numbers or whitespace, include them exactly "
    "as they appear.\n"
    'If no part of the Context is relevant to the Question, respond with: "No '
    'related clause."\n'
)

USER_TEMPLATE = (
    "Context: \n```\n{context}\n```\nQuestion:\n```\n{question}\n```\n"
)

UPSTREAM_SOURCE = "github.com/olivialiu121/ContractEval @ main"
USER_TEMPLATE_SHA256 = "b4499e66a32921b38765661d69614692df719081adb8afd1e3ef77305eb28889"
SYSTEM_PROMPT_SHA256 = "d41b84571d05f3c2b2e07742d4f882132d469b3130ff778fe3b5d0e7925f9773"

DECLINATION = "no related clause"


def render(context: str, question: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TEMPLATE.format(context=context, question=question)},
    ]


def is_declination(raw: str) -> bool:
    return DECLINATION in (raw or "").strip(" \n`").lower()


def response_to_spans(raw: str) -> list[str]:
    if raw is None:
        return []
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    if is_declination(text):
        return []
    parts = [p.strip() for p in text.split("\n\n")]
    if len(parts) == 1:
        parts = [p.strip() for p in text.split("\n")]
    out = []
    for p in parts:
        p = p.strip()
        for prefix in ("- ", "* ", "• "):
            if p.startswith(prefix):
                p = p[len(prefix) :].strip()
        if p:
            out.append(p)
    return out or ([text.strip()] if text.strip() else [])
