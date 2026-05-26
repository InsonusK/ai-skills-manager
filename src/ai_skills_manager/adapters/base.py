"""Base class for file adapters."""

from abc import ABC, abstractmethod
from pathlib import Path


class FileAdapter(ABC):
    """Adapts files after copying to target."""

    @property
    @abstractmethod
    def version(self) -> int:
        """Adapter version for change detection."""
        pass

    @abstractmethod
    def adapt(self, filepath: Path) -> None:
        """Modify file in place after copying."""
        pass
