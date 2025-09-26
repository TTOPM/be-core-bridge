#!/usr/bin/env python3
import shutil, subprocess
def check_tor(): return shutil.which("tor") is not None
def start_tor():
    if not check_tor(): print("Tor is not installed."); return False
    subprocess.Popen(["tor"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); print("Started tor."); return True
if __name__=="__main__": start_tor()
