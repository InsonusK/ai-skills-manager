"""Directory discovery strategy.

Expects subdirectories containing SKILL.md files.
"""

from pathlib import Path
from typing import List

from .base import DiscoveryStrategy, SkillMapping


class DirectoryDiscovery(DiscoveryStrategy):
    """Find directory skills (subdirs with SKILL.md)."""

    def discover(self) -> List[SkillMapping]:
        """Find all subdirectories containing SKILL.md."""
        if not self.source_path.exists():
            return []

        # If source itself is a file, ignore
        if self.source_path.is_file():
            return []

        # If source itself has SKILL.md, it's a single skill
        if (self.source_path / 'SKILL.md').exists():
            return [self._create_mapping(
                self.source_path,
                self.source_path.name,
                is_flat=False
            )]

        # Otherwise scan subdirectories
        results = []
        for subdir in sorted(self.source_path.iterdir()):
            if subdir.is_dir() and (subdir / 'SKILL.md').exists():
                results.append(self._create_mapping(subdir, subdir.name, is_flat=False))

        return results
