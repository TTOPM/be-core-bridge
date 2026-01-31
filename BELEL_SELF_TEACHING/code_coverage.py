# BELEL_SELF_TEACHING/code_coverage.py
from __future__ import annotations
from typing import Dict, Any, Callable, Tuple
import re
import random

_RE_CODEBLOCK = re.compile(r"```(?:python)?\n(.*?)```", re.DOTALL | re.IGNORECASE)

def extract_python_code(text: str) -> str | None:
    m = _RE_CODEBLOCK.search(text)
    if not m:
        return None
    code = m.group(1).strip()
    return code if code else None

def generate_tests(code: str, generate_reflexive_variant, max_len: int = 1200) -> str:
    """
    Use your generator to propose minimal pytest-style tests.
    If you have a specialized test-writer model, swap it here.
    """
    prompt = (
        "Write minimal pytest tests for the following python code. "
        "Target edge cases and failure modes. "
        "Return only python code.\n\nCODE:\n"
        f"{code}\n"
    )
    tests = generate_reflexive_variant(prompt, mode="generate")
    # Keep bounded
    return tests[:max_len]

def mutate_code(code: str) -> str:
    """
    Tiny mutation: flip a comparison, change + to -, or change a literal.
    This is intentionally simple and safe.
    """
    lines = code.splitlines()
    if not lines:
        return code
    i = random.randrange(0, len(lines))
    line = lines[i]

    # common minimal mutations
    if "==" in line:
        line = line.replace("==", "!=", 1)
    elif ">=" in line:
        line = line.replace(">=", ">", 1)
    elif "<=" in line:
        line = line.replace("<=", "<", 1)
    elif "+" in line:
        line = line.replace("+", "-", 1)
    elif "-" in line:
        line = line.replace("-", "+", 1)
    else:
        line = line + "  # mutation"

    lines[i] = line
    return "\n".join(lines)

def coverage_verify(
    completion: str,
    sandbox_run_python: Callable[[str], Dict[str, Any]],
    generate_reflexive_variant: Callable[[str, str], str],
) -> Dict[str, Any]:
    """
    Returns:
      {
        "has_code": bool,
        "tests_generated": bool,
        "tests_passed": bool,
        "mutation_killed": bool,
        "details": {...}
      }
    """
    code = extract_python_code(completion)
    if not code:
        return {"has_code": False, "tests_generated": False, "tests_passed": False, "mutation_killed": False, "details": {}}

    tests = generate_tests(code, generate_reflexive_variant)
    combined = code + "\n\n" + tests

    run_res = sandbox_run_python(combined)  # must run & return pass/fail
    tests_passed = bool(run_res.get("passed"))

    mutated = mutate_code(code)
    mutated_combined = mutated + "\n\n" + tests
    mut_res = sandbox_run_python(mutated_combined)
    mutation_killed = not bool(mut_res.get("passed"))

    return {
        "has_code": True,
        "tests_generated": True,
        "tests_passed": tests_passed,
        "mutation_killed": mutation_killed,
        "details": {"run": run_res, "mutation": mut_res}
    }
