"""Semantic and corruption tests. Run: python -m unittest discover -s tests -v."""

import importlib.util
import itertools
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/analyze.py"
SPEC = importlib.util.spec_from_file_location("release_analysis", SCRIPT)
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


class SharpBoundsTests(unittest.TestCase):
    def test_exhaustive_binary_completions(self):
        # All combinations of missing/-1/0/1/2 labels on a four-document universe.
        # All two-document rankings, including full/partial/no overlap, are used.
        # Enumerating all legal completions independently checks endpoint sharpness.
        universe = ("a", "b", "c", "d")
        rankings = list(itertools.combinations(universe, 2))
        for states in itertools.product((None, -1, 0, 1, 2), repeat=len(universe)):
            labels = {doc: state for doc, state in zip(universe, states) if state is not None}
            unknown = [doc for doc in universe if labels.get(doc) in (None, -1)]
            for threshold in (1, 2):
                completions = []
                for values in itertools.product((0, 1), repeat=len(unknown)):
                    completed = {doc: int(labels.get(doc) in ((1, 2) if threshold == 1 else (2,))) for doc in universe}
                    completed.update(zip(unknown, values))
                    completions.append(completed)
                for a, b in itertools.product(rankings, repeat=2):
                    actual = analysis.paired_precision_bounds(a, b, labels, threshold)
                    deltas = [(sum(done[doc] for doc in a) - sum(done[doc] for doc in b)) / 2 for done in completions]
                    self.assertEqual(actual["lower_bound"], min(deltas))
                    self.assertEqual(actual["upper_bound"], max(deltas))

    def test_shared_unjudged_cancels(self):
        result = analysis.paired_precision_bounds(("shared", "positive"), ("shared", "zero"), {"positive": 2, "zero": 0})
        self.assertEqual(result["lower_bound"], 0.5)
        self.assertEqual(result["upper_bound"], 0.5)
        self.assertEqual(result["unjudged_shared"], 1)

    def test_minus_one_is_unjudged_zero_is_judged(self):
        runs = {"example": {"1": ["minus1", "zero", "one", "two", "absent"]}}
        labels = {"1": {"minus1": -1, "zero": 0, "one": 1, "two": 2}}
        rows, summary = analysis.coverage_tables(runs, labels, cutoffs=(5,))
        self.assertEqual(rows[0]["n_judged"], 3)
        self.assertEqual(rows[0]["n_unjudged"], 2)
        self.assertEqual(rows[0]["n_explicit_minus1"], 1)
        self.assertEqual(summary[0]["mean_hole_fraction"], 0.4)
        result = analysis.paired_precision_bounds(["minus1"], ["zero"], labels["1"])
        self.assertEqual((result["lower_bound"], result["upper_bound"]), (0.0, 1.0))
        self.assertFalse(analysis.relevant(-1, 1))
        self.assertFalse(analysis.relevant(0, 1))
        self.assertTrue(analysis.relevant(1, 1))
        self.assertFalse(analysis.relevant(1, 2))

    def test_invalid_bounds_inputs_fail(self):
        for a, b, labels in [([], [], {}), (["a"], ["a", "b"], {}), (["a", "a"], ["b", "c"], {}), (["a"], ["b"], {"a": 3})]:
            with self.assertRaises(analysis.DataError):
                analysis.paired_precision_bounds(a, b, labels)


class InputValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.queries = {"1": {}, "2": {}}
        self.metadata = {"a": {"has_abstract": True, "corpus_index": 0}, "b": {"has_abstract": True, "corpus_index": 1}, "c": {"has_abstract": False, "corpus_index": 2}}

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, text):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_qrels_preserve_minus_one(self):
        path = self.write("test.tsv", "query-id\tcorpus-id\tscore\n1\ta\t-1\n1\tb\t0\n2\tc\t2\n")
        result = analysis.read_qrels(path, self.queries, self.metadata)
        self.assertEqual(result, {"1": {"a": -1, "b": 0}, "2": {"c": 2}})

    def test_corrupt_qrels_fail(self):
        for lines in ("1\ta\t2\n1\ta\t2\n", "1\ta\t3\n", "unknown\ta\t0\n", "1\tunknown\t0\n", "1\ta\t2.0\n"):
            with self.subTest(lines=lines):
                path = self.write("test.tsv", "query-id\tcorpus-id\tscore\n" + lines)
                with self.assertRaises(analysis.DataError):
                    analysis.read_qrels(path, self.queries, self.metadata)

    def test_valid_run(self):
        path = self.write("run.tsv", "query_id\tdoc_id\trank\tscore\n2\tb\t1\t0.9\n2\ta\t2\t0.8\n1\ta\t1\t1.0\n1\tb\t2\t0.8\n")
        self.assertEqual(analysis.read_run(path, self.queries, self.metadata, depth=2), {"2": ["b", "a"], "1": ["a", "b"]})

    def test_corrupt_runs_fail(self):
        valid = "1\ta\t1\t0.9\n1\tb\t2\t0.8\n2\tb\t1\t0.9\n2\ta\t2\t0.8\n"
        cases = {
            "duplicate": valid.replace("1\tb\t2", "1\ta\t2"),
            "rank gap": valid.replace("1\tb\t2", "1\tb\t3"),
            "unknown query": valid.replace("2\tb\t1", "3\tb\t1"),
            "unknown document": valid.replace("1\ta\t1", "1\tunknown\t1"),
            "missing query": "1\ta\t1\t0.9\n1\tb\t2\t0.8\n",
            "short run": valid.rsplit("2\ta", 1)[0],
            "nonfinite": valid.replace("0.9", "nan", 1),
            "increasing score": valid.replace("1\tb\t2\t0.8", "1\tb\t2\t1.0"),
            "wrong tie order": valid.replace("2\ta\t2\t0.8", "2\ta\t2\t0.9"),
        }
        for reason, lines in cases.items():
            with self.subTest(reason=reason):
                path = self.write("run.tsv", "query_id\tdoc_id\trank\tscore\n" + lines)
                with self.assertRaises(analysis.DataError):
                    analysis.read_run(path, self.queries, self.metadata, depth=2)

    def test_valid_exact_score_tie_uses_corpus_index(self):
        path = self.write("run.tsv", "query_id\tdoc_id\trank\tscore\n1\ta\t1\t0.9\n1\tb\t2\t0.9\n2\ta\t1\t0.0\n2\tc\t2\t0.0\n")
        self.assertEqual(analysis.read_run(path, self.queries, self.metadata, depth=2), {"1": ["a", "b"], "2": ["a", "c"]})

    def test_eligible_run_must_have_abstract(self):
        path = self.write("run.tsv", "query_id\tdoc_id\trank\tscore\n1\tc\t1\t0.9\n2\ta\t1\t0.8\n")
        with self.assertRaises(analysis.DataError):
            analysis.read_run(path, self.queries, self.metadata, depth=1, require_abstract=True)

    def test_queries_reject_duplicates_and_malformed_rows(self):
        rows = [json.dumps({"_id": "1", "text": "query"})] * 2
        for content in ("\n".join(rows), "not JSON", json.dumps({"_id": 1, "text": "query"}), json.dumps({"_id": "1"})):
            with self.subTest(content=content):
                path = self.write("queries.jsonl", content + "\n")
                with self.assertRaises(analysis.DataError):
                    analysis.read_queries(path)

    def test_metadata_rejects_inconsistent_flags_and_indices(self):
        header = "corpus_index,doc_id,has_title,has_abstract,title_chars,abstract_chars\n"
        for lines in ("0,a,1,0,1,2\n", "1,a,1,0,1,0\n", "0,a,1,0,1,0\n0,b,1,0,1,0\n", "0,a,1,0,1,0\n1,a,1,0,1,0\n"):
            with self.subTest(lines=lines):
                path = self.write("metadata.csv", header + lines)
                with self.assertRaises(analysis.DataError):
                    analysis.read_metadata(path)


if __name__ == "__main__":
    unittest.main()
