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
from ai_skills_manager.core import copy_skill


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

    def test_discover_flat_files(self):
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
                subpath="skills",
            )
            result = strategy.discover()

        self.assertEqual(len(result), 2)
        names = {r.skill_name for r in result}
        self.assertEqual(names, {"guide", "tips"})

    def test_discover_directory_skills(self):
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
                subpath="skills",
            )
            result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, "web")
        self.assertFalse(result[0].is_flat)

    def test_missing_subpath_returns_empty(self):
        archive = _make_fake_archive(
            "repo-main",
            {"other/readme.md": "# Readme"},
        )

        with self._mock_download(archive):
            strategy = GitHubDiscovery(
                "https://github.com/owner/repo",
                self.target,
                tree="main",
                subpath="skills",
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
                subpath="skills",
            )
            result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, "a")

    def test_default_subpath_skills(self):
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
                subpath="skills",
            )
            result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, "x")

    def test_discover_source_paths_remain_valid_after_return(self):
        """Regression test: source_path must point to real files after discover() returns.

        Previously the extracted temp directory was cleaned up inside the
        discover() method, so callers got dangling paths.
        """
        archive = _make_fake_archive(
            "repo-main",
            {
                "skills/version-control/SKILL.md": "# Version Control",
                "skills/version-control/extra.md": "# Extra",
            },
        )

        with self._mock_download(archive):
            strategy = GitHubDiscovery(
                "https://github.com/owner/repo",
                self.target,
                tree="main",
                subpath="skills",
            )
            result = strategy.discover()

        self.assertEqual(len(result), 1)
        mapping = result[0]
        self.assertEqual(mapping.skill_name, "version-control")
        self.assertFalse(mapping.is_flat)

        # The source_path must still exist after discover() returned
        self.assertTrue(mapping.source_path.exists())
        self.assertTrue((mapping.source_path / "SKILL.md").exists())
        self.assertEqual(
            (mapping.source_path / "SKILL.md").read_text(),
            "# Version Control",
        )

    def test_discover_and_copy_directory_skill(self):
        """End-to-end: discover from GitHub archive and copy skill to target."""
        archive = _make_fake_archive(
            "repo-main",
            {
                "skills/version-control/SKILL.md": "# Version Control",
                "skills/version-control/extra.md": "# Extra",
            },
        )

        with self._mock_download(archive):
            strategy = GitHubDiscovery(
                "https://github.com/owner/repo",
                self.target,
                tree="main",
                subpath="skills",
            )
            result = strategy.discover()

        self.assertEqual(len(result), 1)
        mapping = result[0]

        copy_skill(mapping, dry_run=False)

        # Verify the skill was copied into the target directory
        skill_dir = self.target / "version-control"
        self.assertTrue(skill_dir.exists())
        self.assertTrue((skill_dir / "SKILL.md").exists())
        self.assertEqual((skill_dir / "SKILL.md").read_text(), "# Version Control")
        self.assertTrue((skill_dir / "extra.md").exists())
        self.assertEqual((skill_dir / "extra.md").read_text(), "# Extra")

    def test_discover_single_md_file(self):
        """A single .md file selected via subpath is treated as a flat skill."""
        archive = _make_fake_archive(
            "repo-main",
            {
                "skills/nested/guide.md": "# Guide",
            },
        )

        with self._mock_download(archive):
            strategy = GitHubDiscovery(
                "https://github.com/owner/repo",
                self.target,
                tree="main",
                subpath="skills/nested/guide.md",
            )
            result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, "guide")
        self.assertTrue(result[0].is_flat)
        self.assertTrue(result[0].source_path.exists())

    def test_discover_single_md_file_copies_correctly(self):
        """End-to-end: discover a single .md file and copy it as a flat skill."""
        archive = _make_fake_archive(
            "repo-main",
            {
                "docs/quickstart.md": "# Quickstart",
            },
        )

        with self._mock_download(archive):
            strategy = GitHubDiscovery(
                "https://github.com/owner/repo",
                self.target,
                tree="main",
                subpath="docs/quickstart.md",
            )
            result = strategy.discover()

        self.assertEqual(len(result), 1)
        mapping = result[0]
        self.assertEqual(mapping.skill_name, "quickstart")
        self.assertTrue(mapping.is_flat)

        copy_skill(mapping, dry_run=False)

        skill_dir = self.target / "quickstart"
        self.assertTrue(skill_dir.exists())
        self.assertTrue((skill_dir / "SKILL.md").exists())
        self.assertEqual((skill_dir / "SKILL.md").read_text(), "# Quickstart")

    def test_discover_single_nonexistent_file_returns_empty(self):
        """Selecting a missing file returns an empty list."""
        archive = _make_fake_archive(
            "repo-main",
            {"skills/guide.md": "# Guide"},
        )

        with self._mock_download(archive):
            strategy = GitHubDiscovery(
                "https://github.com/owner/repo",
                self.target,
                tree="main",
                subpath="skills/missing.md",
            )
            result = strategy.discover()

        self.assertEqual(len(result), 0)

    def test_discover_multiple_subpaths(self):
        """Multiple subpaths can be provided as a list."""
        archive = _make_fake_archive(
            "repo-main",
            {
                "skills/web/SKILL.md": "# Web",
                "docs/guide.md": "# Guide",
            },
        )

        with self._mock_download(archive):
            strategy = GitHubDiscovery(
                "https://github.com/owner/repo",
                self.target,
                tree="main",
                subpath=["skills", "docs"],
            )
            result = strategy.discover()

        self.assertEqual(len(result), 2)
        names = {r.skill_name for r in result}
        self.assertEqual(names, {"web", "guide"})

    def test_discover_multiple_subpaths_mixed(self):
        """A list of subpaths can contain both directories and single .md files."""
        archive = _make_fake_archive(
            "repo-main",
            {
                "skills/web/SKILL.md": "# Web",
                "docs/quickstart.md": "# Quickstart",
            },
        )

        with self._mock_download(archive):
            strategy = GitHubDiscovery(
                "https://github.com/owner/repo",
                self.target,
                tree="main",
                subpath=["skills", "docs/quickstart.md"],
            )
            result = strategy.discover()

        self.assertEqual(len(result), 2)
        by_name = {r.skill_name: r for r in result}
        self.assertIn("web", by_name)
        self.assertFalse(by_name["web"].is_flat)
        self.assertIn("quickstart", by_name)
        self.assertTrue(by_name["quickstart"].is_flat)

    def test_discover_multiple_subpaths_skips_missing(self):
        """Missing subpaths in a list are skipped rather than failing."""
        archive = _make_fake_archive(
            "repo-main",
            {
                "skills/guide.md": "# Guide",
            },
        )

        with self._mock_download(archive):
            strategy = GitHubDiscovery(
                "https://github.com/owner/repo",
                self.target,
                tree="main",
                subpath=["missing", "skills"],
            )
            result = strategy.discover()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].skill_name, "guide")


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
