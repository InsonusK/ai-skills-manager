"""Tests for core synchronization logic."""

import unittest
import tempfile
import shutil
import json
from pathlib import Path

from ai_skills_manager.core import (
    SkillSync,
    build_source_to_target_map,
    collect_source_files,
    copy_skill,
)
from ai_skills_manager.discovery.base import SkillMapping
from ai_skills_manager.utils import is_managed


class TestBuildSourceToTargetMap(unittest.TestCase):
    def test_flat_mapping(self):
        mapping = SkillMapping(
            source_path=Path('/src/guide.md'),
            target_path=Path('/tgt/guide'),
            skill_name='guide',
            is_flat=True
        )

        result = build_source_to_target_map([mapping])

        self.assertEqual(result[Path('/src/guide.md')], Path('/tgt/guide/SKILL.md'))

    def test_directory_mapping(self):
        src = Path(tempfile.mkdtemp())
        try:
            skill_dir = src / 'web'
            skill_dir.mkdir()
            (skill_dir / 'SKILL.md').write_text('# Web')
            (skill_dir / 'extra.md').write_text('# Extra')

            mapping = SkillMapping(
                source_path=skill_dir,
                target_path=Path('/tgt/web'),
                skill_name='web',
                is_flat=False
            )

            result = build_source_to_target_map([mapping])

            self.assertEqual(result[skill_dir / 'SKILL.md'], Path('/tgt/web/SKILL.md'))
            self.assertEqual(result[skill_dir / 'extra.md'], Path('/tgt/web/extra.md'))
        finally:
            shutil.rmtree(src)

    def test_multiple_mappings(self):
        mappings = [
            SkillMapping(Path('/src/a.md'), Path('/tgt/a'), 'a', True),
            SkillMapping(Path('/src/b'), Path('/tgt/b'), 'b', False),
        ]

        result = build_source_to_target_map(mappings)

        self.assertEqual(len(result), 1)  # Only flat has direct mapping
        self.assertEqual(result[Path('/src/a.md')], Path('/tgt/a/SKILL.md'))


class TestCollectSourceFiles(unittest.TestCase):
    def test_flat_files(self):
        src_a = Path(tempfile.mkdtemp()) / 'a.md'
        src_a.write_text('# A')
        src_b = Path(tempfile.mkdtemp()) / 'b.md'
        src_b.write_text('# B')

        mappings = [
            SkillMapping(src_a, Path('/tgt/a'), 'a', True),
            SkillMapping(src_b, Path('/tgt/b'), 'b', True),
        ]

        result = collect_source_files(mappings)

        self.assertEqual(result, {src_a, src_b})

    def test_directory_files(self):
        src = Path(tempfile.mkdtemp())
        try:
            skill_dir = src / 'web'
            skill_dir.mkdir()
            (skill_dir / 'SKILL.md').write_text('# Web')
            (skill_dir / 'extra.md').write_text('# Extra')

            mapping = SkillMapping(skill_dir, Path('/tgt/web'), 'web', False)
            result = collect_source_files([mapping])

            self.assertEqual(len(result), 2)
            self.assertIn(skill_dir / 'SKILL.md', result)
            self.assertIn(skill_dir / 'extra.md', result)
        finally:
            shutil.rmtree(src)


class TestCopySkill(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.source = self.tmpdir / 'source'
        self.source.mkdir()
        self.target = self.tmpdir / 'target'
        self.target.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_copy_flat(self):
        md = self.source / 'guide.md'
        md.write_text('# Guide')

        mapping = SkillMapping(md, self.target / 'guide', 'guide', True)
        copy_skill(mapping, dry_run=False)

        self.assertTrue((self.target / 'guide').exists())
        self.assertTrue((self.target / 'guide' / 'SKILL.md').exists())
        self.assertEqual((self.target / 'guide' / 'SKILL.md').read_text(), '# Guide')
        self.assertTrue(is_managed(self.target / 'guide'))

    def test_copy_directory(self):
        skill = self.source / 'web'
        skill.mkdir()
        (skill / 'SKILL.md').write_text('# Web')
        (skill / 'extra.md').write_text('# Extra')

        mapping = SkillMapping(skill, self.target / 'web', 'web', False)
        copy_skill(mapping, dry_run=False)

        self.assertTrue((self.target / 'web').exists())
        self.assertTrue((self.target / 'web' / 'SKILL.md').exists())
        self.assertTrue((self.target / 'web' / 'extra.md').exists())
        self.assertTrue(is_managed(self.target / 'web'))

    def test_dry_run_no_changes(self):
        md = self.source / 'guide.md'
        md.write_text('# Guide')

        mapping = SkillMapping(md, self.target / 'guide', 'guide', True)
        copy_skill(mapping, dry_run=True)

        self.assertFalse((self.target / 'guide').exists())

    def test_overwrite_existing(self):
        existing = self.target / 'guide'
        existing.mkdir()
        (existing / 'old.md').write_text('old')

        md = self.source / 'guide.md'
        md.write_text('# Guide')

        mapping = SkillMapping(md, existing, 'guide', True)
        copy_skill(mapping, dry_run=False)

        self.assertFalse((existing / 'old.md').exists())
        self.assertTrue((existing / 'SKILL.md').exists())


class TestSkillSyncIntegration(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_full_sync(self):
        # Create source structure
        src = self.tmpdir / 'skills-repo'
        src.mkdir()
        (src / 'guide.md').write_text('# Guide')

        web = src / 'web'
        web.mkdir()
        (web / 'SKILL.md').write_text('# Web')

        # Create config
        config = self.tmpdir / 'ai-skills.yaml'
        config.write_text(json.dumps({
            'sources': [{'path': './skills-repo'}],
            'settings': {'target': '.agents/skills'}
        }))

        # Run sync
        sync = SkillSync(config_file=config)
        result = sync.sync()

        self.assertEqual(result['synced_count'], 2)

        # Verify structure
        target = self.tmpdir / '.agents' / 'skills'
        self.assertTrue((target / 'guide').exists())
        self.assertTrue((target / 'web').exists())
        self.assertTrue((target / 'guide' / '.ai-skills-managed').exists())

    def test_conflict_error(self):
        src = self.tmpdir / 'repo'
        src.mkdir()

        a = src / 'a'
        a.mkdir()
        (a / 'SKILL.md').write_text('# A')

        b = src / 'b'
        b.mkdir()
        (b / 'SKILL.md').write_text('# B')

        config = self.tmpdir / 'ai-skills.yaml'
        config.write_text(json.dumps({
            'sources': [
                {'path': './repo/a', 'name': 'same'},
                {'path': './repo/b', 'name': 'same'}
            ]
        }))

        sync = SkillSync(config_file=config, on_conflict='error')

        with self.assertRaises(ValueError) as ctx:
            sync.sync()

        self.assertIn('CONFLICT', str(ctx.exception))

    def test_dry_run(self):
        src = self.tmpdir / 'repo'
        src.mkdir()
        (src / 'guide.md').write_text('# Guide')

        config = self.tmpdir / 'ai-skills.yaml'
        config.write_text(json.dumps({
            'sources': [{'path': './repo'}]
        }))

        sync = SkillSync(config_file=config, dry_run=True)
        result = sync.sync()

        self.assertTrue(result['dry_run'])
        self.assertFalse((self.tmpdir / '.agents').exists())

    def test_orphan_removal(self):
        target = self.tmpdir / '.agents' / 'skills'
        target.mkdir(parents=True)

        old = target / 'old-skill'
        old.mkdir()
        from ai_skills_manager.utils import tag_managed
        tag_managed(old)

        src = self.tmpdir / 'repo'
        src.mkdir()
        (src / 'new.md').write_text('# New')

        config = self.tmpdir / 'ai-skills.yaml'
        config.write_text(json.dumps({
            'sources': [{'path': './repo'}],
            'settings': {'remove_orphans': True}
        }))

        sync = SkillSync(config_file=config)
        sync.sync()

        self.assertFalse(old.exists())
        self.assertTrue((target / 'new').exists())


if __name__ == '__main__':
    unittest.main()
