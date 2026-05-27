# AI Skills Manager

Sync AI agent skills into `.agents/skills/` from local directories or GitHub repositories.

## Quick start

Create an `ai-skills.yaml` config in your project root:

```yaml
sources:
  - path: ./my-skills
    type: auto

settings:
  target: .agents/skills
  remove_orphans: true
  on_conflict: error
```

Run the sync:

```bash
ai-skills-sync
```

## Documentation

- [Installation](docs/install.md)
- [Running](docs/run.md)
- [Configuration](docs/config.md)

## What it does

- Discovers skills from local directories (`auto`, `flat`, `directory`) or GitHub repositories.
- Copies them to a target directory (default: `.agents/skills`).
- Removes orphan skills that are no longer in the config (optional).
- Updates internal links so they point to the correct target paths.
- Supports dry-run mode to preview changes safely.

## Skill types

### `flat`
Each `.md` file becomes its own skill directory with a `SKILL.md` inside.

```
my-skills/
  guide.md   → .agents/skills/guide/SKILL.md
  tips.md    → .agents/skills/tips/SKILL.md
```

### `directory`
Each subdirectory containing `SKILL.md` is copied as-is.

```
my-skills/
  web/
    SKILL.md   → .agents/skills/web/SKILL.md
    extra.md   → .agents/skills/web/extra.md
```

### `auto` (default)
Automatically detects whether a directory should be treated as `directory` (contains `SKILL.md`) or `flat`.
