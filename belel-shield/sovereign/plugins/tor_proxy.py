import shutil, subprocess
def start_tor_safely():
    if not shutil.which("tor"):
        print("[TOR] not installed"); return
    subprocess.Popen(["tor"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("[TOR] started (local)")
