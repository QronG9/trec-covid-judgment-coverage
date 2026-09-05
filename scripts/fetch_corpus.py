#!/usr/bin/env python3
"""Fetch or verify the exact BEIR corpus and regenerate its text-free metadata."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile

from import_source import export_metadata, sha256

ROOT = Path(__file__).resolve().parents[1]
URL = "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/trec-covid.zip"
ZIP_MD5 = "ce62140cb23feb9becf6270d0d1fe6d1"
FILES = ["corpus.jsonl", "queries.jsonl", "qrels/test.tsv"]


def verify_files(root):
    manifest = json.loads((root / "provenance/import_inputs.json").read_text())
    expected = {r["source_artifact"]: r["sha256"] for r in manifest["inputs"]}
    for name in FILES:
        path = root / "data/trec-covid" / name
        if not path.is_file() or sha256(path) != expected["trec-covid/" + name]:
            raise ValueError("Raw-data checksum mismatch or file missing: " + name)
    with tempfile.TemporaryDirectory() as tmp:
        rebuilt = Path(tmp) / "corpus_metadata.csv.gz"
        export_metadata(root / "data/trec-covid/corpus.jsonl", rebuilt)
        if sha256(rebuilt) != sha256(root / "data/corpus_metadata.csv.gz"):
            raise ValueError("Corpus-derived metadata differs from the release")
    print("PASS: all three raw BEIR files and regenerated corpus metadata match.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Use an already-downloaded original BEIR zip")
    parser.add_argument("--verify-only", action="store_true", help="Verify local raw files without downloading")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.verify_only:
        verify_files(root)
        return
    manifest = json.loads((root / "provenance/import_inputs.json").read_text())
    expected = {r["source_artifact"]: r["sha256"] for r in manifest["inputs"]}
    with tempfile.TemporaryDirectory() as tmp:
        archive = args.archive
        if archive is None:
            archive = Path(tmp) / "trec-covid.zip"
            print("Downloading the original BEIR archive; corpus text is excluded from Git.")
            with urllib.request.urlopen(URL, timeout=60) as response, archive.open("wb") as out:
                shutil.copyfileobj(response, out)
        h = hashlib.md5()
        with archive.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        if h.hexdigest() != ZIP_MD5:
            raise ValueError("Archive MD5 differs from the original BEIR release")
        # Read only the three explicit members; never blindly extract a zip.
        with zipfile.ZipFile(archive) as z:
            for name in FILES:
                target = root / "data/trec-covid" / name
                staged = Path(tmp) / name
                staged.parent.mkdir(parents=True, exist_ok=True)
                with z.open("trec-covid/" + name) as src, staged.open("wb") as out:
                    shutil.copyfileobj(src, out)
                if sha256(staged) != expected["trec-covid/" + name]:
                    raise ValueError("Extracted raw-data SHA-256 mismatch: " + name)
                if target.exists():
                    if sha256(target) != sha256(staged):
                        raise ValueError("Refusing to overwrite differing existing file: " + name)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(staged, target)
    verify_files(root)


if __name__ == "__main__":
    main()
