"""Base classes for skill discovery."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class SkillMapping:
    """Maps a source to a target skill."""
    source_path: Path
    target_path: Path
    skill_name: str
    is_flat: bool


class DiscoveryStrategy(ABC):
    """Abstract base for skill discovery strategies."""

    def __init__(self, source_path: Path, target_dir: Path):
        if not source_path.exists():
            logger.error("source_path not found: %s", source_path)
        self.source_path = source_path.resolve()
        self.target_dir = target_dir

    @abstractmethod
    def discover(self) -> List[SkillMapping]:
        """Discover skills and return list of mappings."""
        pass

    def _create_mapping(self, source: Path, name: str, is_flat: bool) -> SkillMapping:
        """Helper to create a SkillMapping with resolved target path."""
        return SkillMapping(
            source_path=source,
            target_path=self.target_dir / name,
            skill_name=name,
            is_flat=is_flat
        )
