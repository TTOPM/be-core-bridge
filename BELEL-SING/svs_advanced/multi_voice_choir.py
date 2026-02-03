import torch
from transformers import pipeline
import numpy as np
import soundfile as sf
from pydub import AudioSegment

# Load models
yue_choir = pipeline("text-to-audio", model="m-a-p/YuE-s1-7B-anneal-en-cot")  # Multi-voice base
fish_clone = pipeline("text-to-speech", model="fishaudio/fish-speech-1.5")

def generate_choir(lyrics, num_voices=4, styles=["soprano", "alto", "tenor", "bass"]):
    choir_layers = []
    for i, style in enumerate(styles):
        prompt = f"{style} harmony for lyrics: {lyrics}"
        audio = yue_choir(prompt)["audio"][0]
        # Clone variation
        cloned = fish_clone(prompt, voice=audio)["audio"]  # Zero-shot layer
        sf.write(f"choir_layer_{i}.wav", cloned, 44100)
        choir_layers.append(f"choir_layer_{i}.wav")
    
    # Mix layers
    base = AudioSegment.from_wav(choir_layers[0])
    for layer in choir_layers[1:]:
        base = base.overlay(AudioSegment.from_wav(layer))
    base.export("choir.wav", format="wav")
    return "choir.wav"

# Integrate into main: Call in generate_full_song for backups.
