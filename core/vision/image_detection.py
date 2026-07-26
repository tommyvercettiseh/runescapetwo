from __future__ import annotations

# Dedicated public module for image/template detection.
# The implementation remains in detection.py for backwards compatibility.
from .detection import find_all_matches, find_best_match

__all__ = ["find_best_match", "find_all_matches"]
