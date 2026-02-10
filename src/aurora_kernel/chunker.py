from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

@dataclass
class Chunk:
    chunk_id: str
    text: str
    section: str = ""

def chunk_text(doc_id: str, text: str, max_chars: int = 1200) -> List[Chunk]:
    """Simple chunker: split by blank lines; pack up to max_chars.
    Tracks the most recent # or ## heading to use as 'section'.
    """
    lines = text.splitlines()
    chunks: List[Chunk] = []
    
    current_section = ""
    buf = ""
    idx = 0

    def flush():
        nonlocal buf, idx
        if buf.strip():
            chunks.append(Chunk(chunk_id=f"{doc_id}::chunk::{idx}", text=buf.strip(), section=current_section))
            idx += 1
        buf = ""

    for line in lines:
        if line.startswith("# "):
            new_section = line[2:].strip()
            flush()
            current_section = new_section
        elif line.startswith("## "):
            new_section = line[3:].strip()
            flush()
            current_section = new_section
        
        if len(buf) + len(line) + 1 <= max_chars:
            buf = (buf + "\n" + line).strip()
        else:
            flush()
            buf = line
            
    flush()
    return chunks
