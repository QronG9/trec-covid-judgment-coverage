#!/usr/bin/env python3
"""Maintainer command: freeze tracked release files after reviewing all changes."""
import hashlib
from pathlib import Path
import subprocess


def main():
    root = Path(__file__).resolve().parents[1]
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
    lines = []
    for name in sorted(n for n in names if n and n != "MANIFEST.sha256"):
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Only regular release files may be frozen: " + name)
        h = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(h + "  " + name)
    if not lines:
        raise ValueError("Stage the intended release files before freezing the manifest")
    (root / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")
    print(f"Froze {len(lines)} tracked files. Run verify_release.py, then commit manifest and reviewed changes together.")


if __name__ == "__main__":
    main()
