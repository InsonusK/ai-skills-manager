"""Tests for AutoDiscovery strategy."""

import unittest
import tempfile
import shutil
from pathlib import Path

from ai_skills_sync.discovery.auto import AutoDiscovery
from ai_skills_sync.discovery.base import SkillMapping


class TestAutoDiscovery(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.target = self.tmpdir / 'target'
        self.target.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_empty_directory(self):
        empty = self.tmpdir / 'empty'
        empty.mkdir()

        strategy = AutoDiscovery(empty, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 0)

    def test_single_md_file(self):
        md = self.tmpdir / 'guide.md'
        md.write_text('# Guide')

        strategy = AutoDiscovery(md, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, 'guide')
        self.assertTrue(result[0].is_flat)
        self.assertEqual(result[0].source_path, md)
        self.assertEqual(result[0].target_path, self.target / 'guide')

    def test_non_md_file_ignored(self):
        txt = self.tmpdir / 'readme.txt'
        txt.write_text('readme')

        strategy = AutoDiscovery(txt, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 0)

    def test_directory_with_skill_md(self):
        skill_dir = self.tmpdir / 'web'
        skill_dir.mkdir()
        (skill_dir / 'SKILL.md').write_text('# Web')

        strategy = AutoDiscovery(skill_dir, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, 'web')
        self.assertFalse(result[0].is_flat)
        self.assertEqual(result[0].target_path, self.target / 'web')

    def test_flat_directory(self):
        flat = self.tmpdir / 'guides'
        flat.mkdir()
        (flat / 'a.md').write_text('# A')
        (flat / 'b.md').write_text('# B')

        strategy = AutoDiscovery(flat, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 2)
        names = {r.skill_name for r in result}
        self.assertEqual(names, {'a', 'b'})
        for mapping in result:
            self.assertTrue(mapping.is_flat)

    def test_flat_directory_ignores_non_md(self):
        flat = self.tmpdir / 'guides'
        flat.mkdir()
        (flat / 'guide.md').write_text('# Guide')
        (flat / 'readme.txt').write_text('readme')

        strategy = AutoDiscovery(flat, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, 'guide')

    def test_nested_flat_in_subdir(self):
        root = self.tmpdir / 'skills'
        root.mkdir()
        sub = root / 'frontend'
        sub.mkdir()
        (sub / 'react.md').write_text('# React')

        strategy = AutoDiscovery(root, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, 'frontend-react')
        self.assertTrue(result[0].is_flat)

    def test_nested_directory_skill(self):
        root = self.tmpdir / 'skills'
        root.mkdir()
        sub = root / 'backend'
        sub.mkdir()
        (sub / 'SKILL.md').write_text('# Backend')

        strategy = AutoDiscovery(root, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, 'backend')
        self.assertFalse(result[0].is_flat)

    def test_mixed_flat_and_directory(self):
        root = self.tmpdir / 'mixed'
        root.mkdir()
        (root / 'top.md').write_text('# Top')

        sub1 = root / 'web'
        sub1.mkdir()
        (sub1 / 'SKILL.md').write_text('# Web')

        sub2 = root / 'guides'
        sub2.mkdir()
        (sub2 / 'a.md').write_text('# A')

        strategy = AutoDiscovery(root, self.target)
        result = strategy.discover()

        names = {r.skill_name for r in result}
        self.assertEqual(names, {'top', 'web', 'guides-a'})

        by_name = {r.skill_name: r for r in result}
        self.assertTrue(by_name['top'].is_flat)
        self.assertFalse(by_name['web'].is_flat)
        self.assertTrue(by_name['guides-a'].is_flat)

    def test_deep_nesting(self):
        root = self.tmpdir / 'deep'
        root.mkdir()
        l1 = root / 'level1'
        l1.mkdir()
        l2 = l1 / 'level2'
        l2.mkdir()
        (l2 / 'skill.md').write_text('# Deep')

        strategy = AutoDiscovery(root, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, 'level1-level2-skill')

    def test_nonexistent_path(self):
        missing = self.tmpdir / 'missing'

        strategy = AutoDiscovery(missing, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 0)


if __name__ == '__main__':
    unittest.main()
