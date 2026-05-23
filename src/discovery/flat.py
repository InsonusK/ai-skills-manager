import os
"""Flat discovery strategy.

Treats all .md files in directory (and subdirectories) as individual flat skills.
"""

from pathlib import Path
from typing import List

from .base import DiscoveryStrategy, SkillMapping


class FlatDiscovery(DiscoveryStrategy):
    """Treat all .md files as flat skills."""

    def discover(self) -> List[SkillMapping]:
        """Find all .md files recursively."""
        if not self.source_path.exists():
            return []

        if self.source_path.is_file():
            if self.source_path.suffix == '.md':
                return [self._create_mapping(self.source_path, self.source_path.stem, is_flat=True)]
            return []

        results = []
        for md_file in sorted(self.source_path.rglob('*.md')):
            # Use relative path for name to avoid conflicts
            rel = md_file.relative_to(self.source_path)
            name = str(rel.with_suffix('')).replace('/', '-').replace('\\', '-')
            results.append(self._create_mapping(md_file, name, is_flat=True))

        return results
