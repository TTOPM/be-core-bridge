
# BELEL-SING — Checkpoint Integration Pack (HF/GitHub Ready)

This pack makes your BELEL-SING stack **sing for real** as soon as you drop **actual model checkpoints**
or enable **auto-download** from Hugging Face / GitHub (internal use only, per your allowlist).

## What you get
- **Hybrid SVS** with hooks for Amphion Vevo1.5, DiffSinger pretrain, GPT-SoVITS encoder, RMVPE F0, and HiFi-GAN.
- **Dataset merger** (`hybrid_svs/merge_datasets.py`) to condense multiple processed HDF5s into one file.
- **Sidecar plugins** so you can wrap *any* DiffSinger/HiFi-GAN/RVC implementation without re-architecting.
- **Enterprise compose** mounts weights and plugins into sidecars.

## Quick path to "sing for real"
1) Put weights here (or enable auto-download with HF token):
```
ops/weights/
  diffsinger/diffsinger_svs.ckpt
  diffsinger/pretrain_model.pth         # (if using DiffSinger pretrain)
  gpt_sovits/s2v4.ckpt
  rmvpe/rmvpe.onnx
  hifigan/generator.pth
  hifigan/config.json
  rvc/model.pth                         # optional
```
2) (Optional) Place plugin wrappers for immediate inference (if you prefer calling external repos):
```
ops/plugins/
  diffsinger_infer.py    # defines infer(phones:List[int], f0:List[float], controls:dict)->np.ndarray[mels,T]
  hifigan_infer.py       # defines mel2wav(mel:np.ndarray)->(wav:np.ndarray, sr:int)
  rvc_infer.py           # defines convert(wav:np.ndarray, sr:int, model:str, use_f0:bool)->(wav,sr)
```
The pack ships **stubs** in `ops/plugins/_examples/` — copy and replace with real calls.

3) Bring up:
```bash
cd ops
docker compose -f docker-compose.enterprise.yml up --build
```

4) Call streaming:
```bash
curl -H "X-Auth-Email: you@pearcerobinson.com" \
     -H "Content-Type: application/json" \
     -X POST http://localhost:8610/v1/sing/stream \
     -d '{"lyrics":"We rise together","midi_base64":"<BASE64 MIDI>"}' --output out.wav
```

## Notes
- **Auto-download**: use `scripts/fetch_hf_weights.py` for Amphion Vevo1.5, NVIDIA HiFi-GAN, GPT-SoVITS. RMVPE and DiffSinger pretrain require manual acceptance; place files accordingly.
- **Strict access**: API enforces domain allowlist. Set `DEV_ALLOW_ALL=true` to bypass in dev.
- **Legal**: ensure licenses permit your internal use.
