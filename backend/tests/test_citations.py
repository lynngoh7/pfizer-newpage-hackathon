from pathlib import Path

from app.citations import (
    NO_SUPPORT, Citation, Claim, RejectedCitation, VerifiedCitation, check_answer, verify_citation,
)

SAMPLES = Path(__file__).resolve().parents[2] / "sample_notes"

CHUNKS = {
    "c1": "## Decision\n**We're dropping Corvid and switching to Ledgerly (UK-hosted, London region).**\r\n"
          "This replaces the 22 Sep decision.",
    "c2": "Budget: Nadia says ~£40k available for Lighthouse in Q4, “don't plan on more”.",
    "c3": "Croeso i Lighthouse — dechreuwch yma",
}


def ok(chunk_id, quote, chunks=CHUNKS) -> VerifiedCitation:
    r = verify_citation(Citation(chunk_id, quote), chunks)
    assert isinstance(r, VerifiedCitation), r
    return r


def rejected(chunk_id, quote, chunks=CHUNKS) -> str:
    r = verify_citation(Citation(chunk_id, quote), chunks)
    assert isinstance(r, RejectedCitation), r
    return r.reason


def test_exact_quote_and_span_points_at_the_note():
    r = ok("c1", "switching to Ledgerly")
    assert CHUNKS["c1"][r.start:r.end] == "switching to Ledgerly"


def test_harmless_differences_are_ignored():
    ok("c1", "we're dropping corvid and switching to ledgerly")      # case + markdown bold
    ok("c1", "London region).\nThis replaces the 22 Sep decision")    # CRLF vs \n, dropped **
    ok("c1", "\"We’re dropping Corvid\"")                             # surrounding + smart quotes
    ok("c2", "\"don't plan on more\" ")                               # smart double quotes in note
    ok("c3", "Croeso i Lighthouse - dechreuwch yma")                  # em dash vs hyphen
    ok("c3", "Croeso i Lighthouse — dechreuwch yma".replace("e", "é", 1))  # stray accent


def test_ellipsis_gaps_must_be_in_order():
    r = ok("c1", "dropping Corvid ... the 22 Sep decision")
    assert CHUNKS["c1"][r.start:r.end].startswith("dropping Corvid")
    assert CHUNKS["c1"][r.start:r.end].endswith("decision")
    ok("c1", "dropping Corvid … the 22 Sep decision")                 # unicode ellipsis
    assert rejected("c1", "the 22 Sep decision ... dropping Corvid") == "not_found"


def test_fabricated_or_paraphrased_quote_is_rejected():
    assert rejected("c1", "We decided to switch to Ledgerly") == "not_found"
    assert rejected("c2", "Nadia says ~£30k available") == "not_found"


def test_real_quote_from_the_wrong_chunk_is_rejected():
    assert rejected("c2", "switching to Ledgerly") == "not_found"


def test_chunk_not_in_the_prompt_is_rejected():
    assert rejected("c99", "switching to Ledgerly") == "unknown_chunk"


def test_trivial_quotes_are_rejected():
    assert rejected("c1", "Corvid") == "too_short"
    assert rejected("c1", "the 22 ... decision") == "too_short"  # stitched from scraps


def test_quote_must_not_start_or_end_mid_word():
    assert rejected("c1", "witching to Ledgerl") == "not_found"


def test_claims_keep_only_verified_citations():
    answer = check_answer([
        Claim("We switched to Ledgerly.", [Citation("c1", "switching to Ledgerly"),
                                           Citation("c2", "switching to Ledgerly")]),
        Claim("Ledgerly is free.", [Citation("c1", "Ledgerly is free of charge")]),
    ], CHUNKS)
    assert answer.supported and answer.message is None
    assert [c.text for c in answer.claims] == ["We switched to Ledgerly."]
    assert [c.chunk_id for c in answer.claims[0].citations] == ["c1"]
    assert len(answer.rejected) == 2


def test_nothing_verified_means_no_supporting_notes():
    answer = check_answer([Claim("The office moves in March.", [Citation("c1", "office moves in March")])], CHUNKS)
    assert not answer.supported
    assert answer.message == NO_SUPPORT
    assert check_answer([], CHUNKS).message == NO_SUPPORT


def test_against_a_real_sample_note():
    text = (SAMPLES / "meetings" / "2026-10-20 Lighthouse vendor rethink.md").read_text(encoding="utf-8")
    r = ok("n", "Beta moves from 3 Nov to 17 Nov", {"n": text})
    assert text[r.start:r.end] == "Beta moves from 3 Nov to **17 Nov"
