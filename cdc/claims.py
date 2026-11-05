"""
Module 300 — claim extraction.

Both frontends normalise to the same intermediate form, a list of
(component, paragraph) pairs, and all sentence-level logic is shared.  A
sentence becomes a claim only when it asserts something checkable; prose that
merely introduces a section is not a claim and must not be scored as one.
"""

from __future__ import annotations

import hashlib
import re
from typing import List, Tuple

from .model import Claim, sub_tokens

ASSERTIVE_VERBS = frozenset({
    "uses", "use", "implements", "implement", "stores", "store", "encrypts",
    "encrypt", "validates", "validate", "returns", "return", "exposes",
    "expose", "parses", "parse", "computes", "compute", "generates",
    "generate", "handles", "handle", "provides", "provide", "sends", "send",
    "queries", "query", "caches", "cache", "signs", "sign", "verifies",
    "verify", "hashes", "hash", "rotates", "rotate",
})

LIB_LEXICON = {
    "aes": "cryptography", "gcm": "cryptography", "rsa": "cryptography",
    "sha256": "hashlib", "sha512": "hashlib", "md5": "hashlib",
    "hash": "hashlib", "hmac": "hmac", "json": "json", "regex": "re",
    "sql": "sqlite3", "database": "sqlite3", "http": "requests",
    "api": "flask", "endpoint": "flask", "route": "flask", "random": "secrets",
}

_HEADING = re.compile(r"^##+\s+(.+?)\s*$")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_CMD_ARG = re.compile(r"\\[A-Za-z]+\*?\{([^{}]*)\}")
_CMD = re.compile(r"\\[A-Za-z]+\*?")
_SECTION = re.compile(r"\\(?:sub)?section\{([^}]*)\}")


def extract_claims(text: str, fmt: str) -> list[Claim]:
    if fmt == "tex":
        pairs = _latex_pairs(text)
    else:
        pairs = _markdown_pairs(text)
    return _claims_from_pairs(pairs)


def _markdown_pairs(text: str) -> List[Tuple[str, str]]:
    return _pairs_from_markup(text)


def _latex_pairs(text: str) -> List[Tuple[str, str]]:
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("%")]
    normalised = "\n".join(lines)
    normalised = _SECTION.sub(lambda m: "\n## " + m.group(1) + "\n", normalised)
    while True:
        replaced = _CMD_ARG.sub(r"\1", normalised)
        if replaced == normalised:
            break
        normalised = replaced
    normalised = _CMD.sub("", normalised)
    normalised = re.sub(r"[ \t]+", " ", normalised)
    return _pairs_from_markup(normalised)


def _pairs_from_markup(text: str) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    component = ""
    buf: List[str] = []

    def flush() -> None:
        paragraph = re.sub(r"\s+", " ", " ".join(buf)).strip()
        if paragraph:
            pairs.append((component, paragraph))
        buf.clear()

    for line in text.splitlines():
        stripped = line.strip()
        match = _HEADING.match(stripped)
        if match:
            flush()
            component = match.group(1).strip()
            continue
        if stripped.startswith("#"):
            continue
        if not stripped:
            flush()
            continue
        buf.append(stripped)
    flush()
    return pairs


def _claims_from_pairs(pairs: List[Tuple[str, str]]) -> list[Claim]:
    claims: list[Claim] = []
    for component, paragraph in pairs:
        for sentence in _SENTENCE.split(paragraph):
            sentence = sentence.strip()
            if sentence and _is_assertive(sentence):
                claims.append(_claim(component, sentence))
    return claims


def _is_assertive(sentence: str) -> bool:
    tokens = [tok.lower() for tok in re.split(r"[^A-Za-z0-9]+", sentence) if tok]
    return any(tok in ASSERTIVE_VERBS for tok in tokens)


def _kind(sentence: str) -> str:
    lower = sentence.lower()
    if any(kw in lower for kw in ("module", "component", "layer", "service")):
        return "architecture"
    if any(kw in lower for kw in ("algorithm", "encrypt", "hash", "sort", "search")):
        return "algorithm"
    if any(kw in lower for kw in ("endpoint", "api", "route")):
        return "interface"
    if any(kw in lower for kw in ("table", "schema", "column", "database")):
        return "data"
    return "requirement"


def _claim(component: str, text: str) -> Claim:
    terms = frozenset(sub_tokens(text))
    implied_libs = frozenset(LIB_LEXICON[t] for t in terms if t in LIB_LEXICON)
    cid = "c" + hashlib.sha1((component + "|" + text).encode()).hexdigest()[:8]
    return Claim(
        cid=cid,
        component=component,
        text=text,
        kind=_kind(text),
        terms=terms,
        implied_libs=implied_libs,
        section=component,
    )
