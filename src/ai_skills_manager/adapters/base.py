"""Base class for file adapters."""

from abc import ABC, abstractmethod
from pathlib import Path


class FileAdapter(ABC):
    """Adapts files after copying to target."""

    @abstractmethod
    def adapt(self, filepath: Path) -> None:
        """Modify file in place after copying."""
        pass
