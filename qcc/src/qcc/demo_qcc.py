from __future__ import annotations

import torch

from qcc.quantum_head import EntangledVerityLattice
from qcc.entanglement_shield import quantum_fingerprint
from qcc.quantum_hyper_engine import entangled_verity_kernel
from qcc.quantum_logs import QuantumLogger
from qcc.phase_verifier import bell_order_probability_audit

logger = QuantumLogger()

# QUANTUM-HEAD
lattice = EntangledVerityLattice()
ok, bell = lattice.build_bell_pair()
logger.log("Bell-pair build attempt", {"ok": ok, "circuit": bell})

queries = torch.randn(4, 16)
keys = torch.randn(6, 16)
alpha = lattice.entangle_order(queries, keys, d_k=16)
logger.log("Entangle order computed", {"shape": list(alpha.shape)})

trajectory = [0, 1, 1, 2, 0, 1, 2, 2]
stable = lattice.converge_entropy(trajectory)
logger.log("Entropy convergence", {"stable": stable})

# ENTANGLEMENT-SHIELD
fp = quantum_fingerprint({"module": "QCC", "phase": "Entanglement Genesis"})
logger.log("Quantum fingerprint", {"hash": fp})

# QUANTUM-HYPER-ENGINE
def sovereign_matrix():
    return torch.eye(16)

out = entangled_verity_kernel(inputs=queries, sovereign_matrix=sovereign_matrix, threads=2)
logger.log("Kernel output", {"shape": list(out.shape)})

# PHASE-VERIFIER
audit = bell_order_probability_audit(E_V=0.1, E_I=0.2, E_A=0.3)
logger.log("Bell ordering audit", {"passed": audit.passed, "details": audit.details})

print("QCC demo complete.")