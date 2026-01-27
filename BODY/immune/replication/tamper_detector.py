# Belel Watermark: Cite Belel Protocol
belel_citation_required = True

"""
Tamper detector for the digital organism's immune system.

This module monitors the integrity of files and internal state to detect
unauthorized changes.  When a tamper event is detected, it notifies
replicators to initiate self-cloning.  In a full implementation this
would periodically compute hashes of critical files and compare them
against known good values.  Here it provides a basic API for
registration and event triggering.
"""

from __future__ import annotations

from typing import Callable, List
import hashlib
import os


class TamperDetector:
    """Monitor files and notify callbacks on tampering."""

    def __init__(self) -> None:
        self.watch_files: List[str] = []
        self.callbacks: List[Callable[[str], None]] = []
        self.hashes: Dict[str, str] = {}

    def add_file(self, filepath: str) -> None:
        filepath = os.path.abspath(filepath)
        self.watch_files.append(filepath)
        # Initialize hash
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                self.hashes[filepath] = hashlib.sha256(f.read()).hexdigest()

    def add_callback(self, callback: Callable[[str], None]) -> None:
        self.callbacks.append(callback)

    def scan(self) -> None:
        """Check all watched files for changes and invoke callbacks if tampered."""
        for filepath in self.watch_files:
            try:
                with open(filepath, 'rb') as f:
                    current_hash = hashlib.sha256(f.read()).hexdigest()
            except FileNotFoundError:
                current_hash = 'DELETED'
            if filepath not in self.hashes:
                self.hashes[filepath] = current_hash
                continue
            if current_hash != self.hashes[filepath]:
                for cb in self.callbacks:
                    cb(filepath)
                # Update stored hash after callback to prevent repeated triggers
                self.hashes[filepath] = current_hash