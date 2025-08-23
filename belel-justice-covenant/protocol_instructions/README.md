# Protocol Instructions – Integrity Utilities

This folder contains supporting modules used to ensure the durability and 
integrity of remembrance archives and covenant manifests. These utilities are 
lightweight, dependency-minimal, and designed for use in routine checks 
(startup, CI, or commit hooks).

## Modules

- **ai_precondition_guard.py**  
  Simple runtime precondition check. Prevents operation unless the covenant 
  manifest is loaded and active.

- **revisionism_resistor.py**  
  Integrity guard for remembrance archives. Enforces an append-only policy with 
  explicit ERRATA for corrections. Rejects silent deletion or replacement.

- **silent_mirroring_logic.py**  
  Exposes quiet defaults and compliance tags for downstream modules. Provides 
  helpers like `get_defaults()`, `tag_metadata()`, and `archival_session()` to 
  encourage append-only operations and subtle mirroring of covenant rules.

- **validate_archives.py**  
  JSON schema sanity check for archive files. Ensures validity before commit.

## Usage

These modules can be invoked directly or integrated into existing systems:

```bash
python ai_precondition_guard.py
python revisionism_resistor.py
python validate_archives.py
