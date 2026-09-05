#!/usr/bin/env python3
"""Offline release checks: file hashes, clean recomputation, reference values, tests."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def fail(message):
    raise RuntimeError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def check_manifest(root):
    manifest = root / "MANIFEST.sha256"
    if not manifest.is_file():
        fail("MANIFEST.sha256 missing; use --skip-manifest only during release development")
    paths = set()
    for line in manifest.read_text().splitlines():
        expected, name = line.split("  ", 1)
        path = (root / name).resolve()
        if root not in path.parents or name in paths:
            fail("Invalid or repeated manifest path: " + name)
        paths.add(name)
        if not path.is_file() or digest(path) != expected:
            fail("Checksum mismatch: " + name)
    required = {"scripts/analyze.py", "docs/RESEARCH_NOTE.md", "data/trec-covid/qrels/test.tsv", "data/corpus_metadata.csv.gz", "scripts/analyze_extensions.py", "data/method_registry.json"}
    if not required.issubset(paths):
        fail("Manifest does not cover required release files")
    return len(paths)


def command(args, cwd=ROOT):
    run = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if run.returncode:
        fail("Command failed: " + " ".join(map(str, args)) + "\n" + run.stdout + run.stderr)
    return run.stdout + run.stderr


def check_references(root, results):
    refs = []
    for filename in ("reference_values.json", "extension_reference_values.json"):
        refs.extend(json.loads((root / "provenance" / filename).read_text())["references"])
    tables = {}
    for ref in refs:
        name = ref["result_file"]
        if name not in tables:
            with (results / name).open() as f:
                tables[name] = list(csv.DictReader(f))
    count = 0
    for ref in refs:
        matches = [row for row in tables[ref["result_file"]]
                   if all(row.get(key) == str(value) for key, value in ref["key"].items())]
        if len(matches) != 1:
            fail("Reference must match exactly one row: " + str(ref["key"]))
        for field, expected in ref["values"].items():
            actual = float(matches[0][field])
            if not math.isfinite(actual) or not math.isclose(actual, expected, rel_tol=0, abs_tol=1e-10):
                fail(f"Reference mismatch {ref['result_file']} {ref['key']} {field}: {actual} vs {expected}")
            count += 1
    return count


def check_links(root):
    count = 0
    for folder in [root, root / "docs", root / "data", root / "archive", root / "provenance", root / "retrieval_source"]:
        for path in folder.glob("*.md"):
            for raw in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                target = raw.strip().strip("<>").split("#", 1)[0]
                if not target or re.match(r"[a-zA-Z]+:", target):
                    continue
                target = unquote(target)
                if not (path.parent / target).exists():
                    fail(f"Broken relative link in {path.relative_to(root)}: {raw}")
                count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-manifest", action="store_true", help="Development only: explicitly skip release hash checking")
    args = parser.parse_args()
    if args.skip_manifest:
        print("SKIPPED: release manifest (development mode)")
    else:
        print(f"PASS: {check_manifest(ROOT)} release-file SHA-256 checks")
    with tempfile.TemporaryDirectory(prefix="trec-covid-release-") as tmp:
        output = Path(tmp) / "results"
        command([sys.executable, str(ROOT / "scripts/analyze.py"), "--data-dir", str(ROOT / "data"), "--output-dir", str(output)])
        command([sys.executable, str(ROOT / "scripts/analyze_extensions.py"), "--data-dir", str(ROOT / "data"), "--output-dir", str(output / "extensions")])
        expected_files = {p.relative_to(ROOT / "results").as_posix() for p in (ROOT / "results").rglob("*") if p.is_file() and p.suffix in (".csv", ".json")}
        actual_files = {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()}
        if expected_files != actual_files:
            fail("Recomputed result inventory differs from the release")
        for name in expected_files:
            if (output / name).read_bytes() != (ROOT / "results" / name).read_bytes():
                fail("Clean recomputation differs from committed result: " + name)
        print(f"PASS: {len(expected_files)} result files reproduced byte for byte in a clean temporary directory")
        print(f"PASS: {check_references(ROOT, output)} numerical comparisons against saved experiment reference values")
    for flags, label in [([], "normal"), (["-O"], "optimized")]:
        text = command([sys.executable, *flags, "-m", "unittest", "discover", "-s", "tests"])
        match = re.search(r"Ran (\d+) tests", text)
        print(f"PASS: {match.group(1) if match else 'all'} semantic/input tests ({label} Python)")
    source_check = command([sys.executable, str(ROOT / "retrieval_source/verify_source.py")])
    print(source_check.strip())
    print(f"PASS: {check_links(ROOT)} relative documentation links")
    fig = json.loads((ROOT / "figures/figure_sources.json").read_text())
    for name, expected in fig["source_table_sha256"].items():
        if digest(ROOT / "results" / name) != expected:
            fail("Figure source is stale: " + name)
    print("PASS: figure source tables match the recorded hashes")
    print("Release verification completed: fixed-input calculations, numerical continuity, and file integrity.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
