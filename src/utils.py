"""Utility functions for ai-skills-sync."""

import hashlib
from pathlib import Path

MANAGER_TAG_FILE = ".ai-skills-managed"


def compute_hash(filepath: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def is_managed(skill_dir: Path) -> bool:
    """Check if directory was created by this tool."""
    return (skill_dir / MANAGER_TAG_FILE).exists()


def tag_managed(skill_dir: Path) -> None:
    """Mark directory as managed by this tool."""
    (skill_dir / MANAGER_TAG_FILE).touch()
