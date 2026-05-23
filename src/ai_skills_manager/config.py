"""Configuration loading."""

import json
from pathlib import Path


def load_config(config_path: Path) -> dict:
    """Load YAML or JSON config file."""
    content = config_path.read_text(encoding='utf-8')

    if config_path.suffix in ('.yaml', '.yml'):
        try:
            import yaml
            return yaml.safe_load(content)
        except ImportError:
            raise ImportError("PyYAML required for .yaml files. Install: pip install pyyaml")

    return json.loads(content)
