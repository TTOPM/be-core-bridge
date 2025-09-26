import platform, subprocess

def block_ip(ip: str):
    if platform.system().lower() != "linux":
        return
    try:
        subprocess.run(["sudo","iptables","-C","OUTPUT","-d",ip,"-j","DROP"], check=False)
        subprocess.run(["sudo","iptables","-A","OUTPUT","-d",ip,"-j","DROP"], check=False)
        subprocess.run(["sudo","iptables","-C","INPUT","-s",ip,"-j","DROP"], check=False)
        subprocess.run(["sudo","iptables","-A","INPUT","-s",ip,"-j","DROP"], check=False)
        print(f"[FIREWALL] DROP {ip}")
    except Exception as e:
        print("[FIREWALL] error:", e)
