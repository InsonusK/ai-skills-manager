"""Command-line interface."""

import sys
import argparse
from pathlib import Path

from .core import SkillSync

DEFAULT_CONFIG = "ai-skills.yaml"


def main():
    parser = argparse.ArgumentParser(
        prog='ai-skills-sync',
        description='Sync AI skills into .agents/skills/',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ai-skills-sync                          # Use ai-skills.yaml
  ai-skills-sync -c config.yaml           # Custom config
  ai-skills-sync --dry-run                # Preview only
        """
    )
    parser.add_argument('-c', '--config', default=DEFAULT_CONFIG,
                        help=f'Config file (default: {DEFAULT_CONFIG})')
    parser.add_argument('--target', help='Override target directory')
    parser.add_argument('--on-conflict', choices=['error', 'last_wins'],
                        help='Conflict resolution')
    parser.add_argument('--remove-orphans', action='store_true', default=None,
                        help='Remove orphan skills')
    parser.add_argument('--keep-orphans', action='store_true',
                        help='Keep orphan skills')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes')

    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    if not config_path.exists():
        print(f"❌ Config not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    # Determine remove_orphans
    remove = None
    if args.remove_orphans:
        remove = True
    elif args.keep_orphans:
        remove = False

    try:
        sync = SkillSync(
            config_file=config_path,
            target_dir=Path(args.target) if args.target else None,
            on_conflict=args.on_conflict or 'error',
            remove_orphans=remove if remove is not None else True,
            dry_run=args.dry_run
        )

        result = sync.sync()

        print(f"\n📊 Synced: {result['synced_count']} skills")

        if result['fix_summary']:
            print(f"\n🔗 Links:")
            for status, count in sorted(result['fix_summary'].items()):
                emoji = {'fixed': '✅', 'external': '🔗', 'broken': '⚠️'}.get(status, '?')
                print(f"   {emoji} {status}: {count}")

        if result['dry_run']:
            print(f"\n🏃 Dry run - no changes")

    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
