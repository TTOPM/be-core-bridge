from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

import torch
from torch import Tensor
from torch.nn import Softmax

from ..constants import DEFAULT_KL_TOLERANCE


def _safe_kl_div(p_log: Tensor, q: Tensor) -> Tensor:
    """
    KL(p || q) with defensive smoothing.
    p is log-probs, q is probs.
    """
    eps = 1e-12
    q = torch.clamp(q, min=eps)
    return torch.kl_div(p_log, q, reduction="sum")


@dataclass
class EntangledVerityLattice:
    """
    QUANTUM-HEAD Module — Entangled Verity Lattice

    Implements:
    - Bond Entanglement Ordering (attention-like energy)
    - Decoherence-bounded stability via KL threshold (< 0.05)
    - Optional Bell-pair circuit creation if Qiskit is installed (offline safe)
    """

    bond_types: List[str]
    transition: Tensor
    marginal: Tensor
    kl_tolerance: float = DEFAULT_KL_TOLERANCE
    _softmax: Softmax = Softmax(dim=-1)

    def __init__(self, bond_types: Optional[List[str]] = None, kl_tolerance: float = DEFAULT_KL_TOLERANCE):
        if bond_types is None:
            bond_types = ["verity", "integrity", "autonomy"]

        self.bond_types = bond_types
        n = len(bond_types)

        # Stochastic-ish transition matrix for internal trajectories (placeholder).
        self.transition = torch.rand(n, n)
        self.transition = self.transition / self.transition.sum(dim=-1, keepdim=True)

        self.marginal = torch.ones(n) / n
        self.kl_tolerance = kl_tolerance
        self._softmax = Softmax(dim=-1)

    def build_bell_pair(self) -> Tuple[bool, str]:
        """
        Builds a 2-qubit Bell pair circuit if qiskit is present.
        Returns (ok, message). No hard dependency.
        """
        try:
            import qiskit  # type: ignore

            qc = qiskit.QuantumCircuit(2)
            qc.h(0)
            qc.cx(0, 1)
            return True, qc.draw(output="text")
        except Exception as e:
            return False, f"Qiskit unavailable or failed: {e!r}"

    def entangle_order(self, queries: Tensor, keys: Tensor, d_k: int) -> Tensor:
        """
        Energy:
          E_ij = - <psi | q_i^T k_j | psi> / sqrt(d_k)
        Here modeled as standard scaled dot-product attention energy.
        Attention:
          alpha_ij = exp(-E_ij) / sum_l exp(-E_il)
        """
        if queries.dim() != 2 or keys.dim() != 2:
            raise ValueError("queries and keys must be rank-2 tensors: [N, D] and [M, D].")
        if queries.size(1) != keys.size(1):
            raise ValueError("queries and keys must share feature dimension D.")
        if d_k <= 0:
            raise ValueError("d_k must be positive.")

        logits = torch.matmul(queries, keys.T) / torch.sqrt(torch.tensor(float(d_k)))
        energies = -logits
        return self._softmax(-energies)

    def converge_entropy(self, trajectory: Sequence[int]) -> bool:
        """
        Decoherence bound:
          D_KL(pi || hat{pi}) < 0.05
        Where pi is marginal and hat{pi} is empirical frequency from trajectory.
        """
        if len(trajectory) == 0:
            return False

        traj = torch.tensor(list(trajectory), dtype=torch.long)
        n = len(self.bond_types)

        # Safe bincount size.
        emp = torch.bincount(traj, minlength=n).float()
        emp_freq = emp / emp.sum()

        kl = _safe_kl_div(self.marginal.log(), emp_freq)
        return bool(kl.item() < self.kl_tolerance)

    def path_entanglement_softmin(self, path_energies: Tensor, concurrence: Tensor) -> Tensor:
        """
        Path Entanglement Soft-Min:
          E*(s->t) = -log sum_p exp(-E(p)) ⊗ chi(p)
        Here: exp(-E) * concurrence, then softmin via -log(sum(.))
        """
        if path_energies.shape != concurrence.shape:
            raise ValueError("path_energies and concurrence must have the same shape.")

        weights = torch.exp(-path_energies) * concurrence
        s = torch.sum(weights)
        s = torch.clamp(s, min=1e-12)
        return -torch.log(s)