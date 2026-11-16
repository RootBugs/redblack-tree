"""Tests for the redblack-tree project.

Seeded randomness everywhere.  The signature test here is
``test_every_fixup_case_fires``: it drives a crafted sequence plus a
seeded random workload and asserts that *every* instrumented counter —
all three insert-fixup cases, all four delete-fixup cases, and both
rotation directions — was incremented, proving no CLRS branch is dead.
"""

import random
import unittest

from redblack_tree import BLACK, RED, RBTree, RBTreeError


def tree_height(node):
    """Height (edges) of the subtree rooted at ``node``."""
    if node is None:
        return -1
    return 1 + max(tree_height(node.left), tree_height(node.right))


class BasicTests(unittest.TestCase):

    def test_insert_search_get_roundtrip(self):
        t = RBTree()
        for i in range(200):
            self.assertTrue(t.insert(i, i * 2))
        self.assertEqual(len(t), 200)
        for i in range(200):
            self.assertTrue(t.search(i))
            self.assertIn(i, t)
            self.assertEqual(t.get(i), i * 2)
        self.assertFalse(t.search(9999))
        self.assertEqual(t.get(9999, "d"), "d")
        t.verify()

    def test_inorder_iteration_is_sorted(self):
        t = RBTree()
        rng = random.Random(4242)
        values = rng.sample(range(10000), 500)
        for v in values:
            t.insert(v)
        self.assertEqual(list(t), sorted(values))
        self.assertEqual([k for k, _ in t.items()], sorted(values))
        t.verify()

    def test_duplicates_update_value(self):
        t = RBTree()
        self.assertTrue(t.insert("a", 1))
        self.assertFalse(t.insert("a", 2))
        self.assertEqual(len(t), 1)
        self.assertEqual(t.get("a"), 2)
        self.assertEqual(list(t), ["a"])
        t.verify()

    def test_empty_tree_edges(self):
        t = RBTree()
        t.verify()
        self.assertIsNone(t.root)
        self.assertEqual(len(t), 0)
        self.assertFalse(t.delete("x"))
        self.assertEqual(t.range_query(0, 100), [])
        self.assertEqual(list(t), [])


class DeleteTests(unittest.TestCase):

    def test_delete_missing_returns_false(self):
        t = RBTree()
        t.insert(1)
        self.assertFalse(t.delete(2))
        self.assertTrue(t.delete(1))
        self.assertFalse(t.delete(1))
        self.assertEqual(len(t), 0)
        t.verify()

    def test_delete_of_root_repeatedly(self):
        """Delete whatever sits at the root 127 times, verifying each."""
        t = RBTree()
        for i in range(1, 128):
            t.insert(i, i)
        removed = []
        while len(t) > 0:
            root_key = t.root.key
            removed.append(root_key)
            self.assertTrue(t.delete(root_key))
            t.verify()
        self.assertEqual(sorted(removed), list(range(1, 128)))
        self.assertEqual(len(t), 0)

    def test_delete_head_middle_tail_random(self):
        t = RBTree()
        keys = list(range(100))
        for k in keys:
            t.insert(k, k)
        for k in (0, 50, 99, 25, 75):
            self.assertTrue(t.delete(k))
            t.verify()
        remaining = sorted(set(keys) - {0, 25, 50, 75, 99})
        self.assertEqual(list(t), remaining)
        for k in remaining:
            self.assertEqual(t.get(k), k)


class RandomizedTests(unittest.TestCase):

    def test_random_ops_match_reference_dict(self):
        """Seeded insert/delete workload vs dict oracle; verify per batch."""
        t = RBTree()
        ref = {}
        rng = random.Random(31337)
        for step in range(6000):
            key = rng.randrange(1500)
            if rng.random() < 0.6:
                expected = key not in ref
                self.assertEqual(t.insert(key, step), expected,
                                 "insert(%d) step %d" % (key, step))
                ref[key] = step
            else:
                expected = key in ref
                self.assertEqual(t.delete(key), expected,
                                 "delete(%d) step %d" % (key, step))
                if expected:
                    del ref[key]
            if step % 500 == 0:
                t.verify()
        t.verify()
        self.assertEqual(len(t), len(ref))
        self.assertEqual(list(t), sorted(ref))
        for k, v in ref.items():
            self.assertEqual(t.get(k), v)

    def test_10k_op_stress_with_height_bound(self):
        """10k seeded ops: verify() passes and RB height bound holds
        (height <= 2*log2(n+1), the structural payoff of red-black)."""
        t = RBTree()
        rng = random.Random(777)
        ops = 0
        for _ in range(5000):
            t.insert(rng.randrange(10000), 1)
            ops += 1
        t.verify()
        for _ in range(5000):
            t.delete(rng.randrange(10000))
            ops += 1
        self.assertEqual(ops, 10000)
        t.verify()
        n = len(t)
        if n > 0:
            bound = 2 * ((n + 1).bit_length() - 1) + 2
            self.assertLessEqual(tree_height(t.root), bound,
                                 "red-black height bound violated")

    def test_sequential_insert_delete_cycles(self):
        """Ascending inserts then ascending deletes through many cycles."""
        t = RBTree()
        for cycle in range(5):
            base = cycle * 400
            for i in range(base, base + 400):
                t.insert(i, i)
            t.verify()
            self.assertEqual(len(t), 400)
            for i in range(base, base + 400):
                self.assertTrue(t.delete(i))
            t.verify()
            self.assertEqual(len(t), 0)
        self.assertIsNone(t.root)


class FixupInstrumentationTests(unittest.TestCase):

    def test_every_fixup_case_fires(self):
        """Crafted shapes + a seeded random workload must increment
        every insert case, every delete case, and both rotations."""
        # --- crafted shapes for the insert cases --------------------- #
        t = RBTree()
        # Case 1 (uncle red): 10, 5, 15, 1 -> parent 5 red, uncle 15 red.
        for v in (10, 5, 15, 1):
            t.insert(v, v)
        # Case 2+3 (inner then outer child): insert 7 (right of 5) and
        # 3 (left of 1) create rotations on both sides.
        for v in (7, 3):
            t.insert(v, v)
        t.verify()
        # Mirrored shapes on the right side of the tree.
        for v in (50, 30, 70, 75, 65, 60):
            t.insert(v, v)
        t.verify()
        self.assertGreater(t.stats()["insert_case1"], 0)
        self.assertGreater(t.stats()["insert_case2"], 0)
        self.assertGreater(t.stats()["insert_case3"], 0)

        # --- crafted + random delete workload ------------------------ #
        rng = random.Random(987654321)
        # A seeded pool large enough that every delete case occurs.
        for i in range(3000):
            t.insert(rng.randrange(10000), i)
        t.verify()
        for _ in range(3000):
            t.delete(rng.randrange(10000))
        t.verify()
        stats = t.stats()
        for case in ("delete_case1", "delete_case2", "delete_case3",
                     "delete_case4"):
            self.assertGreater(stats[case], 0,
                               "delete fixup %s never fired" % case)
        self.assertGreater(stats["rotations_left"], 0)
        self.assertGreater(stats["rotations_right"], 0)

    def test_stats_counters_track_operations(self):
        t = RBTree()
        t.insert(1, "a")
        t.insert(1, "b")   # update
        t.insert(2, "c")
        t.delete(2)
        s = t.stats()
        self.assertEqual(s["inserts"], 2)
        self.assertEqual(s["updates"], 1)
        self.assertEqual(s["deletes"], 1)
        self.assertEqual(s["size"], 1)
        self.assertGreaterEqual(s["recolors"], 1)


class RangeQueryTests(unittest.TestCase):

    def test_range_query_matches_reference(self):
        t = RBTree()
        rng = random.Random(555)
        values = rng.sample(range(1000), 300)
        for v in values:
            t.insert(v, v)
        ordered = sorted(values)
        for lo, hi in [(0, 999), (100, 200), (-5, 0), (996, 1000),
                       (314, 314), (500, 400), (0, 999999)]:
            expected = [v for v in ordered if lo <= v <= hi]
            self.assertEqual(t.range_query(lo, hi), expected,
                             "range [%r, %r]" % (lo, hi))

    def test_range_query_open_bounds(self):
        t = RBTree()
        for v in (1, 2, 3, 4, 5):
            t.insert(v)
        self.assertEqual(t.range_query(None, 3), [1, 2, 3])
        self.assertEqual(t.range_query(3, None), [3, 4, 5])
        self.assertEqual(t.range_query(None, None), [1, 2, 3, 4, 5])
        # single exact hit and misses
        self.assertEqual(t.range_query(3, 3), [3])
        self.assertEqual(t.range_query(6, 9), [])


class VerifyTests(unittest.TestCase):

    def test_verify_passes_on_healthy_tree(self):
        t = RBTree()
        rng = random.Random(2024)
        for _ in range(500):
            t.insert(rng.randrange(2000))
        self.assertTrue(t.verify())

    def test_verify_catches_red_root(self):
        t = RBTree()
        t.insert(1)
        t.insert(2)
        t.root.color = RED
        with self.assertRaises(RBTreeError):
            t.verify()

    def test_verify_catches_red_red_edge(self):
        t = RBTree()
        for v in (10, 5, 15, 1):
            t.insert(v, v)
        # Crafted shape: root(10) black, left child 5 black, 5.left=1 red.
        # Coloring 5 red as well creates a red-red edge while the root
        # stays black, so property 4 is what must trip.
        self.assertEqual(t.root.color, BLACK)
        node5 = t.root.left
        node1 = node5.left
        node5.color = RED
        node1.color = RED
        with self.assertRaises(RBTreeError) as ctx:
            t.verify()
        self.assertIn("red child", str(ctx.exception))

    def test_verify_catches_bst_violation(self):
        t = RBTree()
        for v in (2, 1, 3):
            t.insert(v, v)
        root = t.root
        root.key = 99            # in-order walk is now 1, 99, 3 -> broken
        with self.assertRaises(RBTreeError):
            t.verify()

    def test_verify_catches_wrong_size(self):
        t = RBTree()
        for v in (1, 2, 3):
            t.insert(v, v)
        t._size = 7
        with self.assertRaises(RBTreeError):
            t.verify()


if __name__ == "__main__":
    unittest.main()
