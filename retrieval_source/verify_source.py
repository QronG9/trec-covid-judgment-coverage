#!/usr/bin/env python3
"""Check my published source snapshot and optionally compare its original source files."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def executable_ast(text, normalize_metadata=False):
    tree = ast.parse(text)

    class WithoutDocstrings(ast.NodeTransformer):
        def generic_visit(self, node):
            node = super().generic_visit(node)
            if (
                isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                node.body = node.body[1:]
            return node

    tree = WithoutDocstrings().visit(tree)
    if normalize_metadata:
        matched = 0
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "save_run"):
                continue
            for argument in node.args:
                if not (isinstance(argument, ast.Call) and isinstance(argument.func, ast.Name)
                        and argument.func.id == "dict"):
                    continue
                for keyword in argument.keywords:
                    if keyword.arg == "reason":
                        if not (isinstance(keyword.value, ast.Constant)
                                and isinstance(keyword.value.value, str)):
                            raise ValueError("Expected one descriptive metadata string")
                        keyword.value = ast.Constant(value="DESCRIPTIVE_REASON_METADATA")
                        matched += 1
        if matched != 1:
            raise ValueError("Expected exactly one recorded metadata location")
    def canonical(value):
        if isinstance(value, ast.AST):
            fields = {key: canonical(val) for key, val in ast.iter_fields(value)
                      if not (key == "type_params" and not val)}
            return {"node": type(value).__name__, "fields": fields}
        if isinstance(value, list):
            return [canonical(item) for item in value]
        return value

    return json.dumps(canonical(tree), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def metadata_value(text):
    tree = ast.parse(text)
    values = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "save_run":
            for argument in node.args:
                if isinstance(argument, ast.Call) and isinstance(argument.func, ast.Name) and argument.func.id == "dict":
                    values.extend(k.value.value for k in argument.keywords
                                  if k.arg == "reason" and isinstance(k.value, ast.Constant))
    if len(values) != 1 or not isinstance(values[0], str):
        raise ValueError("Expected one descriptive metadata value")
    return values[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path,
                        help="Optional original stage1_pooling_bias project for direct source comparison")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "SOURCE_MANIFEST.json").read_text())
    n_python = 0
    for item in manifest["files"]:
        target = ROOT / item["published_path"]
        raw = target.read_bytes()
        if digest(raw) != item["published_sha256"]:
            raise ValueError("Published file checksum differs: " + item["published_path"])
        if target.suffix == ".py":
            text = raw.decode("utf-8")
            compile(text, item["published_path"], "exec")
            normalized = "metadata_standardization" in item
            if normalized:
                if metadata_value(text) != item["metadata_standardization"]["published_value"]:
                    raise ValueError("Descriptive metadata differs")
            current = digest(executable_ast(text).encode())
            algorithm = digest(executable_ast(text, normalized).encode())
            if current != item["published_executable_ast_sha256"]:
                raise ValueError("Published AST differs: " + item["published_path"])
            if algorithm != item["source_algorithm_ast_sha256"] or algorithm != item["published_algorithm_ast_sha256"]:
                raise ValueError("Algorithm AST differs: " + item["published_path"])
            n_python += 1
        if args.source_root:
            original = (args.source_root / item["source_path"]).read_bytes()
            if digest(original) != item["source_sha256"]:
                raise ValueError("Original source checksum differs: " + item["source_path"])
            if target.suffix == ".py":
                original_text = original.decode("utf-8")
                if digest(executable_ast(original_text).encode()) != item["source_executable_ast_sha256"]:
                    raise ValueError("Original AST differs")
                if normalized and digest(metadata_value(original_text).encode()) != item["metadata_standardization"]["source_value_sha256"]:
                    raise ValueError("Original descriptive metadata differs")
                if executable_ast(original_text, normalized) != executable_ast(text, normalized):
                    raise ValueError("Source and publication algorithms differ")
    print(f"PASS: {len(manifest['files'])} source-file hashes; {n_python} syntax and algorithm AST checks")
    if args.source_root:
        print(f"PASS: {len(manifest['files'])} original-source hashes; {n_python} direct source/publication comparisons")


if __name__ == "__main__":
    main()
