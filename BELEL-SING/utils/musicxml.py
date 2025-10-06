
from typing import List, Tuple
from music21 import converter, note, tempo
import re

def parse_musicxml(xml_path:str):
    score = converter.parse(xml_path)
    tempos = score.flat.getElementsByClass(tempo.MetronomeMark)
    bpm = tempos[0].number if tempos else 90
    notes = [n for n in score.flat.notes if isinstance(n, note.Note)]
    return notes, bpm

def syllabify(text:str)->List[str]:
    parts=[]
    for token in text.strip().split():
        parts += re.split(r"[-\u00AD]+", token)
    return [p for p in parts if p]

def align_lyrics_to_notes(lyrics:str, xml_path:str)->List[Tuple[str,int,float]]:
    notes, bpm = parse_musicxml(xml_path)
    syl = syllabify(lyrics)
    if not notes: return []
    dur_quarter_to_sec = 60.0/float(bpm)
    aligned=[]
    for i, n in enumerate(notes):
        syl_idx = min(i, len(syl)-1)
        dur = float(n.quarterLength) * dur_quarter_to_sec
        aligned.append((syl[syl_idx], int(n.pitch.midi), dur))
    return aligned
