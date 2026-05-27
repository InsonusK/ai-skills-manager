"""Command-line interface."""

import argparse

from .commands import sync, new


def main():
    parser = argparse.ArgumentParser(
        prog='ai-skills',
        description='AI skills manager CLI',
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    sync.add_parser(subparsers)
    new.add_parser(subparsers)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
