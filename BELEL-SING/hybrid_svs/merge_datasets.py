
import h5py, os, numpy as np
from sklearn.utils import shuffle

def merge_into_condensed(processed_dir, output_path='data/condensed_singing.h5'):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    all_samples=[]
    for hf in os.listdir(processed_dir):
        if not hf.endswith(".h5"): continue
        with h5py.File(os.path.join(processed_dir, hf), "r") as f:
            for k in f.keys():
                g=f[k]
                all_samples.append({
                    "audio": g["audio"][:],
                    "mel": g["mel"][:],
                    "f0": g["f0"][:],
                    "text_tokens": g["text_tokens"][:],
                    "melody": g["melody"][:],
                })
    all_samples = shuffle(all_samples, random_state=42)
    with h5py.File(output_path,"w") as out:
        for i,s in enumerate(all_samples):
            g=out.create_group(f"sample_{i}")
            g.create_dataset("audio", data=s["audio"], chunks=True)
            g.create_dataset("mel", data=s["mel"], chunks=True)
            g.create_dataset("f0", data=s["f0"], chunks=True)
            g.create_dataset("text_tokens", data=s["text_tokens"])
            g.create_dataset("melody", data=s["melody"])
    print("Merged", len(all_samples), "samples ->", output_path)

if __name__=="__main__":
    merge_into_condensed("./processed_data", "./data/condensed_singing.h5")
