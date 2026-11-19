"""Citation checker: proves every quote the model cites is really in the note.

Safety rule (brief §6, "Grounded answers", P0 #5): the model must cite a chunk
ID plus a short quote for every claim. This module checks in Python that each
quote appears in the chunk it names. Unverified citations are dropped, claims
left with no verified citation are dropped, and if nothing survives the answer
is NO_SUPPORT. The model's word is never trusted on this.

Called by qa.py (step 4) after the LLM replies. `chunks` must be exactly the
chunks that were put in that prompt, so the model cannot cite a chunk it never
saw. Pure functions, no I/O, no state: nothing here is stored.

Matching is exact after normalising harmless differences the model tends to
introduce: case, whitespace and line breaks, smart quotes and dashes, accents,
Markdown emphasis (* _ `), and "..." used to skip words. There is deliberately
no fuzzy matching: a paraphrase is not a quote.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Hashable, Mapping, Sequence

NO_SUPPORT = "No supporting notes found."

# Quotes shorter than this (after normalising, gaps excluded) are rejected:
# "the budget" appears in too many notes to prove anything.
MIN_QUOTE_CHARS = 15
# Each piece between "..." gaps must be at least this long, so a quote cannot
# be stitched together from scattered common words.
MIN_SEGMENT_CHARS = 8

_FOLD = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"', "″": '"',
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-",
    "―": "-", "−": "-",
}
_DROP = frozenset("*_`")
_GAP = "..."


@dataclass(frozen=True)
class Citation:
    chunk_id: Hashable
    quote: str


@dataclass(frozen=True)
class VerifiedCitation:
    chunk_id: Hashable
    quote: str
    # Character span in the original chunk text, from the first to the last
    # quoted character. Add the chunk's own offset to highlight it in the file.
    start: int
    end: int


@dataclass(frozen=True)
class RejectedCitation:
    chunk_id: Hashable
    quote: str
    reason: str  # "unknown_chunk" | "too_short" | "not_found"


@dataclass(frozen=True)
class Claim:
    text: str
    citations: Sequence[Citation]


@dataclass(frozen=True)
class VerifiedClaim:
    text: str
    citations: tuple[VerifiedCitation, ...]


@dataclass
class CheckedAnswer:
    claims: list[VerifiedClaim]
    rejected: list[RejectedCitation] = field(default_factory=list)

    @property
    def supported(self) -> bool:
        return bool(self.claims)

    @property
    def message(self) -> str | None:
        """Text to show instead of an answer, or None if there is one."""
        return None if self.claims else NO_SUPPORT


def _normalise(text: str) -> tuple[str, list[int]]:
    """Fold harmless differences away. Returns the folded text and, for each
    folded character, its index in `text` (so matches map back to the note)."""
    out: list[str] = []
    where: list[int] = []
    space = True  # also trims leading whitespace
    for i, ch in enumerate(text):
        if ch.isspace():
            if not space:
                out.append(" ")
                where.append(i)
                space = True
            continue
        # NFKD splits accents off and expands "…" to "...", so the accent can
        # be dropped per character with no whole-string pass.
        for c in unicodedata.normalize("NFKD", _FOLD.get(ch, ch)):
            if unicodedata.combining(c) or c in _DROP:
                continue
            for f in c.casefold():
                out.append(f)
                where.append(i)
            space = False
    if out and out[-1] == " ":
        out.pop()
        where.pop()
    return "".join(out), where


def _segments(quote: str) -> list[str]:
    q, _ = _normalise(quote)
    q = q.strip(" \"'")
    return [s.strip(" \"'") for s in q.split(_GAP) if s.strip(" \"'")]


def _is_boundary(text: str, i: int) -> bool:
    return i < 0 or i >= len(text) or not text[i].isalnum()


def _find(segments: list[str], text: str) -> tuple[int, int] | None:
    """Find every segment in order, each starting and ending on a word
    boundary. Returns the folded span covering all of them, or None.
    Taking the earliest hit for each segment is enough: an earlier hit never
    rules out a later segment that a later hit would allow."""
    start = cursor = 0
    for n, seg in enumerate(segments):
        hit = text.find(seg, cursor)
        while hit != -1 and not (_is_boundary(text, hit - 1) and _is_boundary(text, hit + len(seg))):
            hit = text.find(seg, hit + 1)
        if hit == -1:
            return None
        if n == 0:
            start = hit
        cursor = hit + len(seg)
    return start, cursor


def verify_citation(citation: Citation, chunks: Mapping[Hashable, str]) -> VerifiedCitation | RejectedCitation:
    text = chunks.get(citation.chunk_id)
    if text is None:
        return RejectedCitation(citation.chunk_id, citation.quote, "unknown_chunk")
    segments = _segments(citation.quote)
    if (sum(len(s) for s in segments) < MIN_QUOTE_CHARS
            or any(len(s) < MIN_SEGMENT_CHARS for s in segments)):
        return RejectedCitation(citation.chunk_id, citation.quote, "too_short")
    folded, where = _normalise(text)
    span = _find(segments, folded)
    if span is None:
        return RejectedCitation(citation.chunk_id, citation.quote, "not_found")
    return VerifiedCitation(citation.chunk_id, citation.quote, where[span[0]], where[span[1] - 1] + 1)


def check_answer(claims: Sequence[Claim], chunks: Mapping[Hashable, str]) -> CheckedAnswer:
    """Keep only claims backed by at least one verified citation."""
    kept: list[VerifiedClaim] = []
    rejected: list[RejectedCitation] = []
    for claim in claims:
        good: list[VerifiedCitation] = []
        for c in claim.citations:
            r = verify_citation(c, chunks)
            (good if isinstance(r, VerifiedCitation) else rejected).append(r)  # type: ignore[arg-type]
        if good:
            kept.append(VerifiedClaim(claim.text, tuple(good)))
    return CheckedAnswer(kept, rejected)
