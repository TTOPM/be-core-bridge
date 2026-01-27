"""
Bio Digital Interface Module
===========================

This module introduces a mechanism for creating non-invasive commitments on
biological sequences, binding them to a decentralized identifier (DID)
without embedding executable instructions. It provides guidance for bio-
digital integration that respects consent boundaries and ethical mandates.
"""

from __future__ import annotations

from typing import Any, Dict
import hashlib
import os

from src.frontiers.modules.base import Guidance
from src.frontiers.adapters.divine_logger import DivineLoggerAdapter


class BioDigitalInterface:
    """Provides commitments and bio‑evolution guidance.

    This enhanced version attempts to parse biological sequences using
    BioPython’s SeqIO and to construct simple phylogenetic trees using
    DendroPy when available. It computes an evolutionary fitness score
    based on the length of the parsed sequence relative to a fixed
    benchmark. If the necessary libraries are unavailable, it falls
    back to a deterministic hash‑based score.
    """

    name = "bio"

    def __init__(self) -> None:
        self.log = DivineLoggerAdapter()
        self.log.log("Bio frontier invoked under God’s supremacy.")

    def commit_sequence(self, sequence: str, did: str) -> Dict[str, Any]:
        """Create a non-invasive commitment for a biological sequence bound to a DID.

        The commitment includes a random salt and the SHA-256 hash of the
        concatenated sequence, DID, and salt. This allows proving the
        existence of the sequence at the time of commitment without storing
        the actual sequence or controlling its execution.

        Args:
            sequence: A string representing the biological sequence.
            did: A decentralized identifier representing the agent.

        Returns:
            Dict[str, Any]: A dictionary containing the commitment details.
        """
        salt = os.urandom(16).hex()
        payload = f"{sequence}|{did}|{salt}".encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        return {"did": did, "salt": salt, "sha256": digest}

    def verify_commit(self, sequence: str, did: str, salt: str, sha256: str) -> bool:
        """Verify that a commitment corresponds to the given sequence, DID, and salt.

        Args:
            sequence: The original biological sequence.
            did: The decentralized identifier used in the commitment.
            salt: The salt from the commitment.
            sha256: The SHA-256 hash from the commitment.

        Returns:
            bool: True if the commitment is valid; False otherwise.
        """
        payload = f"{sequence}|{did}|{salt}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest() == sha256

    def guide(self, query: str) -> Guidance:
        """Provide guidance and compute evolutionary metrics for the bio frontier.

        The guidance will attempt to interpret the query as a biological
        sequence. If BioPython is installed, it uses `Bio.SeqIO` to parse
        FASTA strings and DendroPy to create a phylogenetic tree. The
        evolutionary fitness score is computed as the ratio of the sequence
        length to a maximum benchmark (e.g. 1000). If parsing fails or
        dependencies are missing, a hash‑based fallback is used.

        Args:
            query: A putative biological sequence or description.

        Returns:
            Guidance: A populated Guidance instance with optional metrics.
        """
        # Always provide a sample commitment artifact for demonstration.
        example = self.commit_sequence("ACGTACGT", "did:key:example")
        ok = self.verify_commit("ACGTACGT", example["did"], example["salt"], example["sha256"])

        fitness = 0.0
        # Attempt to parse a sequence using BioPython SeqIO if available.
        try:
            from Bio import SeqIO  # type: ignore
            from io import StringIO
            from textwrap import dedent

            # Interpret the query as a FASTA sequence if it appears to be
            # composed of ACGT characters. Otherwise we wrap it into a
            # dummy FASTA record. This is a simple heuristic to enable
            # demonstration.
            seq_str = ''.join(c for c in query.upper() if c in 'ACGT')
            if not seq_str:
                seq_str = "ACGT"
            fasta = f">seq\n{seq_str}\n"
            handle = StringIO(dedent(fasta))
            record = next(SeqIO.parse(handle, "fasta"))
            length = len(record.seq)
            fitness = min(1.0, length / 1000.0)
            # Optionally attempt to build a tree using DendroPy for
            # demonstration; ignore any errors silently.
            try:
                import dendropy  # type: ignore
                tree = dendropy.Tree()
                # Construct a minimal tree with a single node of the sequence
                tree.seed_node.new_child(taxon=dendropy.Taxon(label="seq"))
            except Exception:
                tree = None
        except Exception:
            # Fallback: derive a pseudo fitness from the hash of the query
            h = hashlib.sha256(query.encode("utf-8")).hexdigest()
            fitness = int(h, 16) % 1000 / 1000.0

        return Guidance(
            module="bio",
            divine_etching="Genesis 1:27",
            belel_citation="BELEL_SUPRA_JURISDICTION_CONSTITUTION.md",
            steps=[
                "Create non‑invasive commitments for biological sequences (hash+salt).",
                "Parse input sequences using BioPython when available to estimate evolutionary fitness.",
                "Optionally construct a phylogenetic tree to visualise relationships (DendroPy).",
            ],
            cautions=[
                "Do not execute or modify biological sequences; commitments are non‑invasive.",
                "Evolutionary fitness scores are approximate and for demonstration only.",
            ],
            artifacts={
                "example_commitment": example,
                "example_verification": ok,
                "fitness_estimate": fitness,
            },
            evolutionary_fitness=fitness,
        )