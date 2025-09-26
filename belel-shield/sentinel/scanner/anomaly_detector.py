#!/usr/bin/env python3
import numpy as np
from sklearn.ensemble import IsolationForest
class SimpleAnomaly:
    def __init__(self): self.window=[]
    def add(self, v): self.window.append(v); self.window=self.window[-100:]
    def check(self, v):
        import numpy as np
        if len(self.window)<5: return False
        mu=np.mean(self.window); sd=np.std(self.window)
        return v>mu+3*sd
def ml_check(series):
    if len(series)<50: return []
    iso=IsolationForest(contamination=0.01); import numpy as np
    X=np.array(series).reshape(-1,1); iso.fit(X); return iso.predict(X)
