import time
from datetime import datetime

from src.protocol.symbiont.symbiont_introspect import SymbiontIntrospect
from src.protocol.permanent_memory import PermanentMemory
from src.protocol.decentralized_comm.ipfs_client import IPFSClient
from src.protocol.security.alert_webhook import WebhookAlerter

# === Configuration ===
INTROSPECTION_INTERVAL = 3600  # Run every hour (in seconds)
WEBHOOK_URL = "https://discord.com/api/webhooks/xxx/yyy"  # Replace with your actual webhook

# === Initialize Components ===
memory = PermanentMemory(log_dir="./symbiont_logs")
ipfs = IPFSClient()
introspect = SymbiontIntrospect(memory=memory, ipfs_client=ipfs)
alerter = WebhookAlerter(WEBHOOK_URL)


def main():
    print("🔁 Symbiont Introspection Scheduler Started")
    print(f"⏱ Interval set to every {INTROSPECTION_INTERVAL / 60:.0f} minutes\n")

    while True:
        print(f"⏳ Starting introspection cycle: {datetime.now().isoformat()}")

        try:
            introspect.run_introspection()
            print("✅ Introspection complete.\n")

        except Exception as e:
            error_msg = f"❌ Introspection failed at {datetime.now().isoformat()}:\n{str(e)}"
            memory.log_event("IntrospectionError", error_msg)
            alerter.send_alert("Symbiont Introspection Failure", error_msg)
            print(error_msg + "\n")

        time.sleep(INTROSPECTION_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("🛑 Scheduler interrupted by user. Exiting gracefully.")
    except Exception as critical_failure:
        failure_msg = f"🔥 Critical failure in scheduler loop: {str(critical_failure)}"
        memory.log_event("SchedulerCriticalError", failure_msg)
        alerter.send_alert("Critical Scheduler Crash", failure_msg)
        raise
