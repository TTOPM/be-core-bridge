# src/protocol/daemon/symbiont_scheduler.py

import time
import schedule
from datetime import datetime

from src.protocol.monitoring.symbiont_introspect import run_introspection
from src.protocol.permanent_memory import PermanentMemory

memory = PermanentMemory()

def introspection_job():
    print("\n[🔍 Introspection Triggered] —", datetime.now().isoformat())
    
    try:
        report = run_introspection()
        memory.log_event("ScheduledIntrospection", report)
        print("✅ Introspection complete. Logged to PermanentMemory.")
    except Exception as e:
        error_msg = f"❌ Introspection failed at {datetime.now()}: {str(e)}"
        memory.log_event("IntrospectionError", error_msg)
        print(error_msg)

# Schedule the job every 30 minutes (adjust as needed)
schedule.every(30).minutes.do(introspection_job)

print("🧬 Symbiont Scheduler started. Introspection will run every 30 minutes...\n")

# Keep running
while True:
    schedule.run_pending()
    time.sleep(1)
