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
    with open(filePath, 'r') as file:
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
    with open(filePath, 'r') as file:
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
