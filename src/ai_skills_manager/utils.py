"""Utility functions for ai-skills-sync."""

import hashlib
import json
from pathlib import Path
from typing import Optional

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


def read_managed_state(skill_dir: Path) -> Optional[dict]:
    """Read managed state from skill directory."""
    path = skill_dir / MANAGER_TAG_FILE
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def write_managed_state(skill_dir: Path, state: dict) -> None:
    """Write managed state to skill directory."""
    path = skill_dir / MANAGER_TAG_FILE
    path.write_text(json.dumps(state, indent=2), encoding='utf-8')
