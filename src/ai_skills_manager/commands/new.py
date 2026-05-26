"""New skill command."""

import sys
from pathlib import Path

SKILL_TEMPLATE = """---
name: {name}
description: _skill description_
version: 1.0.0
---

# When use skill
_Usecase when skill applied_

# Goal
_Goal of applying this skill_

# Requirements
_What ai agent should define before apply skill_

# Implementation
_Implementation plan_
"""


def add_parser(subparsers):
    parser = subparsers.add_parser(
        'new',
        help='Create a new skill',
    )
    parser.add_argument('skill_name', help='Name of the new skill')
    parser.add_argument('path', help='Path to the folder where the skill will be created')
    parser.add_argument(
        '--type', choices=['flat', 'dir'], default='dir',
        help='Skill type: flat (single SKILL.md file) or dir (skill folder with SKILL.md inside)'
    )
    parser.set_defaults(func=run)
    return parser


def run(args):
    skill_name = args.skill_name
    skill_path = Path(args.path).resolve()

    # Ensure parent directory exists
    skill_path.parent.mkdir(parents=True, exist_ok=True)

    if args.type == 'flat':
        # Flat skill: create as a single file named <skill_name>.md
        if skill_path.is_dir():
            target_file = skill_path / f"{skill_name}.md"
        else:
            target_file = skill_path

        if target_file.exists():
            print(f"❌ File already exists: {target_file}", file=sys.stderr)
            sys.exit(1)

        target_file.write_text(SKILL_TEMPLATE.format(name=skill_name), encoding='utf-8')
        print(f"✅ Created flat skill: {target_file}")
    else:
        # Dir skill: create a folder with SKILL.md inside
        if skill_path.exists():
            print(f"❌ Path already exists: {skill_path}", file=sys.stderr)
            sys.exit(1)

        skill_path.mkdir(parents=True, exist_ok=False)
        target_file = skill_path / 'SKILL.md'
        target_file.write_text(SKILL_TEMPLATE.format(name=skill_name), encoding='utf-8')
        print(f"✅ Created directory skill: {skill_path}/")
