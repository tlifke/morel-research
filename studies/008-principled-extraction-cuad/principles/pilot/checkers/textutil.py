import re
import unicodedata
from functools import lru_cache

SENTENCE_SPLIT = re.compile(r"(?<=[.;])\s+|\n\s*\n")


def sentences(text):
    out = []
    start = 0
    for match in SENTENCE_SPLIT.finditer(text):
        end = match.start()
        if end > start:
            out.append((start, end, text[start:end]))
        start = match.end()
    if start < len(text):
        out.append((start, len(text), text[start:]))
    return out


@lru_cache(maxsize=64)
def cached_sentences(text):
    return tuple(sentences(text))


def normalise(text):
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = re.sub(r"[‐-―]", "-", text)
    text = re.sub(r"-\n\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def sentence_containing(text, offset):
    for start, end, body in cached_sentences(text):
        if start <= offset < end:
            return start, end, body
    return None


def any_sentence_matches(text, *patterns, window=None):
    body = text if window is None else text[:window]
    for _, _, sentence in cached_sentences(body):
        if all(pattern.search(sentence) for pattern in patterns):
            return True
    return False


def near(pattern_a, pattern_b, text, distance):
    for match in pattern_a.finditer(text):
        lo = max(0, match.start() - distance)
        hi = min(len(text), match.end() + distance)
        if pattern_b.search(text[lo:hi]):
            return True
    return False


def signature_block(text, tail=3000):
    return text[-tail:]
