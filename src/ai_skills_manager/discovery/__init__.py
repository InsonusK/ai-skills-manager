"""Skill discovery strategies."""

from .base import SkillMapping, DiscoveryStrategy
from .auto import AutoDiscovery
from .flat import FlatDiscovery
from .directory import DirectoryDiscovery
from .github import GitHubDiscovery

__all__ = [
    "SkillMapping",
    "DiscoveryStrategy", 
    "AutoDiscovery",
    "FlatDiscovery",
    "DirectoryDiscovery",
    "GitHubDiscovery",
]
