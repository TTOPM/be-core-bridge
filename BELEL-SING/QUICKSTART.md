
# BELEL-SING — All-in-One Drop-In Bundle

This bundle contains **everything wired** (API, streaming, MusicXML alignment, enterprise sidecars, plugin system, ULTRA trainer).
The **only thing not included** is third‑party model weights (due to licenses). Drop your weights or run the fetcher, then start.

## A) One-command bring-up (production singing with sidecars)
1) Place your licensed checkpoints under `ops/weights/`:
```
ops/weights/
  diffsinger/diffsinger_svs.ckpt
  diffsinger/pretrain_model.pth      # optional DiffSinger pretrain
  gpt_sovits/s2v4.ckpt
  rmvpe/rmvpe.onnx
  hifigan/generator.pth
  hifigan/config.json
  rvc/model.pth                      # optional, consented timbre
```
2) (Optional) Auto-download what is permitted:
```bash
python scripts/fetch_hf_weights.py
```
3) Start:
```bash
cd ops
docker compose -f docker-compose.enterprise.yml up --build
```
4) Call the streaming API (MIDI or MusicXML):
```bash
# Use an email in your allowlist
curl -H "X-Auth-Email: you@pearcerobinson.com" -H "Content-Type: application/json" \
     -X POST http://localhost:8610/v1/sing/stream \     -d '{"lyrics":"We rise together","midi_base64":"<BASE64 MIDI>"}' --output out.wav
```

## B) ULTRA training (push realism beyond pretrains)
1) Preprocess your datasets (edit paths inside script):
```bash
python hybrid_svs/preprocess_data.py
python hybrid_svs/merge_datasets.py    # merges to data/condensed_singing.h5
```
2) Train your model:
```bash
python hybrid_svs/hybrid_trainer.py --config hybrid_svs/config.yaml
```
3) Swap the trained checkpoints into the **DiffSinger/HiFi-GAN sidecars** (or wrap as plugins in `ops/plugins/`).

## Access Control
- The API enforces a domain allowlist: `ALLOWED_EMAIL_DOMAINS` env (defaults include your internal domains).
- For local dev, set `DEV_ALLOW_ALL=true`.

## Where things live
- API + streaming: `api/` (`/v1/sing`, `/v1/sing/stream`)
- Inference glue: `inference/`
- Utilities (MusicXML, phonemes, audio): `utils/`
- Sidecar images & compose: `ops/`
- Weights placeholders: `ops/weights/` (with README)
- Plugin examples: `ops/plugins/_examples/`
- ULTRA trainer: `hybrid_svs/` (+ `README_ULTRA.md`)
- HF fetch helper: `scripts/fetch_hf_weights.py`

You're ready. Drop weights → `docker compose up` → **it sings**.
