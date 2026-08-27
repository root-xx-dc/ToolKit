"""
rootx.git_helper
================
Git repository helper. Requires git CLI.
Prerequisite: utils.command_exists("git")
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

from . import utils


@dataclass
class GitRepo:
    path: str
    name: str
    branch: str = ""


@dataclass
class GitStatus:
    repo: str
    branch: str
    changes: List[str] = field(default_factory=list)
    raw: str = ""


def is_available() -> bool:
    return utils.command_exists("git")


def detect_repos(path: str, max_depth: int = 2) -> List[GitRepo]:
    """Walk up to max_depth levels to find .git directories."""
    repos: List[GitRepo] = []
    path = os.path.expanduser(path)
    try:
        for root, dirs, _ in os.walk(path):
            rel = os.path.relpath(root, path)
            depth = 0 if rel == "." else rel.count(os.sep) + 1
            if depth > max_depth:
                dirs.clear()
                continue
            if ".git" in dirs:
                name = os.path.basename(root)
                repos.append(GitRepo(path=root, name=name))
                dirs.remove(".git")
    except Exception:
        pass
    return repos


def _get_branch(repo_path: str) -> str:
    result = utils.run(["git", "-C", repo_path, "branch", "--show-current"], timeout=10)
    return result.stdout.strip() if result.ok else ""


def status(repo_path: str) -> GitStatus:
    """Get git status --short for a repo."""
    branch = _get_branch(repo_path)
    result = utils.run(["git", "-C", repo_path, "status", "--short"], timeout=10)
    changes = result.stdout.splitlines() if result.ok else []
    return GitStatus(repo=repo_path, branch=branch, changes=changes, raw=result.stdout)


def log(repo_path: str, lines: int = 10) -> str:
    """Get git log --oneline -N."""
    result = utils.run(["git", "-C", repo_path, "log", "--oneline", f"-{lines}"], timeout=10)
    return result.stdout or result.error or "No commits found."


def stash(repo_path: str) -> utils.CommandResult:
    return utils.run(["git", "-C", repo_path, "stash"], timeout=15)


def stash_pop(repo_path: str) -> utils.CommandResult:
    return utils.run(["git", "-C", repo_path, "stash", "pop"], timeout=15)


def quick_commit(repo_path: str, message: str) -> utils.CommandResult:
    """git add -A && git commit -m message."""
    stage = utils.run(["git", "-C", repo_path, "add", "-A"], timeout=15)
    if not stage.ok:
        return stage
    return utils.run(["git", "-C", repo_path, "commit", "-m", message], timeout=15)


def diff_stat(repo_path: str) -> str:
    """Get git diff --staged --stat."""
    result = utils.run(["git", "-C", repo_path, "diff", "--staged", "--stat"], timeout=10)
    return result.stdout or "No staged changes."


def pull(repo_path: str) -> utils.CommandResult:
    return utils.run(["git", "-C", repo_path, "pull"], timeout=60)


def push(repo_path: str) -> utils.CommandResult:
    return utils.run(["git", "-C", repo_path, "push"], timeout=60)
