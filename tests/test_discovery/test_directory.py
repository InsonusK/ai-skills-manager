"""Tests for DirectoryDiscovery strategy."""

import unittest
import tempfile
import shutil
from pathlib import Path

from ai_skills_sync.discovery.directory import DirectoryDiscovery


class TestDirectoryDiscovery(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.target = self.tmpdir / 'target'
        self.target.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_single_skill_directory(self):
        skill = self.tmpdir / 'web'
        skill.mkdir()
        (skill / 'SKILL.md').write_text('# Web')

        strategy = DirectoryDiscovery(skill, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, 'web')
        self.assertFalse(result[0].is_flat)

    def test_multiple_skill_directories(self):
        root = self.tmpdir / 'skills'
        root.mkdir()

        web = root / 'web'
        web.mkdir()
        (web / 'SKILL.md').write_text('# Web')

        api = root / 'api'
        api.mkdir()
        (api / 'SKILL.md').write_text('# API')

        strategy = DirectoryDiscovery(root, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 2)
        names = {r.skill_name for r in result}
        self.assertEqual(names, {'api', 'web'})

    def test_ignores_directories_without_skill_md(self):
        root = self.tmpdir / 'skills'
        root.mkdir()

        valid = root / 'valid'
        valid.mkdir()
        (valid / 'SKILL.md').write_text('# Valid')

        invalid = root / 'invalid'
        invalid.mkdir()
        (invalid / 'README.md').write_text('# Invalid')

        strategy = DirectoryDiscovery(root, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, 'valid')

    def test_file_input_ignored(self):
        md = self.tmpdir / 'guide.md'
        md.write_text('# Guide')

        strategy = DirectoryDiscovery(md, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 0)

    def test_empty_directory(self):
        empty = self.tmpdir / 'empty'
        empty.mkdir()

        strategy = DirectoryDiscovery(empty, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 0)

    def test_self_as_skill(self):
        """If root itself has SKILL.md, it's a single skill."""
        root = self.tmpdir / 'my-skill'
        root.mkdir()
        (root / 'SKILL.md').write_text('# My Skill')

        strategy = DirectoryDiscovery(root, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, 'my-skill')

    def test_self_with_subdirs(self):
        """If root has SKILL.md, subdirs are ignored."""
        root = self.tmpdir / 'my-skill'
        root.mkdir()
        (root / 'SKILL.md').write_text('# My Skill')

        sub = root / 'sub'
        sub.mkdir()
        (sub / 'SKILL.md').write_text('# Sub')

        strategy = DirectoryDiscovery(root, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, 'my-skill')


if __name__ == '__main__':
    unittest.main()
