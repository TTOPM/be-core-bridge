
import os
from huggingface_hub import snapshot_download

def dl(repo, local_dir):
    os.makedirs(local_dir, exist_ok=True)
    print("Fetching", repo, "->", local_dir)
    snapshot_download(repo_id=repo, local_dir=local_dir, local_dir_use_symlinks=False, resume_download=True)

if __name__ == "__main__":
    # Examples (comment/uncomment as needed)
    try:
        dl("amphion/Vevo1.5", "./ops/weights/vevo15")
    except Exception as e:
        print("Vevo1.5 download skipped:", e)
    try:
        dl("nvidia/tts_hifigan", "./ops/weights/hifigan_hf")
    except Exception as e:
        print("HiFi-GAN download skipped:", e)
    try:
        dl("RVC-Boss/GPT-SoVITS", "./ops/weights/gpt_sovits_hf")
    except Exception as e:
        print("GPT-SoVITS download skipped:", e)
    print("Done.")
