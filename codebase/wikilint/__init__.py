"""Shared wiki lint engine. This package is byte-identical across all
Scriptorium variants; per-variant behavior lives entirely in the CONFIG
dict and index_entry_extra() defined in the wiki root's lint.py."""

from .cli import main

__all__ = ["main"]
