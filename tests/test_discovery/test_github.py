"""Tests for GitHubDiscovery strategy."""

import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_skills_manager.discovery.github import (
    GitHubDiscovery,
    _parse_github_url,
    _find_extracted_root,
)
from ai_skills_manager.discovery.auto import AutoDiscovery
from ai_skills_manager.discovery.flat import FlatDiscovery
from ai_skills_manager.discovery.directory import DirectoryDiscovery


def _make_fake_archive(repo_name: str, files: dict) -> bytes:
    """Create a tar.gz archive in memory.

    files: dict of {path_inside_repo: content}
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for rel_path, content in files.items():
            arcname = f"{repo_name}/{rel_path}"
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=arcname)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class TestParseGitHubUrl(unittest.TestCase):
    def test_https_with_git_suffix(self):
        self.assertEqual(
            _parse_github_url("https://github.com/owner/repo.git"),
            ("owner", "repo"),
        )

    def test_https_without_git_suffix(self):
        self.assertEqual(
            _parse_github_url("https://github.com/owner/repo"),
            ("owner", "repo"),
        )

    def test_https_with_trailing_slash(self):
        self.assertEqual(
            _parse_github_url("https://github.com/owner/repo/"),
            ("owner", "repo"),
        )

    def test_ssh_format(self):
        self.assertEqual(
            _parse_github_url("git@github.com:owner/repo.git"),
            ("owner", "repo"),
        )

    def test_invalid_url_raises(self):
        with self.assertRaises(ValueError):
            _parse_github_url("https://example.com/not-github")


class TestGitHubDiscovery(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.target = self.tmpdir / "target"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def _mock_download(self, archive_bytes: bytes):
        """Return a patcher that replaces _download_archive with a writer of archive_bytes."""
        def fake_download(owner, repo, tree):
            path = self.tmpdir / "fake_archive.tar.gz"
            path.write_bytes(archive_bytes)
            return path

        return patch(
            "ai_skills_manager.discovery.github._download_archive",
            side_effect=fake_download,
        )

    def test_discover_auto_flat_files(self):
        archive = _make_fake_archive(
            "repo-main",
            {
                "skills/guide.md": "# Guide",
                "skills/tips.md": "# Tips",
            },
        )

        with self._mock_download(archive):
            strategy = GitHubDiscovery(
                "https://github.com/owner/repo",
                self.target,
                tree="main",
                subfolder="skills",
                scan="auto",
            )
            result = strategy.discover()

        self.assertEqual(len(result), 2)
        names = {r.skill_name for r in result}
        self.assertEqual(names, {"guide", "tips"})

    def test_discover_auto_directory_skills(self):
        archive = _make_fake_archive(
            "repo-main",
            {
                "skills/web/SKILL.md": "# Web",
                "skills/web/extra.md": "# Extra",
            },
        )

        with self._mock_download(archive):
            strategy = GitHubDiscovery(
                "https://github.com/owner/repo",
                self.target,
                tree="main",
                subfolder="skills",
                scan="auto",
            )
            result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, "web")
        self.assertFalse(result[0].is_flat)

    def test_discover_flat_scan(self):
        archive = _make_fake_archive(
            "repo-main",
            {
                "skills/nested/SKILL.md": "# Nested",
                "skills/top.md": "# Top",
            },
        )

        with self._mock_download(archive):
            strategy = GitHubDiscovery(
                "https://github.com/owner/repo",
                self.target,
                tree="main",
                subfolder="skills",
                scan="flat",
            )
            result = strategy.discover()

        names = {r.skill_name for r in result}
        self.assertEqual(names, {"nested-SKILL", "top"})
        for mapping in result:
            self.assertTrue(mapping.is_flat)

    def test_discover_dir_scan(self):
        archive = _make_fake_archive(
            "repo-main",
            {
                "skills/web/SKILL.md": "# Web",
                "skills/api/SKILL.md": "# API",
            },
        )

        with self._mock_download(archive):
            strategy = GitHubDiscovery(
                "https://github.com/owner/repo",
                self.target,
                tree="main",
                subfolder="skills",
                scan="dir",
            )
            result = strategy.discover()

        names = {r.skill_name for r in result}
        self.assertEqual(names, {"web", "api"})
        for mapping in result:
            self.assertFalse(mapping.is_flat)

    def test_missing_subfolder_returns_empty(self):
        archive = _make_fake_archive(
            "repo-main",
            {"other/readme.md": "# Readme"},
        )

        with self._mock_download(archive):
            strategy = GitHubDiscovery(
                "https://github.com/owner/repo",
                self.target,
                tree="main",
                subfolder="skills",
                scan="auto",
            )
            result = strategy.discover()

        self.assertEqual(len(result), 0)

    def test_default_tree_master(self):
        archive = _make_fake_archive(
            "repo-master",
            {"skills/a.md": "# A"},
        )

        with self._mock_download(archive):
            strategy = GitHubDiscovery(
                "https://github.com/owner/repo",
                self.target,
                subfolder="skills",
            )
            result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, "a")

    def test_default_subfolder_skills(self):
        archive = _make_fake_archive(
            "repo-main",
            {"skills/b.md": "# B"},
        )

        with self._mock_download(archive):
            strategy = GitHubDiscovery(
                "https://github.com/owner/repo",
                self.target,
                tree="main",
            )
            result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, "b")

    def test_default_scan_auto(self):
        archive = _make_fake_archive(
            "repo-main",
            {"skills/c.md": "# C"},
        )

        with self._mock_download(archive):
            strategy = GitHubDiscovery(
                "https://github.com/owner/repo",
                self.target,
                tree="main",
                subfolder="skills",
            )
            result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, "c")

    def test_ssh_url_accepted(self):
        archive = _make_fake_archive(
            "repo-main",
            {"skills/x.md": "# X"},
        )

        with self._mock_download(archive):
            strategy = GitHubDiscovery(
                "git@github.com:owner/repo.git",
                self.target,
                tree="main",
                subfolder="skills",
                scan="auto",
            )
            result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, "x")


class TestFindExtractedRoot(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_single_directory(self):
        (self.tmpdir / "repo-main").mkdir()
        root = _find_extracted_root(self.tmpdir)
        self.assertEqual(root.name, "repo-main")

    def test_multiple_directories_raises(self):
        (self.tmpdir / "a").mkdir()
        (self.tmpdir / "b").mkdir()
        with self.assertRaises(RuntimeError):
            _find_extracted_root(self.tmpdir)


if __name__ == "__main__":
    unittest.main()
