"""Tests for config module."""

import unittest
import tempfile
import json
from pathlib import Path

from ai_skills_manager.config import load_config


class TestLoadConfig(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_load_json(self):
        config_file = self.tmpdir / 'config.json'
        config_file.write_text(json.dumps({'key': 'value', 'num': 42}))

        result = load_config(config_file)
        self.assertEqual(result['key'], 'value')
        self.assertEqual(result['num'], 42)

    def test_load_yaml(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML not installed")

        config_file = self.tmpdir / 'config.yaml'
        config_file.write_text('key: value\nnum: 42\n')

        result = load_config(config_file)
        self.assertEqual(result['key'], 'value')
        self.assertEqual(result['num'], 42)

    def test_load_yml_extension(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML not installed")

        config_file = self.tmpdir / 'config.yml'
        config_file.write_text('test: true\n')

        result = load_config(config_file)
        self.assertTrue(result['test'])

    def test_load_invalid_json(self):
        config_file = self.tmpdir / 'bad.json'
        config_file.write_text('not json {')

        with self.assertRaises(json.JSONDecodeError):
            load_config(config_file)


if __name__ == '__main__':
    unittest.main()
