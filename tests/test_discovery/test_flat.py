"""Tests for FlatDiscovery strategy."""

import unittest
import tempfile
import shutil
from pathlib import Path

from ai_skills_manager.discovery.flat import FlatDiscovery


class TestFlatDiscovery(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.target = self.tmpdir / 'target'
        self.target.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_single_md_file(self):
        md = self.tmpdir / 'guide.md'
        md.write_text('# Guide')

        strategy = FlatDiscovery(md, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, 'guide')
        self.assertTrue(result[0].is_flat)

    def test_non_md_file_ignored(self):
        txt = self.tmpdir / 'readme.txt'
        txt.write_text('readme')

        strategy = FlatDiscovery(txt, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 0)

    def test_flat_directory(self):
        flat = self.tmpdir / 'guides'
        flat.mkdir()
        (flat / 'a.md').write_text('# A')
        (flat / 'b.md').write_text('# B')

        strategy = FlatDiscovery(flat, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 2)
        names = {r.skill_name for r in result}
        self.assertEqual(names, {'a', 'b'})

    def test_recursive_flat(self):
        root = self.tmpdir / 'docs'
        root.mkdir()
        (root / 'top.md').write_text('# Top')

        sub = root / 'api'
        sub.mkdir()
        (sub / 'rest.md').write_text('# REST')

        strategy = FlatDiscovery(root, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 2)
        names = {r.skill_name for r in result}
        self.assertEqual(names, {'top', 'api-rest'})

    def test_ignores_skill_md_directories(self):
        """Flat mode should still find .md files inside directories with SKILL.md."""
        root = self.tmpdir / 'skills'
        root.mkdir()

        web = root / 'web'
        web.mkdir()
        (web / 'SKILL.md').write_text('# Web')
        (web / 'extra.md').write_text('# Extra')

        strategy = FlatDiscovery(root, self.target)
        result = strategy.discover()

        # Should find both .md files
        names = {r.skill_name for r in result}
        self.assertIn('web-SKILL', names)
        self.assertIn('web-extra', names)

    def test_empty_directory(self):
        empty = self.tmpdir / 'empty'
        empty.mkdir()

        strategy = FlatDiscovery(empty, self.target)
        result = strategy.discover()

        self.assertEqual(len(result), 0)


if __name__ == '__main__':
    unittest.main()
