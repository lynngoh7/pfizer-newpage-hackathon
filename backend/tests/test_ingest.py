"""ingest: chunking TXT/MD/PDF, and broken files are skipped, not fatal."""
import pytest

from app import audit, ingest


@pytest.fixture(autouse=True)
def _clean():
    ingest.chunks.clear()
    audit.clear()
    yield
    ingest.chunks.clear()


def test_txt_splits_on_blank_lines_and_keeps_last_chunk(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("one\ntwo\n\n\nthree\n")
    assert ingest.chunkFile(str(f))
    assert [(c.start, c.end) for c in ingest.chunks] == [(0, 1), (4, 4)]


def test_md_starts_a_chunk_at_each_heading(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("# One\nbody\n# Two\nmore\n")
    ingest.chunkFile(str(f))
    assert [c.text.splitlines()[0] for c in ingest.chunks] == ["# One", "# Two"]


def test_broken_files_are_skipped_and_logged(tmp_path):
    bad_pdf = tmp_path / "corrupt.pdf"
    bad_pdf.write_bytes(b"%PDF-1.7\nnot really a pdf")
    bad_txt = tmp_path / "latin1.txt"
    bad_txt.write_bytes("first\n\ncaf\xe9\n".encode("latin-1"))  # chunk 1 ok, then a decode error
    good = tmp_path / "ok.txt"
    good.write_text("fine\n")

    assert not ingest.chunkFile(str(bad_pdf))
    assert not ingest.chunkFile(str(bad_txt))
    assert ingest.chunkFile(str(good))

    # nothing left over from the half-read file
    assert [c.filePath for c in ingest.chunks] == [str(good)]
    log = [(e["action"], e["outcome"]) for e in audit.entries()]
    assert log[0][0] == log[1][0] == "skipped"
    assert log[2] == ("read", "ok")
    # the log names the error type only, never file content
    assert all("caf" not in o for _, o in log)


def test_docx_splits_at_headings(tmp_path):
    import zipfile
    # smallest valid .docx: one Heading1 paragraph and one body paragraph each
    body = "".join(
        f'<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>{h}</w:t></w:r></w:p>'
        f'<w:p><w:r><w:t>{b}</w:t></w:r></w:p>' for h, b in [("One", "first"), ("Two", "second")])
    W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    f = tmp_path / "a.docx"
    with zipfile.ZipFile(f, "w") as z:
        z.writestr("[Content_Types].xml",
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("_rels/.rels",
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/document.xml", f"<w:document {W}><w:body>{body}</w:body></w:document>")
    assert ingest.chunkFile(str(f))
    assert [c.text.split()[:2] for c in ingest.chunks] == [["#", "One"], ["#", "Two"]]
