from pathlib import Path
from pypdf import PdfReader

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
        chunks.append(Chunk(filePath, i, page.extract_text(), i))

def chunkFile(filePath:str):
    if filePath[-3:] == "txt":
        chunkText(filePath)
    elif filePath[-2:] == "md":
        chunkMD(filePath)
    elif filePath[-3:] == "pdf":
        chunkPDF(filePath)
    