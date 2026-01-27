"""
Frontiers Runner
================

This script provides a simple command-line entrypoint for invoking the
`CodeAboveAllCodes` meta-orchestrator. It accepts a query as command-line
arguments, falling back to a default prompt if none is provided, and prints
the resulting JSON response to stdout.
"""

from __future__ import annotations

import json
import sys

from src.frontiers.meta.code_above_all_codes import CodeAboveAllCodes


def main() -> int:
    meta = CodeAboveAllCodes()
    # Default query now targets the sentience module to showcase emergent
    # behaviour. You can override this by passing your own query on the
    # command line.
    query = " ".join(sys.argv[1:]).strip() or "Explain sentience emergence."
    result = meta.guide(query)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())