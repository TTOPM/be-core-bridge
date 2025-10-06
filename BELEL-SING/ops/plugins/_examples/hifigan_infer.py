
# Example: load generator.pth/config.json and do mel->wav
import numpy as np
def mel2wav(mel):
    sr=44100
    return np.zeros(sr, dtype=np.float32), sr
