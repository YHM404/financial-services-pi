#!/usr/bin/env python3
"""Validate the pi package adapter manifest and resources.

This intentionally checks pi-facing packaging rules, not Claude plugin rules.
"""

from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
ARG_RE = re.compile(r"\$(?:ARGUMENTS|@|\d+)")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def warn(message: str) -> None:
    print(f"WARN: {message}", file=sys.stderr)


def load_package() -> dict:
    package_file = ROOT / "package.json"
    if not package_file.exists():
        fail("package.json is missing")
    package = json.loads(package_file.read_text())
    if "pi-package" not in package.get("keywords", []):
        fail("package.json keywords must include pi-package")
    pi = package.get("pi")
    if not isinstance(pi, dict):
        fail("package.json must contain a pi manifest")
    for key in ("skills", "prompts"):
        if not isinstance(pi.get(key), list) or not pi[key]:
            fail(f"package.json pi.{key} must be a non-empty list")
    return package


def expand_patterns(patterns: Iterable[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        if pattern.startswith("!"):
            continue
        matches = glob.glob(str(ROOT / pattern), recursive=True)
        if not matches:
            fail(f"manifest pattern matched nothing: {pattern}")
        paths.extend(Path(m) for m in matches)
    return sorted(set(paths))


def frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(errors="replace")
    if not text.startswith("---\n"):
        fail(f"{path.relative_to(ROOT)} is missing YAML frontmatter")
    end = text.find("\n---", 4)
    if end == -1:
        fail(f"{path.relative_to(ROOT)} has unterminated YAML frontmatter")
    raw = text[4:end]
    fields: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip() or line.startswith(" ") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"')
    return fields, text[end + 4 :]


def skill_files(skill_paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in skill_paths:
        if path.is_dir():
            files.extend(path.rglob("SKILL.md"))
        elif path.name == "SKILL.md":
            files.append(path)
        else:
            fail(f"pi.skills entry is neither a dir nor SKILL.md: {path.relative_to(ROOT)}")
    return sorted(set(files))


def check_skills(package: dict) -> None:
    files = skill_files(expand_patterns(package["pi"]["skills"]))
    if not files:
        fail("no skills discovered from pi.skills")
    seen: dict[str, Path] = {}
    for path in files:
        fields, _body = frontmatter(path)
        rel = path.relative_to(ROOT)
        name = fields.get("name", "")
        desc = fields.get("description", "")
        if not name:
            fail(f"{rel}: missing name")
        if not NAME_RE.fullmatch(name):
            fail(f"{rel}: invalid skill name {name!r}")
        if name != path.parent.name:
            fail(f"{rel}: name {name!r} must match parent dir {path.parent.name!r}")
        if not desc:
            fail(f"{rel}: missing description")
        if len(desc) > 1024:
            fail(f"{rel}: description too long ({len(desc)} > 1024)")
        if name in seen:
            fail(f"duplicate skill name {name!r}: {seen[name].relative_to(ROOT)} and {rel}")
        seen[name] = path
    print(f"OK skills: {len(files)}")


def check_prompts(package: dict) -> None:
    files = [p for p in expand_patterns(package["pi"]["prompts"]) if p.is_file()]
    if not files:
        fail("no prompt templates discovered from pi.prompts")
    seen: dict[str, Path] = {}
    for path in files:
        fields, body = frontmatter(path)
        rel = path.relative_to(ROOT)
        name = path.stem
        if not fields.get("description"):
            fail(f"{rel}: prompt template missing description")
        if name in seen:
            fail(f"duplicate prompt command /{name}: {seen[name].relative_to(ROOT)} and {rel}")
        seen[name] = path
        if not ARG_RE.search(body):
            warn(f"{rel}: prompt template does not reference command arguments")
    print(f"OK prompts: {len(files)}")


def main() -> None:
    package = load_package()
    check_skills(package)
    check_prompts(package)
    print("OK pi package manifest")


if __name__ == "__main__":
    main()
