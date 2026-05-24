# Installation

## Requirements

- Python 3.9 or newer
- `pip`

## Install from source (development)

Clone the repository and install in editable mode:

```bash
git clone https://github.com/InsonusK/ai-skills-manager
cd ai-skill-manager
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

This installs the package along with its runtime dependency (`pyyaml`).

## Install dependencies only

If you prefer to run the code without installing the package, install the requirements file:

```bash
pip install -r requirements.txt
```

## Verify installation

After installation, the `ai-skills-sync` command should be available:

```bash
ai-skills-sync --help
```

Or run the CLI module directly:

```bash
python -m ai_skills_manager.cli --help
```
