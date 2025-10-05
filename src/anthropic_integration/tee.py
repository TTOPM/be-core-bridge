"""
Trusted Execution Environment abstraction (stub).
"""
def run_in_tee(fn):
    # In production, wrap in a real TEE (SGX/SEV/TEE enclaves).
    return fn()
