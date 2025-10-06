
import os, numpy as np
from utils.phonemes import to_phonemes, phoneme_ids
from utils.pitch import midi_to_f0_curve
from utils.musicxml import align_lyrics_to_notes

USE_SIDECARS = os.getenv('USE_SIDECARS','true').lower()=='true'
if USE_SIDECARS:
    from svs.clients.diffsinger_client import infer_mel
    from vocoder.clients.hifigan_client import mel2wav
    try:
        from vc.clients.rvc_client import convert_voice as rvc_convert
    except Exception:
        rvc_convert = None
else:
    # local fallbacks (silence)
    def infer_mel(phone_ids, f0, controls=None):
        T = max(len(f0), 400); return np.zeros((80,T), dtype='float32')
    def mel2wav(mel): 
        sr=44100; return np.zeros(sr, dtype='float32'), sr
    def rvc_convert(wav, sr, model_name="target", f0=True):
        return wav, sr

def sing(lyrics:str, midi_path:str=None, musicxml_path:str=None, controls:dict=None):
    phones = to_phonemes(lyrics, lang='en')
    if musicxml_path:
        aligned = align_lyrics_to_notes(lyrics, musicxml_path)
        f0 = [440.0 * (2 ** ((midi-69)/12.0)) for _, midi, _ in aligned] if aligned else []
    else:
        f0 = midi_to_f0_curve(midi_path) if midi_path else []
    mel = infer_mel(phoneme_ids(phones), f0, controls=controls or {})
    wav, sr = mel2wav(mel)
    if controls and controls.get("rvc_model") and rvc_convert:
        wav, sr = rvc_convert(wav, sr, model_name=str(controls["rvc_model"]), f0=True)
    return wav, sr
