
import numpy as np, mido
def extract_f0(wav, sr):
    T = max(int(len(wav)/(sr/100)), 100)
    return np.zeros(T, dtype='float32')
def midi_to_f0_curve(midi_path, sr=44100, hop=512):
    mid = mido.MidiFile(midi_path); steps=[]
    for msg in mid:
        if msg.type=='note_on' and msg.velocity>0:
            f0 = 440.0 * (2 ** ((msg.note-69)/12))
            steps.append(f0)
    T = max(len(steps)*50, 400); f0 = np.zeros(T, dtype='float32')
    for i,s in enumerate(steps): f0[i*50:(i+1)*50]=s
    return f0
