# Configuration

The configuration file controls where skills are discovered and how they are synchronized.

## File format

The config file can be **YAML** (`.yaml` / `.yml`) or **JSON** (`.json`).

Default file name: `ai-skills.yaml`

## Top-level structure

```yaml
sources:
  - path: ./my-skills
    type: auto

settings:
  target: .agents/skills
  remove_orphans: true
  on_conflict: error
  dry_run: false
```

## `sources`

List of source locations to scan for skills. Each source is a dictionary with the following fields:

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `path` | Yes | — | Directory path relative to the config file |
| `type` | No | `auto` | Discovery strategy: `auto`, `flat`, or `directory` |
| `name` | No | — | Explicit skill name override |

### Discovery types

#### `auto`
Recursively scans the source directory:
- If a directory contains `SKILL.md`, it is treated as a **directory** skill.
- Otherwise, each `.md` file becomes a **flat** skill, and subdirectories are scanned recursively.

#### `flat`
Every `.md` file (recursively) is treated as an individual skill. Each file is copied into its own target directory as `SKILL.md`.

Example source:
```
my-skills/
  guide.md
  tips.md
```

Result target:
```
.agents/skills/
  guide/SKILL.md
  tips/SKILL.md
```

#### `directory`
Expects subdirectories that contain a `SKILL.md` file. The entire directory is copied as-is to the target.

Example source:
```
my-skills/
  web/
    SKILL.md
    extra.md
```

Result target:
```
.agents/skills/
  web/
    SKILL.md
    extra.md
```

## `settings`

Global settings that apply to the synchronization.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `target` | string | `.agents/skills` | Target directory relative to the config file |
| `remove_orphans` | boolean | `true` | Remove skills in the target that are no longer defined in the config |
| `on_conflict` | string | `error` | How to handle duplicate skill names: `error` or `last_wins` |
| `dry_run` | boolean | `false` | When `true`, preview changes without writing anything |

### Conflict resolution

- `error` — raise an error if two sources produce the same skill name.
- `last_wins` — the last source in the list wins.

CLI flags (`--target`, `--on-conflict`, `--remove-orphans`, `--keep-orphans`, `--dry-run`) override the config file values.
