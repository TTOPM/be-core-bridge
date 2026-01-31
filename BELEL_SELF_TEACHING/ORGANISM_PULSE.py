# In ORGANISM_PULSE.py - add to main loop or periodic task
import random

# ... existing pulse code ...

if random.random() < 0.15:  # ~every 6-7 pulses, or use time-based
    print("Initiating self-teaching cycle...")
    from BELEL_SELF_TEACHING.BELEL_SELF_TEACHING_GENERATOR import run_self_teaching_cycle
    run_self_teaching_cycle()
