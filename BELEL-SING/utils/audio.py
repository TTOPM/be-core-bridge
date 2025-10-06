
import numpy as np
def wav_to_mel(wav, sr, n_mels=80):
    T = max(int(len(wav)/(sr/100)), 80)
    return np.zeros((n_mels, T), dtype='float32')
