"""GitHub source discovery strategy.

Downloads a GitHub repository archive, extracts it to a temp directory,
and delegates to the appropriate local discovery strategy on a subfolder.
"""

import re
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import List

from .auto import AutoDiscovery
from .base import DiscoveryStrategy, SkillMapping
from .directory import DirectoryDiscovery
from .flat import FlatDiscovery


_GITHUB_URL_PATTERNS = [
    # https://github.com/owner/repo.git
    re.compile(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$"),
    # git@github.com:owner/repo.git
    re.compile(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?/?$"),
]

_SCAN_MAP = {
    "auto": AutoDiscovery,
    "flat": FlatDiscovery,
    "dir": DirectoryDiscovery,
}


def _parse_github_url(url: str) -> tuple:
    """Extract (owner, repo) from a GitHub URL."""
    for pattern in _GITHUB_URL_PATTERNS:
        match = pattern.match(url)
        if match:
            return match.group(1), match.group(2)
    raise ValueError(f"Invalid GitHub repository URL: {url}")


def _download_archive(owner: str, repo: str, tree: str) -> Path:
    """Download repo archive tarball to a temp file."""
    archive_url = f"https://github.com/{owner}/{repo}/archive/{tree}.tar.gz"
    fd, tmp_path = tempfile.mkstemp(suffix=".tar.gz")
    try:
        with urllib.request.urlopen(archive_url, timeout=60) as response:
            with open(fd, "wb") as f:
                shutil.copyfileobj(response, f)
    except Exception:
        # Clean up the temp file on error
        Path(tmp_path).unlink(missing_ok=True)
        raise
    return Path(tmp_path)


def _extract_archive(archive_path: Path, extract_to: Path) -> None:
    """Extract a tar.gz archive."""
    with tarfile.open(archive_path, "r:gz") as tar:
        # filter available in Python 3.12+; suppresses deprecation warning
        kwargs = {"filter": "fully_trusted"} if hasattr(tarfile, "TarFile") else {}
        if hasattr(tarfile, "data_filter"):
            kwargs = {"filter": "fully_trusted"}
        tar.extractall(path=extract_to, **kwargs)


def _find_extracted_root(extract_to: Path) -> Path:
    """Find the single top-level directory created by GitHub archive extraction."""
    entries = [e for e in extract_to.iterdir() if e.is_dir()]
    if len(entries) != 1:
        raise RuntimeError(
            f"Expected exactly one top-level directory in extracted archive, found {len(entries)}"
        )
    return entries[0]


class GitHubDiscovery(DiscoveryStrategy):
    """Discover skills from a GitHub repository.

    Downloads the repo archive for the specified tree/branch, extracts it,
    and delegates discovery to the configured scan strategy on the subfolder.
    """

    def __init__(
        self,
        source_path,
        target_dir: Path,
        tree: str = "master",
        subfolder: str = "skills",
        scan: str = "auto",
    ):
        # source_path is the repo URL (str or Path-like); avoid base resolve()
        self.repo_url = str(source_path)
        self.target_dir = target_dir
        self.tree = tree
        self.subfolder = subfolder
        self.scan = scan

    def discover(self) -> List[SkillMapping]:
        """Download repo, extract, and discover skills."""
        owner, repo = _parse_github_url(self.repo_url)

        archive_path = _download_archive(owner, repo, self.tree)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                extract_to = Path(tmpdir)
                _extract_archive(archive_path, extract_to)

                repo_root = _find_extracted_root(extract_to)
                scan_path = repo_root / self.subfolder

                if not scan_path.exists():
                    return []

                strategy_class = _SCAN_MAP.get(self.scan, AutoDiscovery)
                strategy = strategy_class(scan_path, self.target_dir)
                return strategy.discover()
        finally:
            archive_path.unlink(missing_ok=True)
