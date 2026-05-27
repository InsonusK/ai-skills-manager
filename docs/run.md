# Running

## Basic usage

By default, the tool looks for `ai-skills.yaml` in the current directory and syncs skills to `.agents/skills/` relative to the config file.

```bash
# Use default config (ai-skills.yaml)
ai-skills

# Or run via module
python -m ai_skills_manager.cli
```

## Custom config file

```bash
ai-skills -c ./config/my-skills.yaml
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
ai-skills --dry-run
```

### Override target directory

```bash
ai-skills --target ./my-skills
```

### Force orphan removal

```bash
ai-skills --remove-orphans
```

### Keep orphan skills

```bash
ai-skills --keep-orphans
```

### Set conflict resolution

```bash
ai-skills --on-conflict last_wins
```
