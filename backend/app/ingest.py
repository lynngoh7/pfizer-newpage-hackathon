from pathlib import Path

chunks = set()
class Chunk: 
    def __init__(self, filePath, start, text, end):
        self.filePath = filePath
        self.start = start
        self.end = end 
        self.text = text

def chunkText(filePath:str):
    with open('filename.txt', 'r') as file:
        start=1
        end=1
        text=""
        for i, line in enumerate(file):
            if line in ["\n", "\r\n"]:
                set.append(Chunk(filePath, start, text, end))
                start = i+1
                end = i+1

            else:
                end=i
                text+="" + line

                

def chunkFile(filePath:str):
    if filePath[:-3] == "txt":
        chunkText(filePath)
    