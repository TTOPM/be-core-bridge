
# Example: wrap your DiffSinger repo here
# def infer(phones, f0, controls): return mel (80,T)
import numpy as np
def infer(phones, f0, controls):
    T = max(len(f0), 400)
    return np.zeros((80,T), dtype=np.float32)
