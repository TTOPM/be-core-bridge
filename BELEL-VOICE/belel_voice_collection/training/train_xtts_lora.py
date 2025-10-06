
import subprocess, sys, os
cfg = 'training/xtts_v2_lora.yaml'
cmd = ['tts', 'train', '--config_path', cfg]
print('Running:', ' '.join(cmd))
sys.exit(subprocess.call(cmd))
