from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

MAX_SCANNED_FILE_BYTES: Final = 2 * 1024 * 1024
EXCLUDED_DIRECTORY_NAMES: Final = frozenset(
    {".git", ".next", "__pycache__", "build", "coverage", "dist", "node_modules"}
)
EXCLUDED_FILE_NAMES: Final = frozenset({".env", ".env.local"})
SCANNABLE_SUFFIXES: Final = frozenset(
    {
        ".cfg",
        ".env",
        ".example",
        ".ini",
        ".js",
        ".json",
        ".jsx",
        ".md",
        ".pem",
        ".py",
        ".sh",
        ".toml",
        ".ts",
        ".tsx",
        ".txt",
        ".yaml",
        ".yml",
    }
)
SCANNABLE_FILE_NAMES: Final = frozenset({"Dockerfile", "Makefile"})
SECRET_PATTERNS: Final = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("openai-api-key", re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}")),
    (
        "github-token",
        re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{20,255})"),
    ),
    ("aws-access-key", re.compile(r"AKIA[0-9A-Z]{16}")),
    (
        "aws-secret-access-key",
        re.compile(
            r"aws_secret_access_key\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{40}['\"]?",
            re.IGNORECASE,
        ),
    ),
    ("google-api-key", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("slack-token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}")),
)


@dataclass(frozen=True, slots=True)
class SecretFinding:
    path: Path
    rule_name: str


def is_scannable_path(path: Path) -> bool:
    if path.name in EXCLUDED_FILE_NAMES:
        return False
    if any(part in EXCLUDED_DIRECTORY_NAMES for part in path.parts):
        return False
    return path.name in SCANNABLE_FILE_NAMES or path.suffix.lower() in SCANNABLE_SUFFIXES


def scan_files(paths: Iterable[Path]) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    for path in sorted(paths):
        if not is_scannable_path(path) or not path.is_file():
            continue
        if path.stat().st_size > MAX_SCANNED_FILE_BYTES:
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for rule_name, pattern in SECRET_PATTERNS:
            if pattern.search(content):
                findings.append(SecretFinding(path=path, rule_name=rule_name))
    return findings


def tracked_files(repository_root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=False,
    )
    return [
        repository_root / raw_path.decode("utf-8")
        for raw_path in result.stdout.split(b"\0")
        if raw_path
    ]


def run_scan(paths: Sequence[Path]) -> int:
    findings = scan_files(paths)
    if not findings:
        print("Secret scan passed: no candidate credentials found in tracked source files.")
        return 0
    print("Secret scan failed: remove the detected credential candidates.")
    for finding in findings:
        print(f"{finding.path}: {finding.rule_name}")
    return 1


def main() -> int:
    repository_root = Path(__file__).resolve().parents[1]
    try:
        return run_scan(tracked_files(repository_root))
    except subprocess.CalledProcessError:
        print("Secret scan failed: unable to enumerate tracked repository files.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
