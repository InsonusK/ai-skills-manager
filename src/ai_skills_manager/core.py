"""Core synchronization logic."""

import hashlib
import shutil
from pathlib import Path
from typing import List, Dict, Optional

from .config import load_config
from .discovery.base import SkillMapping
from .discovery.auto import AutoDiscovery
from .discovery.flat import FlatDiscovery
from .discovery.directory import DirectoryDiscovery
from .discovery.github import GitHubDiscovery
from .adapters.link_updater import LinkUpdater
from .utils import is_managed, tag_managed, compute_hash, read_managed_state, write_managed_state


STRATEGIES = {
    'auto': AutoDiscovery,
    'flat': FlatDiscovery,
    'directory': DirectoryDiscovery,
    'github': GitHubDiscovery,
}


def build_source_to_target_map(mappings: List[SkillMapping]) -> Dict[Path, Path]:
    """Build map from source file path to target file path."""
    result = {}
    for mapping in mappings:
        if mapping.is_flat:
            result[mapping.source_path] = mapping.target_path / 'SKILL.md'
        else:
            for src_file in mapping.source_path.rglob('*'):
                if src_file.is_file():
                    rel = src_file.relative_to(mapping.source_path)
                    result[src_file] = mapping.target_path / rel
    return result


def collect_source_files(mappings: List[SkillMapping]) -> set:
    """Collect all source file paths."""
    files = set()
    for mapping in mappings:
        if mapping.is_flat:
            files.add(mapping.source_path)
        else:
            files.update(mapping.source_path.rglob('*'))
    return {p for p in files if p.is_file()}


def compute_skill_hash(mapping: SkillMapping) -> str:
    """Compute hash of a skill source."""
    if mapping.is_flat:
        return compute_hash(mapping.source_path)
    h = hashlib.sha256()
    for file_path in sorted(mapping.source_path.rglob('*')):
        if file_path.is_file():
            rel = str(file_path.relative_to(mapping.source_path))
            h.update(rel.encode())
            h.update(compute_hash(file_path).encode())
    return h.hexdigest()


def copy_skill(mapping: SkillMapping, dry_run: bool, adapters: Optional[List] = None) -> None:
    """Copy a skill from source to target."""
    if dry_run:
        return

    if mapping.target_path.exists():
        shutil.rmtree(mapping.target_path)

    if mapping.is_flat:
        mapping.target_path.mkdir(parents=True, exist_ok=True)
        shutil.copy2(mapping.source_path, mapping.target_path / 'SKILL.md')
    else:
        shutil.copytree(mapping.source_path, mapping.target_path)

    tag_managed(mapping.target_path)

    state = {
        'hash': compute_skill_hash(mapping),
        'adapters': [
            {'name': adapter.__class__.__name__, 'version': getattr(adapter, 'version', 1)}
            for adapter in (adapters or [])
        ],
    }
    write_managed_state(mapping.target_path, state)


def should_copy_skill(mapping: SkillMapping, adapters: List, force: bool = False) -> bool:
    """Check if skill needs to be copied based on hash and adapter versions."""
    if force:
        return True
    if not is_managed(mapping.target_path):
        return True

    state = read_managed_state(mapping.target_path)
    if state is None:
        return True

    current_hash = compute_skill_hash(mapping)
    if state.get('hash') != current_hash:
        return True

    current_adapters = sorted(
        [
            {'name': adapter.__class__.__name__, 'version': getattr(adapter, 'version', 1)}
            for adapter in adapters
        ],
        key=lambda x: x['name'],
    )
    previous_adapters = sorted(
        state.get('adapters', []),
        key=lambda x: x.get('name', ''),
    )
    if current_adapters != previous_adapters:
        return True

    return False


def remove_orphans(target_dir: Path, valid_names: set, dry_run: bool) -> None:
    """Remove skills not in the valid set."""
    if not target_dir.exists():
        return

    for item in target_dir.iterdir():
        if item.is_dir() and is_managed(item) and item.name not in valid_names:
            if not dry_run:
                shutil.rmtree(item)


class SkillSync:
    """Main synchronization orchestrator."""

    def __init__(
        self,
        config_file: Path,
        target_dir: Optional[Path] = None,
        on_conflict: str = 'error',
        remove_orphans: bool = True,
        dry_run: bool = False,
        force: bool = False,
    ):
        self.config_file = Path(config_file).resolve()
        self.config_dir = self.config_file.parent
        self.target_dir = target_dir or (self.config_dir / '.agents' / 'skills')
        self.on_conflict = on_conflict
        self.remove_orphans = remove_orphans
        self.dry_run = dry_run
        self.force = force
        self.mappings: List[SkillMapping] = []

    def _resolve_conflicts(self, mappings: List[SkillMapping]) -> List[SkillMapping]:
        """Handle skill name conflicts."""
        name_to_mapping: Dict[str, SkillMapping] = {}

        for mapping in mappings:
            if mapping.skill_name in name_to_mapping:
                if self.on_conflict == 'error':
                    existing = name_to_mapping[mapping.skill_name].source_path
                    raise ValueError(
                        f"CONFLICT: Skill '{mapping.skill_name}' from {existing} "
                        f"and {mapping.source_path}"
                    )
                # last_wins: overwrite

            name_to_mapping[mapping.skill_name] = mapping

        return list(name_to_mapping.values())

    def sync(self) -> dict:
        """Run full synchronization."""
        config = load_config(self.config_file)
        settings = config.get('settings', {})
        sources = config.get('sources', [])

        # Override from config
        if 'target' in settings and not self.target_dir:
            self.target_dir = self.config_dir / settings['target']
        if 'on_conflict' in settings:
            self.on_conflict = settings['on_conflict']
        if 'remove_orphans' in settings:
            self.remove_orphans = settings['remove_orphans']
        if settings.get('dry_run', False):
            self.dry_run = True

        # Discover skills from all sources
        all_mappings: List[SkillMapping] = []
        strategies = []

        try:
            for src in sources:
                src_type = src.get('type', 'auto')
                strategy_class = STRATEGIES.get(src_type, AutoDiscovery)

                if src_type == 'github':
                    repo_url = src.get('path', '')
                    tree = src.get('tree', 'master')
                    subpath = src.get('subpath', 'skills')
                    strategy = strategy_class(
                        repo_url, self.target_dir, tree=tree, subpath=subpath
                    )
                else:
                    src_path = self.config_dir / src.get('path', '.')
                    strategy = strategy_class(src_path, self.target_dir)

                discovered = strategy.discover()
                strategies.append(strategy)

                # Apply explicit name override
                if 'name' in src and discovered:
                    for mapping in discovered:
                        mapping.skill_name = src['name']

                all_mappings.extend(discovered)

            # Resolve conflicts
            self.mappings = self._resolve_conflicts(all_mappings)

            # Build maps
            source_to_target = build_source_to_target_map(self.mappings)
            all_source_files = collect_source_files(self.mappings)

            # Prepare adapters
            updater = LinkUpdater(self.mappings, source_to_target, all_source_files, self.dry_run)
            adapters = [updater]

            # Ensure target exists
            if not self.dry_run:
                self.target_dir.mkdir(parents=True, exist_ok=True)

            # Copy skills
            skipped = 0
            for mapping in self.mappings:
                if mapping.target_path.exists() and not is_managed(mapping.target_path):
                    continue  # Skip non-managed existing skills
                if not should_copy_skill(mapping, adapters, force=self.force):
                    skipped += 1
                    continue
                copy_skill(mapping, self.dry_run, adapters=adapters)

            # Fix links
            fixes = updater.adapt_all(self.target_dir)

            fix_summary = {}
            for fix in fixes:
                fix_summary[fix['status']] = fix_summary.get(fix['status'], 0) + 1

            # Remove orphans
            if self.remove_orphans:
                valid_names = {m.skill_name for m in self.mappings}
                remove_orphans(self.target_dir, valid_names, self.dry_run)

            return {
                'synced_count': len(self.mappings) - skipped,
                'skipped_count': skipped,
                'fix_summary': fix_summary,
                'dry_run': self.dry_run,
            }
        finally:
            for strategy in strategies:
                if hasattr(strategy, 'cleanup'):
                    strategy.cleanup()
