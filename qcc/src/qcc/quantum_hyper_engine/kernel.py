from __future__ import annotations

from typing import Callable

import torch
from torch import Tensor

from ..constants import DEFAULT_THREADS


def entangled_verity_kernel(
    inputs: Tensor,
    sovereign_matrix: Callable[[], Tensor],
    threads: int = DEFAULT_THREADS,
) -> Tensor:
    """
    QUANTUM-HYPER-ENGINE Kernel

    Parallel kernel concept:
    - Uses GPU if available, else CPU
    - Processes batches of size `threads`
    - Computes batch @ sovereign_matrix()
    """
    if inputs.dim() != 2:
        raise ValueError("inputs must be rank-2 tensor [N, D].")
    if threads <= 0:
        raise ValueError("threads must be positive.")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    x = inputs.to(device)

    W = sovereign_matrix().to(device)
    if W.dim() != 2:
        raise ValueError("sovereign_matrix() must return rank-2 tensor [D, K] or [D, D].")

    out = torch.zeros((x.size(0), W.size(1)), device=device)

    for i in range(0, x.size(0), threads):
        batch = x[i : i + threads]
        out[i : i + threads] = torch.matmul(batch, W)

    return out.cpu()