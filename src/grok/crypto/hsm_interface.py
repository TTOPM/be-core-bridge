class HSM:
    def __init__(self): pass
    def seal(self, data: bytes) -> bytes: return data  # stub
    def unseal(self, blob: bytes) -> bytes: return blob
