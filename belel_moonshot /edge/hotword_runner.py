
# hotword_runner.py — example runner using the HotwordEngine interface.
from time import sleep
from hotword_iface import PorcupineShim

def on_wake():
    print("[hotword] Wake word detected: Belel.")

if __name__=="__main__":
    eng = PorcupineShim()
    eng.load("models/belel_wake.ppn", sensitivity=0.6)
    eng.start(on_wake)
    try:
        for _ in range(5):
            sleep(1)
            # Simulate wake event:
            on_wake()
    finally:
        eng.stop()
