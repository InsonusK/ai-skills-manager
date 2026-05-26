"""Tests for CLI and commands."""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
import io

from ai_skills_manager.cli import main
from ai_skills_manager.commands.new import SKILL_TEMPLATE, run as new_run


class TestNewCommand(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_create_dir_skill(self):
        args = type('Args', (), {
            'skill_name': 'test-skill',
            'path': str(self.tmp / 'test-skill'),
            'type': 'dir',
        })()
        new_run(args)

        skill_dir = self.tmp / 'test-skill'
        self.assertTrue(skill_dir.exists())
        self.assertTrue(skill_dir.is_dir())

        skill_file = skill_dir / 'SKILL.md'
        self.assertTrue(skill_file.exists())
        content = skill_file.read_text(encoding='utf-8')
        self.assertIn('name: test-skill', content)
        self.assertIn('# When use skill', content)

    def test_create_flat_skill(self):
        args = type('Args', (), {
            'skill_name': 'test-skill',
            'path': str(self.tmp / 'test-skill.md'),
            'type': 'flat',
        })()
        new_run(args)

        skill_file = self.tmp / 'test-skill.md'
        self.assertTrue(skill_file.exists())
        content = skill_file.read_text(encoding='utf-8')
        self.assertIn('name: test-skill', content)
        self.assertIn('# When use skill', content)

    def test_create_flat_skill_in_directory(self):
        args = type('Args', (), {
            'skill_name': 'test-skill',
            'path': str(self.tmp),
            'type': 'flat',
        })()
        new_run(args)

        skill_file = self.tmp / 'test-skill.md'
        self.assertTrue(skill_file.exists())

    def test_dir_skill_already_exists(self):
        (self.tmp / 'test-skill').mkdir()
        args = type('Args', (), {
            'skill_name': 'test-skill',
            'path': str(self.tmp / 'test-skill'),
            'type': 'dir',
        })()

        with self.assertRaises(SystemExit) as cm:
            new_run(args)
        self.assertEqual(cm.exception.code, 1)

    def test_flat_skill_already_exists(self):
        (self.tmp / 'test-skill.md').write_text('existing')
        args = type('Args', (), {
            'skill_name': 'test-skill',
            'path': str(self.tmp / 'test-skill.md'),
            'type': 'flat',
        })()

        with self.assertRaises(SystemExit) as cm:
            new_run(args)
        self.assertEqual(cm.exception.code, 1)


class TestCLIEntrypoint(unittest.TestCase):
    def test_help_shows_subcommands(self):
        with patch('sys.argv', ['ai-skills-sync', '--help']):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 0)

    def test_sync_help(self):
        with patch('sys.argv', ['ai-skills-sync', 'sync', '--help']):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 0)

    def test_new_help(self):
        with patch('sys.argv', ['ai-skills-sync', 'new', '--help']):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 0)
