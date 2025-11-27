#!/usr/bin/env python3
"""
Helper script to run: git pull → git add → git commit → git push.

Usage:
    python git_sync.py -m "Your commit message"
If -m is omitted, you will be prompted (defaults to a timestamp-based message).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import subprocess
import sys
from typing import List


def run_git(args: List[str], *, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command and stream its output."""
    cmd = ["git", *args]
    print(f"$ {' '.join(cmd)}", flush=True)
    completed = subprocess.run(cmd, check=False)
    if check and completed.returncode != 0:
        raise subprocess.CalledProcessError(completed.returncode, cmd)
    return completed


def working_tree_dirty() -> bool:
    """Return True if there are staged changes after running git add."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pull latest changes, stage everything, commit, and push."
    )
    parser.add_argument(
        "-m",
        "--message",
        help="Commit message to use. Defaults to a timestamped message.",
    )
    parser.add_argument(
        "--skip-pull",
        action="store_true",
        help="Skip the initial git pull step.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.skip_pull:
        run_git(["pull"])

    run_git(["add", "-A"])

    if not working_tree_dirty():
        print("No changes to commit. Skipping commit/push.")
        return 0

    message = args.message
    if not message:
        try:
            message = input(
                "Enter commit message (leave blank to auto-generate): "
            ).strip()
        except EOFError:
            message = ""

    if not message:
        message = f"Update { _dt.datetime.now().strftime('%Y-%m-%d %H:%M') }"

    run_git(["commit", "-m", message])
    run_git(["push"])
    print("All done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
