
# BELEL-SING — Ultra Realism Add-on

- New **hybrid_svs/** module with vibrato/timbre controls, diffusion refinement, and training scaffolds.
- Use alongside enterprise compose to deploy real checkpoints for immediate singing; use ULTRA to train your own next-gen models.

## Quick steps
1) Preprocess your singing datasets in `hybrid_svs/preprocess_data.py`.
2) Train with `hybrid_svs/hybrid_trainer.py`.
3) Swap the enterprise sidecars to your trained checkpoints for production.
