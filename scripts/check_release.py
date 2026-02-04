#!/usr/bin/env python
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _read_version_py(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not m:
        raise ValueError(f"Unable to find __version__ in {path}")
    return m.group(1).strip()


def _read_pyproject_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.search(r'^\s*version\s*=\s*"([^"]+)"\s*$', text, re.MULTILINE)
    if not m:
        raise ValueError(f"Unable to find version in {path}")
    return m.group(1).strip()


def _has_changelog_version(changelog: str, version: str) -> bool:
    pattern = re.compile(rf"^##\s*\[{re.escape(version)}\]\s*(?:-|$)", re.MULTILINE)
    return bool(pattern.search(changelog))


def _has_unreleased(changelog: str) -> bool:
    pattern = re.compile(r"^##\s*\[Unreleased\]\s*$", re.MULTILINE)
    return bool(pattern.search(changelog))


def main() -> int:
    parser = argparse.ArgumentParser(description="Release consistency checks")
    parser.add_argument("--require-version", action="store_true", help="Require CHANGELOG to include current version")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    version_py = root / "onceonly" / "version.py"
    pyproject = root / "pyproject.toml"
    changelog = root / "CHANGELOG.md"

    version = _read_version_py(version_py)
    pyproject_version = _read_pyproject_version(pyproject)

    if version != pyproject_version:
        print(f"Version mismatch: onceonly/version.py={version} vs pyproject.toml={pyproject_version}")
        return 1

    if not changelog.exists():
        print("Missing CHANGELOG.md")
        return 1

    changelog_text = changelog.read_text(encoding="utf-8")
    has_version = _has_changelog_version(changelog_text, version)
    has_unreleased = _has_unreleased(changelog_text)

    if args.require_version and not has_version:
        print(f"CHANGELOG.md missing version entry: {version}")
        return 1

    if not (has_version or has_unreleased):
        print("CHANGELOG.md missing [Unreleased] and current version entry")
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
