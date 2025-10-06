
import numpy as np
def wav_chunks(wav: "np.ndarray", sr:int, chunk_sec:float=0.5):
    step = int(sr*chunk_sec)
    for i in range(0, len(wav), step):
        yield wav[i:i+step]
