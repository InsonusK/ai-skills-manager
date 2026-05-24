"""Updates relative Markdown links after skill sync.

Rules:
- Links within same skill -> unchanged
- Links to other managed skills -> updated to new path
- Links to external files -> updated relative to new location
- Broken links -> left as-is, reported in validation
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Optional

from ai_skills_manager.discovery.base import SkillMapping

MD_LINK_RE = re.compile(r'!?\[([^\]]*)\]\(([^\s\)"]*)(?:\s+"[^"]*")?\)')

logger = logging.getLogger(__name__)


class LinkUpdater:
    """Updates Markdown links to match new target structure."""

    version: int = 1

    def __init__(
        self,
        mappings: List[SkillMapping],
        source_to_target: Dict[Path, Path],
        all_source_files: Set[Path],
        dry_run: bool = False
    ):
        self.mappings = {m.skill_name: m for m in mappings}
        self.source_to_target = source_to_target
        self.all_source_files = all_source_files
        self.dry_run = dry_run
        self.fixes: List[dict] = []

    def _find_mapping_for_file(self, filepath: Path) -> Optional[SkillMapping]:
        """Find which skill mapping a target file belongs to."""
        for mapping in self.mappings.values():
            if mapping.is_flat:
                if filepath == mapping.target_path / "SKILL.md":
                    return mapping
            else:
                try:
                    filepath.relative_to(mapping.target_path)
                    return mapping
                except ValueError:
                    continue
        return None

    def adapt(self, filepath: Path) -> None:
        """Update links in a single markdown file."""
        if not filepath.exists() or filepath.suffix != ".md":
            return

        content = filepath.read_text(encoding="utf-8")
        original = content

        my_mapping = self._find_mapping_for_file(filepath)
        if not my_mapping:
            return

        def replace_link(match) -> str:
            full_match = match.group(0)
            text = match.group(1)
            link_path = match.group(2)
            is_image = full_match.startswith("!")

            # Skip external, anchors, absolute
            if link_path.startswith(("http://", "https://", "ftp://", "mailto:", "#", "/")):
                return full_match

            # Resolve link relative to the SOURCE file's directory
            if my_mapping.is_flat:
                source_dir = my_mapping.source_path.parent
            else:
                try:
                    rel = filepath.relative_to(my_mapping.target_path)
                    source_dir = my_mapping.source_path / rel.parent
                except ValueError:
                    source_dir = my_mapping.source_path

            linked_source = (source_dir / link_path).resolve()

            # Check if resolved source path is in our source_to_target map
            if linked_source in self.source_to_target:
                new_target = self.source_to_target[linked_source]
                try:
                    new_rel = os.path.relpath(new_target, filepath.parent).replace(os.sep, "/")
                    logger.debug(
                        "- Change link %s -> %s\n"
                        "   source file %s\n"
                        "   target file %s",
                        link_path, new_rel, filepath, new_target
                    )
                    self.fixes.append({
                        "file": str(filepath),
                        "old": link_path,
                        "new": new_rel,
                        "status": "fixed"
                    })
                    prefix = "!" if is_image else ""
                    return f"{prefix}[{text}]({new_rel})"
                except ValueError:
                    self.fixes.append({
                        "file": str(filepath),
                        "old": link_path,
                        "status": "broken"
                    })
                    return full_match

            # Check if linked file exists at source (external reference)
            if linked_source.exists():
                try:
                    new_rel = os.path.relpath(linked_source, filepath.parent).replace(os.sep, "/")
                    logger.debug(
                        "- Change link %s -> %s\n"
                        "   source file %s\n"
                        "   target file %s",
                        link_path, new_rel, filepath, linked_source
                    )
                    self.fixes.append({
                        "file": str(filepath),
                        "old": link_path,
                        "new": new_rel,
                        "status": "external"
                    })
                    prefix = "!" if is_image else ""
                    return f"{prefix}[{text}]({new_rel})"
                except ValueError:
                    self.fixes.append({
                        "file": str(filepath),
                        "old": link_path,
                        "status": "broken"
                    })
                    return full_match

            # Broken link
            self.fixes.append({
                "file": str(filepath),
                "old": link_path,
                "status": "broken"
            })
            return full_match

        new_content = MD_LINK_RE.sub(replace_link, content)

        if new_content != original and not self.dry_run:
            filepath.write_text(new_content, encoding="utf-8")

    def adapt_all(self, target_dir: Path) -> List[dict]:
        """Update links in all markdown files under target_dir."""
        self.fixes = []
        if not target_dir.exists():
            return self.fixes

        for md_file in target_dir.rglob("*.md"):
            self.adapt(md_file)

        return self.fixes
