## Belel World Generator
Self-contained module for generating sovereign, interactive worlds.

### Setup
1. Install requirements: `pip install -r requirements.txt`
2. Add LingBot submodule and model as above.
3. Run local IPFS: `ipfs daemon` (install IPFS if needed).
4. Run local Ethereum: `ganache` (for multiplayer).
5. Generate: `python src/belel_world_generator.py --prompt "Your prompt" --image "path/to/image.jpg"`
6. Test: `pytest tests/test_world_generator.py` - Generates a sample world.
7. Fine-tune: `python src/fine_tune_world.py`

No external keys needed—all local.
