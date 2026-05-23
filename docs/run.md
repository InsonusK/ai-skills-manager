# Running

## Basic usage

By default, the tool looks for `ai-skills.yaml` in the current directory and syncs skills to `.agents/skills/` relative to the config file.

```bash
# Use default config (ai-skills.yaml)
ai-skills-sync

# Or run via module
python -m ai_skills_manager.cli
```

## Custom config file

```bash
ai-skills-sync -c ./config/my-skills.yaml
```

## Common options

| Option | Description |
|--------|-------------|
| `-c, --config` | Path to config file (default: `ai-skills.yaml`) |
| `--target` | Override the target directory |
| `--on-conflict` | Conflict resolution: `error` or `last_wins` |
| `--remove-orphans` | Remove skills not present in config |
| `--keep-orphans` | Keep skills not present in config |
| `--dry-run` | Preview changes without applying them |

## Examples

### Preview changes

```bash
ai-skills-sync --dry-run
```

### Override target directory

```bash
ai-skills-sync --target ./my-skills
```

### Force orphan removal

```bash
ai-skills-sync --remove-orphans
```

### Keep orphan skills

```bash
ai-skills-sync --keep-orphans
```

### Set conflict resolution

```bash
ai-skills-sync --on-conflict last_wins
```
