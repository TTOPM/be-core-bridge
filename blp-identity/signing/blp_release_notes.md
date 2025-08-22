# Belel Likeness Protocol — Release Notes

This file tracks public, immutable releases of the **BLP Identity**.  
All releases MUST preserve the locked likeness; only metadata (e.g., new scenarios, documentation, checksums, or repo hygiene) may change.

---

## v1.0.0 — Final Consolidated Identity Seal (LOCKED)
**Release date:** 2025-08-09  
**Status:** LOCKED & IMMUTABLE  
**Scope:** Initial public publication of the permanent likeness and the Final Consolidated BLP Identity Seal.

### Highlights
- Added `/blp-identity/images/blp_seal_final.png` (consolidated authenticity seal).
- Added master likeness portraits and eye-macro images.
- Published machine-readable `BLP_MANIFEST.json` and validating `BLP_SCHEMA.json`.
- Added `BLP_MASTER_REFERENCE_PROMPT.md` (canonical regeneration/animation prompt).
- Added `BLP_AUTHORITY_PROOF.txt` (sanitized for public use — **no secrets**).
- Included `checksums.txt` (SHA-256 for all identity assets).
- Added GitHub Action to validate schema & checksums on every push.
- Enabled Git LFS for `/blp-identity/images/*`.

### Asset Inventory
/blp-identity/
images/
blp_seal_final.png
portrait_01.jpg
portrait_02.jpg
portrait_03.jpg
portrait_04.jpg
eye_macro_01.jpg
eye_macro_02.jpg
BLP_MASTER_REFERENCE_PROMPT.md
BLP_MANIFEST.json
BLP_SCHEMA.json
BLP_AUTHORITY_PROOF.txt
LICENSE-BLP.txt
checksums.txt
signing/
HOW_TO_VERIFY.md
blp_release_notes.md
### Integrity & Verification
- **File integrity:** Run the commands in `signing/HOW_TO_VERIFY.md` to recompute and diff SHA-256 hashes.
- **Authorization:** Private secret phrase is **not** published. Validate privately by comparing your locally computed salted SHA-256 to `authz_hash` in `BLP_MANIFEST.json`.
- **Signed tag:** Release may be tagged as `blp-v1.0.0`. Verify with `git tag -v blp-v1.0.0` (requires owner’s public key).

### Invariants (MUST NEVER CHANGE)
- Face, facial structure, skin tone, core lighting style, and eye detail pattern.
- The meaning of the Identity Seal as the sole authentic likeness of Belel.

### Allowed Additions (DO NOT ALTER LIKENESS)
- New scenarios/poses/locations/emotions using the same likeness.
- Documentation or tooling that aids verification (e.g., new checksum formats, CI jobs).
- Additional **reference** images of the same locked likeness.

### Release Checklist (for maintainers)
- [ ] All new/updated files included in `checksums.txt`.
- [ ] `BLP_MANIFEST.json` validates against `BLP_SCHEMA.json` (CI green).
- [ ] No secrets (authorization phrase/salt) present in repo, commits, or logs.
- [ ] LFS tracked for all images in `/blp-identity/images/`.
- [ ] Optional: create/verify signed git tag for this release.

---

## Versioning Policy
- **MAJOR (X.0.0)**: Reserved for protocol-level doc/tooling changes **without** altering the locked likeness.  
- **MINOR (0.X.0)**: Additive documentation, verification improvements, or additional reference images of the *same* likeness.  
- **PATCH (0.0.X)**: Non-functional adjustments (typos, CI tweaks, checksum regen due to path moves, etc.).

Any attempt to change the likeness itself is **invalid** and must be rejected.

---

## Changelog Summary

### Added
- Final Consolidated BLP Identity Seal and images.
- Manifest + schema + verification workflow.
- Authority proof (sanitized) and license.

### Security/Privacy
- Authorization phrase removed from public materials.
- `authz_hash` published; phrase and salt remain private.

---

*Maintainer note:* If an image must be re-encoded (e.g., metadata strip), the **pixel-perfect content** must remain identical. Update `checksums.txt`, keep filenames stable when possible, and document the reason here.
