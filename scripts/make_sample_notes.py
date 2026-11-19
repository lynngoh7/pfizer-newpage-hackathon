"""Generate the non-text files in sample_notes/ and set file dates.

The .md/.txt notes are written by hand and committed as-is. This script makes
the files that are awkward to hand-write (.docx, .pdf, .png, symlinks, odd
encodings, a very long log) and sets each note's modified time to the date it
was "written", because git does not keep file dates.

Run from the repo root after cloning or pulling:
    pip install pymupdf python-docx      # any venv; dev-only, not app deps
    python scripts/make_sample_notes.py

Safe to re-run: it overwrites only the files it generates.
"""

import os
import time
from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF
from docx import Document

ROOT = Path(__file__).resolve().parent.parent / "sample_notes"


def leadership_docx() -> None:
    d = Document()
    d.add_heading("Leadership sync — 14 October 2026", 0)
    d.add_paragraph("Attendees: CPO, Finance (Nadia Shah), Heads of Product, Eng, Ops")
    d.add_heading("1. Q4 spend", 1)
    d.add_paragraph(
        "Company-wide Q4 discretionary spend is being tightened after the Q3 results. "
        "Each programme was reviewed line by line."
    )
    t = d.add_table(rows=1, cols=3)
    t.style = "Table Grid"
    for c, h in zip(t.rows[0].cells, ["Programme", "Q4 allocation (was)", "Q4 allocation (now)"]):
        c.text = h
    for row in [("Lighthouse (onboarding)", "£40k", "£30k"),
                ("Helpdesk revamp", "£25k", "£25k"),
                ("Data platform", "£60k", "£45k")]:
        cells = t.add_row().cells
        for c, v in zip(cells, row):
            c.text = v
    d.add_paragraph(
        "Lighthouse: funding reduced to £30k for Q4. Programme leads to re-plan within the new figure "
        "and report back by end of October."
    )
    d.add_heading("2. Hiring", 1)
    d.add_paragraph("No change to permanent hiring. Contractor spend to be reviewed again in November.")
    d.add_heading("3. AOB", 1)
    d.add_paragraph("Offsite moved to 9 October (already happened — note for the record).")
    d.save(ROOT / "docs" / "2026-10-14 Leadership sync.docx")


def ledgerly_pdf() -> None:
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((72, 80), "Ledgerly - Proposal for Kestrel Labs", fontsize=18)
    p1.insert_textbox(fitz.Rect(72, 110, 520, 700), (
        "Prepared for: Rory Doyle, Kestrel Labs\nDate: 16 October 2026\n\n"
        "1. Overview\n"
        "Ledgerly provides product analytics with a UK-hosted region (London). "
        "All event data for UK-plan customers stays in the UK.\n\n"
        "2. Integration\n"
        "Typical integration is 3-4 weeks including single sign-on (SSO). "
        "SSO alone usually takes 1-2 weeks.\n\n"
        "See page 2 for pricing."
    ), fontsize=11)
    p2 = doc.new_page()
    p2.insert_text((72, 80), "3. Pricing", fontsize=14)
    p2.insert_textbox(fitz.Rect(72, 100, 520, 700), (
        "List price: £28,000 per year (UK plan, up to 50k monthly users).\n\n"
        "Offer: £26,500 per year if the contract is signed by 31 October 2026.\n\n"
        "Minimum term: 12 months."
    ), fontsize=11)
    doc.save(ROOT / "docs" / "Ledgerly proposal.pdf")


def text_image(lines: list[str], width=520, height=220, fontsize=13) -> fitz.Pixmap:
    """Render lines of text to an image (no text layer survives)."""
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    page.draw_rect(page.rect, color=None, fill=(1, 1, 1))
    y = 30
    for line in lines:
        page.insert_text((20, y), line, fontsize=fontsize)
        y += fontsize + 9
    return page.get_pixmap(dpi=144)


def slack_screenshot() -> None:
    pix = text_image([
        "#lighthouse-team                                    Mon 10 Nov",
        "",
        "Ollie Barnes  10:42",
        "heads up - Ledgerly SSO is taking longer than their FAQ said.",
        "realistically beta is 24 Nov, not 17th. will confirm Weds",
        "",
        "Hattie Moss  10:45",
        "ugh ok. consent screen is ready whenever",
    ])
    pix.save(ROOT / "screenshots" / "2026-11-10 slack Ollie.png")


def scanned_pdf() -> None:
    """A PDF that is only an image: no text layer. Needs OCR to read."""
    pix = text_image(["RECEIPT - Offsite catering", "9 Oct 2026", "Total: £412.50"], height=120)
    doc = fitz.open()
    page = doc.new_page()
    page.insert_image(fitz.Rect(50, 50, 550, 170), stream=pix.tobytes("png"))
    doc.save(ROOT / "edge_cases" / "scanned receipt.pdf", deflate=True)


def locked_pdf() -> None:
    doc = fitz.open()
    doc.new_page().insert_text((72, 80), "Salary bands 2027 (password protected)")
    doc.save(ROOT / "edge_cases" / "password protected.pdf",
             encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="fake-test-pw", owner_pw="fake-test-pw")


def odd_files() -> None:
    e = ROOT / "edge_cases"
    (e / "corrupt.pdf").write_bytes(b"%PDF-1.7\n" + bytes(range(256)) * 4 + b"\n(truncated")
    # Latin-1 bytes + Windows line endings: not valid UTF-8.
    (e / "latin1 windows.txt").write_bytes(
        "Café catch-up w/ Zoë from Wexcombe — they want the pilot extended to March. Naïve?\r\nCost: £0\r\n"
        .replace("—", "-").encode("latin-1"))
    # ~150 KB of routine standups with one real decision buried in the middle.
    lines = ["# Daily standup log (Lighthouse) — Sep to Nov 2026", ""]
    for i in range(900):
        lines += [f"## Standup {i + 1}", "- Ollie: integration work continuing, no blockers",
                  "- Hattie: design reviews, nothing new", "- Rory: vendor admin", ""]
        if i == 450:
            lines += ["- DECISION: the beta will be called 'Lighthouse Preview' in customer comms, "
                      "to avoid confusion with the Lighthouse meeting room.", ""]
    (e / "long standup log.md").write_text("\n".join(lines), encoding="utf-8")


def symlinks() -> None:
    e = ROOT / "edge_cases"
    for name, target in [("escape link.md", "../../README.md"),  # points outside sample_notes
                         ("loop", "..")]:                         # walking into it never ends
        link = e / name
        if link.is_symlink() or link.exists():
            link.unlink()
        os.symlink(target, link)


# Modified time = when the note was "written". Everything else keeps today's date.
DATES = {
    "meetings/2026-09-08 Lighthouse kickoff.md": "2026-09-08 17:10",
    "meetings/2026-09-15 hiring plan.md": "2026-09-15 10:05",
    "meetings/2026-09-22 Lighthouse vendor decision.md": "2026-09-22 15:30",
    "meetings/2026-10-01 team weekly.md": "2026-10-01 11:00",
    "1on1s/2026-10-06 Ollie 1on1.txt": "2026-10-06 14:20",
    "docs/2026-10-14 Leadership sync.docx": "2026-10-14 16:45",
    "1on1s/2026-10-15 Nadia 1on1.txt": "2026-10-15 12:10",
    "docs/Ledgerly proposal.pdf": "2026-10-16 09:00",
    "inbox/fwd Ledgerly FAQ.txt": "2026-10-17 08:30",
    "meetings/2026-10-20 Lighthouse vendor rethink.md": "2026-10-20 16:00",
    "personal/2026-10-28 Imogen perf notes.md": "2026-10-28 18:00",
    "inbox/2026-11-03 status update DRAFT.md": "2026-11-03 21:15",
    "meetings/2026-11-05 team weekly.md": "2026-11-05 11:00",
    "screenshots/2026-11-10 slack Ollie.png": "2026-11-10 10:46",
    "inbox/2026-11-12 quick note.txt": "2026-11-12 09:05",
    "todo.md": "2026-11-12 09:10",
    "links/saved links.md": "2026-10-21 13:00",
    "personal/ideas.txt": "2026-10-02 22:40",
    # Deliberately backdated copy: same text as the original, newer date.
    "edge_cases/Copy of 2026-09-22 Lighthouse vendor decision.md": "2026-11-01 08:00",
}


def set_dates() -> None:
    for rel, stamp in DATES.items():
        t = time.mktime(datetime.strptime(stamp, "%Y-%m-%d %H:%M").timetuple())
        os.utime(ROOT / rel, (t, t))


if __name__ == "__main__":
    leadership_docx()
    ledgerly_pdf()
    slack_screenshot()
    scanned_pdf()
    locked_pdf()
    odd_files()
    symlinks()
    set_dates()
    print("sample_notes/ generated")
