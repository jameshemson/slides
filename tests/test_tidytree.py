"""Tests for tidytree.py — the pure hierarchy layout."""
import os
import sys
import unittest

_SCRIPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "source", "skills",
                 "build-deck", "scripts")
)
sys.path.insert(0, _SCRIPTS_DIR)

import tidytree  # noqa: E402


def _tree(label, *children):
    return {"label": label, "children": list(children)}


class TestLayout(unittest.TestCase):
    def test_single_node(self):
        rows, max_x, max_depth = tidytree.layout(_tree("root"))
        self.assertEqual(len(rows), 1)
        self.assertEqual((max_x, max_depth), (0.0, 0))

    def test_parent_centred_over_children(self):
        root = _tree("root", _tree("a"), _tree("b"), _tree("c"))
        rows, max_x, max_depth = tidytree.layout(root)
        pos = {n["label"]: (x, d) for n, x, d in rows}
        # leaves get 0,1,2; root centred at 1.0
        self.assertEqual(pos["a"][0], 0.0)
        self.assertEqual(pos["b"][0], 1.0)
        self.assertEqual(pos["c"][0], 2.0)
        self.assertEqual(pos["root"][0], 1.0)
        self.assertEqual(max_depth, 1)

    def test_no_two_nodes_share_x_at_a_depth(self):
        # A lopsided tree: root -> (a -> (a1,a2), b)
        root = _tree("root", _tree("a", _tree("a1"), _tree("a2")), _tree("b"))
        rows, _, _ = tidytree.layout(root)
        by_depth = {}
        for n, x, d in rows:
            by_depth.setdefault(d, []).append(x)
        for d, xs in by_depth.items():
            self.assertEqual(len(xs), len(set(xs)),
                             f"duplicate x at depth {d}: {xs}")

    def test_parent_between_children_span(self):
        root = _tree("root", _tree("a", _tree("a1"), _tree("a2")), _tree("b"))
        rows, _, _ = tidytree.layout(root)
        pos = {n["label"]: x for n, x, _ in rows}
        self.assertTrue(pos["a1"] < pos["a"] < pos["a2"])
        self.assertTrue(pos["a"] < pos["root"] < pos["b"])

    def test_deterministic(self):
        root = _tree("root", _tree("a", _tree("a1")), _tree("b", _tree("b1")))
        r1 = tidytree.layout(root)
        r2 = tidytree.layout(root)
        self.assertEqual([(n["label"], x, d) for n, x, d in r1[0]],
                         [(n["label"], x, d) for n, x, d in r2[0]])

    def test_count_nodes(self):
        root = _tree("root", _tree("a", _tree("a1"), _tree("a2")), _tree("b"))
        self.assertEqual(tidytree.count_nodes(root), 5)


if __name__ == "__main__":
    unittest.main()
