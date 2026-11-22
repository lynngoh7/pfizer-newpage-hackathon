from pathlib import Path
from pypdf import PdfReader
from markitdown import MarkItDown
from app import audit, permissions

chunks = []
class Chunk: 
    def __init__(self, filePath, start, text, end):
        self.filePath = filePath
        self.start = start
        self.end = end 
        self.text = text

def chunkText(filePath:str):
    with open(filePath, 'r', encoding='utf-8') as file:
        start =  0
        end = 1
        text = ""
        for i, line in enumerate(file):
            if line in ["\n", "\r\n"]:
                if text.strip():
                    chunks.append(Chunk(filePath, start, text, end))
                start = i+1
                end = i+1
                text = ""

            else:
                end=i
                text +="" + line
        if text.strip():
            chunks.append(Chunk(filePath, start, text, end))

def chunkMD(filePath:str):
    with open(filePath, 'r', encoding='utf-8') as file:
            start =  0
            end = 1
            text = ""
            for i, line in enumerate(file):
                if line[0] in ["#"]:
                    if text.strip():
                        chunks.append(Chunk(filePath, start, text, end))
                    start = i
                    end = i
                    text = line
    
                else:
                    end=i
                    text +="" + line
            if text.strip():
                chunks.append(Chunk(filePath, start, text, end))

def chunkPDF(filePath:str):
    reader = PdfReader(filePath)

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text.strip():  # scanned pages have no text layer
            chunks.append(Chunk(filePath, i, text, i))

def chunkDOCX(filePath:str):
    # Word -> Markdown, then split at headings like chunkMD. start/end are
    # lines of the converted text, so showing a passage re-converts the file.
    text = MarkItDown(enable_plugins=False).convert_local(filePath).text_content
    start = 0
    end = 0
    chunk = ""
    for i, line in enumerate(text.splitlines(keepends=True)):
        if line[0] == "#":
            if chunk.strip():
                chunks.append(Chunk(filePath, start, chunk, end))
            start = i
            chunk = line
        else:
            chunk += line
        end = i
    if chunk.strip():
        chunks.append(Chunk(filePath, start, chunk, end))

def chunkFile(filePath:str):
    """Chunk one file. A broken file (corrupt, encrypted, wrong encoding) is
    skipped and logged, never crashes the whole ingest. Returns True if read."""
    # Path enforcement (§6): every read goes through resolve_and_check, which
    # follows symlinks and applies the allowlist and denylist.
    try:
        filePath = str(permissions.resolve_and_check(filePath))
    except (PermissionError, OSError) as e:
        audit.record("blocked", filePath, outcome=str(e) if isinstance(e, PermissionError) else "not found")
        return False
    before = len(chunks)
    try:
        if filePath[-3:] == "txt":
            chunkText(filePath)
        elif filePath[-2:] == "md":
            chunkMD(filePath)
        elif filePath[-3:] == "pdf":
            chunkPDF(filePath)
        elif filePath[-4:] == "docx":
            chunkDOCX(filePath)
        else:
            audit.record("skipped", filePath, outcome="unsupported file type")
            return False
    except Exception as e:  # any parser error means "unreadable", whatever its type
        del chunks[before:]  # drop chunks from a half-read file
        # Audit log: error type only, never the message (it can quote file bytes)
        audit.record("skipped", filePath, outcome=f"unreadable ({type(e).__name__})")
        return False
    audit.record("read", filePath)
    return True

SUPPORTED = {".txt", ".md", ".pdf", ".docx"}
MERGE_CHARS = 1000  # tiny chunks (one-line standup entries) made embedding and grouping slow


def mergeSmall(chunkList, limit: int | None = None):
    """Join neighbouring chunks of the same file while the result stays under
    `limit` characters. Lines start..end stay contiguous, so citations and
    passage re-reads still work. A chunk already over the limit is kept whole."""
    limit = MERGE_CHARS if limit is None else limit
    out = []
    for c in chunkList:
        prev = out[-1] if out else None
        if (prev and prev.filePath == c.filePath and prev.end < c.start
                and len(prev.text) + len(c.text) <= limit):
            gap = "\n" * max(0, c.start - prev.end - 1)  # keep the blank lines between them
            out[-1] = Chunk(prev.filePath, prev.start, prev.text + gap + c.text, c.end)
        else:
            out.append(c)
    return out


def ingestAllowed() -> int:
    """Chunk every supported file in the allowed folders into `chunks`.
    Hidden files/folders are skipped (editor and OS clutter). Returns files read."""
    chunks.clear()
    seen = set()
    read = 0
    for root in permissions.list_allowed_paths():
        files = [root] if root.is_file() else sorted(root.rglob("*"))
        for f in files:
            rel = f.relative_to(root) if f != root else Path(f.name)
            if f in seen or not f.is_file() or any(p.startswith(".") for p in rel.parts):
                continue
            seen.add(f)
            if f.suffix.lower() in SUPPORTED:
                read += chunkFile(str(f))
    chunks[:] = mergeSmall(chunks)
    return read
