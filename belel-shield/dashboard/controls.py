import os, subprocess, signal, sys, json
from pathlib import Path

HOME = Path.home()
DATA_DIR = HOME / ".belel"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PID_FILE = DATA_DIR / "gideon_scanner.pid"

def _python_executable():
    # Prefer the Python running Streamlit, else fallback to python3
    return sys.executable or "python3"

def scanner_is_running():
    if not PID_FILE.exists(): return False
    try:
        pid = int(PID_FILE.read_text().strip())
    except Exception:
        return False
    try:
        os.kill(pid, 0)  # check signal
        return True
    except Exception:
        PID_FILE.unlink(missing_ok=True)
        return False

def start_scanner(scanner_path: str) -> str:
    """
    Launch gideon_scanner.py detached, record its PID.
    Returns a status string.
    """
    if scanner_is_running():
        return "Scanner is already running."
    try:
        py = _python_executable()
        proc = subprocess.Popen(
            [py, scanner_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        PID_FILE.write_text(str(proc.pid))
        return f"Scanner started (pid {proc.pid})."
    except Exception as e:
        return f"Failed to start scanner: {e}"

def stop_scanner() -> str:
    """
    Stop the running scanner if PID file exists and process is alive.
    """
    if not PID_FILE.exists():
        return "No PID file; scanner not tracked."
    try:
        pid = int(PID_FILE.read_text().strip())
    except Exception as e:
        PID_FILE.unlink(missing_ok=True)
        return f"Invalid PID file removed ({e})."

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        PID_FILE.unlink(missing_ok=True)
        return "Scanner process not found; cleaned PID file."
    except Exception as e:
        return f"Failed to stop scanner: {e}"

    PID_FILE.unlink(missing_ok=True)
    return "Scanner stopped."

def run_update_blocklist(updater_path: str) -> str:
    """
    Run the manual updater once; return output combined (stdout+stderr).
    """
    try:
        py = _python_executable()
        out = subprocess.check_output([py, updater_path], stderr=subprocess.STDOUT, text=True)
        return out.strip()
    except subprocess.CalledProcessError as e:
        return (e.output or "").strip() or f"Updater failed: {e}"
    except Exception as e:
        return f"Updater error: {e}"

def firewall_apply_hint():
    # Print the exact commands; user enters sudo password themselves in a terminal.
    return (
        "To apply firewall sinkhole/tarpit rules (Linux):\n"
        "  sudo ./resilience/firewall_rules.sh\n\n"
        "To remove current DROP rules manually (examples):\n"
        "  sudo iptables -D OUTPUT -d <IP> -j DROP\n"
        "  sudo iptables -D INPUT  -s <IP> -j DROP\n"
    )
