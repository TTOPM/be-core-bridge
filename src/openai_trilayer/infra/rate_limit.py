import time
class TokenBucket:
    def __init__(self, rate:float, burst:int):
        self.rate=rate; self.burst=burst; self.tokens=burst; self.last=time.time()
    def allow(self, cost:int=1)->bool:
        now=time.time(); self.tokens=min(self.burst, self.tokens+(now-self.last)*self.rate); self.last=now
        if self.tokens>=cost: self.tokens-=cost; return True
        return False
