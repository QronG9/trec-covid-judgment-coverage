"""Independent semantic checks for the completed-condition reanalysis."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("extension_analysis", SCRIPTS / "analyze_extensions.py")
ext = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ext)


class SavedOrderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "run.tsv"
        self.queries = {"1": {}, "2": {}}
        self.metadata = {"a": {}, "b": {}, "c": {}}
        self.valid = "1\tb\t1\t0.1\n1\ta\t2\t0.9\n2\tc\t1\t0\n2\ta\t2\t0\n"

    def tearDown(self):
        self.temp.cleanup()

    def read(self, rows):
        self.path.write_text("query_id\tdoc_id\trank\tscore\n" + rows)
        return ext.read_saved_run(self.path, self.queries, self.metadata, depth=2)

    def test_mmr_order_and_random_ties_are_preserved(self):
        self.assertEqual(self.read(self.valid), {"1": ["b", "a"], "2": ["c", "a"]})

    def test_empty_score_only_when_explicitly_unscored(self):
        rows = "1\tb\t1\t\n1\ta\t2\t\n2\tc\t1\t\n2\ta\t2\t\n"
        with self.assertRaises(ext.core.DataError):
            self.read(rows)
        self.assertEqual(ext.read_saved_run(self.path, self.queries, self.metadata, depth=2, allow_unscored=True), {"1": ["b", "a"], "2": ["c", "a"]})

    def test_corrupt_saved_runs_are_rejected(self):
        for rows in (
            self.valid.replace("1\ta\t2", "1\tb\t2"),
            self.valid.replace("1\ta\t2", "1\ta\t3"),
            self.valid.replace("2\tc", "unknown\tc"),
            self.valid.replace("2\tc", "2\tunknown"),
            self.valid.replace("0.1", "nan"),
            self.valid.replace("0.1", "inf"),
            self.valid.replace("0.1", "bad"),
            self.valid.split("2\tc", 1)[0],
        ):
            with self.subTest(rows=rows), self.assertRaises(ext.core.DataError):
                self.read(rows)


class RetrievalSemanticsTests(unittest.TestCase):
    def test_precision_and_recall_use_two_distinct_label_thresholds(self):
        runs = {"bm25": {"1": ["a", "b", "c", "d"], "2": ["a", "b", "c", "d"]}}
        labels = {"1": {"a": 2, "b": 1, "c": -1, "d": 0, "outside": 2}, "2": {"c": -1}}
        rows, summary = ext.observed_ir_tables(runs, labels, precision_k=2, recall_k=4)
        strict, relaxed = rows[0], rows[2]
        self.assertEqual((strict["observed_precision"], strict["observed_recall"]), (0.5, 0.5))
        self.assertEqual((relaxed["observed_precision"], relaxed["observed_recall"]), (1.0, 2 / 3))
        self.assertIsNone(rows[1]["observed_recall"])
        self.assertEqual(summary[0]["n_queries_with_relevant_qrels"], 1)
        self.assertEqual(summary[0]["mean_observed_recall"], 0.5)
        self.assertEqual(summary[0]["mean_observed_precision"], 0.25)

    def test_overlap_and_strata_partition_each_ranking(self):
        runs = {"bm25": {"1": ["a", "b", "c"], "2": ["d", "e", "f"]},
                "m": {"1": ["a", "x", "y"], "2": ["d", "e", "f"]}}
        labels = {"1": {"a": 0, "b": 2, "x": -1, "y": 1}, "2": {"d": 2}}
        overlap, _ = ext.overlap_tables(runs, cutoffs=(3,))
        self.assertEqual(overlap[0]["n_shared"], 1)
        self.assertEqual(overlap[0]["jaccard"], 1 / 5)
        rows, summary = ext.strata_tables(runs, labels, cutoffs=(3,))
        lookup = {(row["query_id"], row["stratum"]): row for row in rows}
        for q in ("1", "2"):
            self.assertEqual(lookup[q, "shared"]["n_pairs"] + lookup[q, "method_only"]["n_pairs"], 3)
            self.assertEqual(lookup[q, "shared"]["n_pairs"] + lookup[q, "bm25_only"]["n_pairs"], 3)
        shared = summary[0]
        self.assertEqual(shared["pooled_judged_fraction"], 2 / 4)
        self.assertEqual(shared["macro_nonempty_judged_fraction"], (1 + 1 / 3) / 2)
        only = summary[1]
        self.assertEqual(only["n_nonempty_queries"], 1)
        self.assertEqual(only["pooled_judged_fraction"], 0.5)
        self.assertEqual(only["n_explicit_minus1"], 1)
        self.assertIsNone(lookup["2", "method_only"]["judged_fraction"])

    def test_bound_difference_direction_and_shared_cancellation(self):
        runs = {"bm25": {"1": ["shared", "b"]}, "m": {"1": ["a", "shared"]}}
        rows, summary = ext.bound_tables(runs, {"1": {"a": 2, "b": 0}}, cutoffs=(2,))
        self.assertEqual(rows[0]["observed_delta"], 0.5)
        self.assertEqual(rows[0]["lower_bound"], 0.5)
        self.assertEqual(rows[0]["upper_bound"], 0.5)
        self.assertEqual(summary[0]["n_queries_a_guaranteed_higher"], 1)

    def test_candidate_membership_is_against_deeper_bm25_set(self):
        runs = {"bm25": {"1": ["a", "b", "c", "d"]}, "m": {"1": ["c", "x", "a", "y"]}}
        rows, summary = ext.candidate_membership_tables(runs, {"1": {"c": 0, "x": -1}}, cutoffs=(2,), baseline_depth=4)
        self.assertEqual((rows[0]["n_pairs"], rows[1]["n_pairs"]), (1, 1))
        self.assertEqual(rows[0]["judged_fraction"], 1)
        self.assertEqual(rows[1]["judged_fraction"], 0)
        self.assertEqual(summary[0]["mean_retrieved_fraction"], 0.5)

    def test_reranking_invariance_checks_set_and_counts(self):
        runs = {"bm25": {"1": ["a", "b", "c"]}, "bm25_ce": {"1": ["c", "a", "b"]},
                "direct": {"1": ["a", "x", "y"]}, "direct_mmr_rerank": {"1": ["y", "a", "x"]}}
        rows = ext.set_invariance_checks(runs, {"1": {"a": 2, "b": 0, "c": -1, "x": 1}}, depth=3)
        for row in rows:
            self.assertEqual(row["identical_sets"], 1)
            self.assertEqual(row["n_positions_changed"], 3)
            self.assertEqual(row["judged_count_delta"], 0)
            self.assertEqual(row["relevant_count_delta_strict"], 0)
            self.assertEqual(row["relevant_count_delta_relaxed"], 0)
        runs["bm25_ce"]["1"][0] = "x"
        with self.assertRaises(ext.core.DataError):
            ext.set_invariance_checks(runs, {"1": {}}, depth=3)

    def test_pilot_comparison_distinguishes_sequence_and_set_agreement(self):
        pilot = {"m": {"1": ["a", "b", "c"], "2": ["d", "e", "f"], "3": ["x", "y", "z"]}}
        full = {"m": {"1": ["a", "b", "c"], "2": ["f", "e", "d"], "3": ["x", "j", "k"], "4": ["q", "r", "s"]}}
        rows, summary = ext.pilot_full50_overlap_tables(pilot, full, cutoffs=(3,))
        self.assertEqual([row["same_sequence"] for row in rows], [1, 0, 0])
        self.assertEqual([row["n_shared"] for row in rows], [3, 3, 1])
        self.assertEqual([row["n_same_positions"] for row in rows], [3, 1, 1])
        self.assertEqual(summary[0]["n_same_sequence"], 1)
        self.assertEqual(summary[0]["n_identical_sets"], 2)
        self.assertEqual(summary[0]["mean_overlap_fraction"], (1 + 1 + 1 / 3) / 3)
        self.assertEqual(summary[0]["n_queries"], 3)


if __name__ == "__main__":
    unittest.main()
