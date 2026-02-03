import torch
from demucs import pretrained  # Add demucs to reqs if needed

demucs_model = pretrained.get_model("htdemucs_ft").to(device)  # Fine-tuned

def separate_stems(audio_path, num_stems=16):
    waveform, sr = librosa.load(audio_path, sr=44100)
    waveform = torch.tensor(waveform).unsqueeze(0)
    stems = demucs_model(waveform)  # Outputs dict of stems
    for name, stem in stems.items():
        sf.write(f"{name}.wav", stem.squeeze(0).cpu().numpy(), sr)
    return list(stems.keys())

# Call in main: separate_stems("full_song.wav")
