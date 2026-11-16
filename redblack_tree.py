"""Red-Black Tree — CLRS insert and delete, honestly implemented.

This is the textbook algorithm, not an approximation: rotations,
recoloring, and every fixup case from *Introduction to Algorithms*
(CLRS, 3rd ed., ch. 13 & 14), including the notoriously fiddly
RB-DELETE-FIXUP with its four cases and its sibling-walking loop.

What makes it inspectable:

* **Instrumented fixup cases.** Every branch of insert-fixup (cases 1–3)
  and delete-fixup (cases 1–4) increments a named counter, and each
  rotation increments ``rotations_left``/``rotations_right``.  The test
  suite asserts that a seeded workload drives *every* counter above
  zero, so no branch is dead code.
* **``verify()`` checks all five RB properties** plus BST ordering,
  parent-pointer consistency, and the declared node count:
  1. every node is red or black; 2. the root is black; 3. every leaf
  (``None``/NIL) is treated as black; 4. no red node has a red child;
  5. every root-to-NIL path contains the same number of black nodes —
  the *black-height* computed recursively and compared across siblings.
* **Range query** with pruning: ``range_query(lo, hi)`` walks only the
  subtrees that can contain keys inside the bounds.

Duplicates policy (documented and tested): keys are unique — inserting
an existing key replaces its value and returns ``False``; a new key
returns ``True``.

The tree stores ``size`` explicitly so ``len(tree)`` is O(1).
"""

from __future__ import annotations

from typing import Any, Iterator

__all__ = ["RBTree", "RBNode", "RBTreeError", "RED", "BLACK"]

RED = "red"
BLACK = "black"


class RBTreeError(Exception):
    """Raised by verify() when a red-black invariant is violated."""


class RBNode:
    """One tree node: key, value, color, parent/left/right links."""

    __slots__ = ("key", "value", "color", "parent", "left", "right")

    def __init__(self, key: Any, value: Any, color: str = RED) -> None:
        self.key = key
        self.value = value
        self.color = color
        self.parent: RBNode | None = None
        self.left: RBNode | None = None
        self.right: RBNode | None = None

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "RBNode(%r, %s)" % (self.key, self.color)


class RBTree:
    """A red-black tree mapping unique keys to values.

    Args:
        None — the tree is empty until you insert into it.

    Keys must be totally ordered with ``<``.
    """

    def __init__(self) -> None:
        self._root: RBNode | None = None
        self._size = 0
        self._counters: dict[str, int] = {
            "rotations_left": 0,
            "rotations_right": 0,
            "insert_case1": 0,
            "insert_case2": 0,
            "insert_case3": 0,
            "delete_case1": 0,
            "delete_case2": 0,
            "delete_case3": 0,
            "delete_case4": 0,
            "recolors": 0,
            "inserts": 0,
            "updates": 0,
            "deletes": 0,
        }

    # ------------------------------------------------------------------ #
    # introspection
    # ------------------------------------------------------------------ #

    @property
    def root(self) -> RBNode | None:
        """The root node (read-only view for inspection/tests)."""
        return self._root

    def __len__(self) -> int:
        return self._size

    def stats(self) -> dict:
        """Return counters: rotation counts, fixup case hits, op counts."""
        out = dict(self._counters)
        out["size"] = self._size
        return out

    def _count(self, name: str) -> None:
        self._counters[name] += 1

    # ------------------------------------------------------------------ #
    # rotations (each one counted — the tests assert both directions fire)
    # ------------------------------------------------------------------ #

    def _rotate_left(self, x: RBNode) -> None:
        """Left-rotate around ``x`` (CLRS ROTATE, x.right must exist)."""
        y = x.right
        x.right = y.left
        if y.left is not None:
            y.left.parent = x
        y.parent = x.parent
        if x.parent is None:
            self._root = y
        elif x is x.parent.left:
            x.parent.left = y
        else:
            x.parent.right = y
        y.left = x
        x.parent = y
        self._count("rotations_left")

    def _rotate_right(self, x: RBNode) -> None:
        """Right-rotate around ``x`` (CLRS ROTATE, x.left must exist)."""
        y = x.left
        x.left = y.right
        if y.right is not None:
            y.right.parent = x
        y.parent = x.parent
        if x.parent is None:
            self._root = y
        elif x is x.parent.right:
            x.parent.right = y
        else:
            x.parent.left = y
        y.right = x
        x.parent = y
        self._count("rotations_right")

    # ------------------------------------------------------------------ #
    # insert
    # ------------------------------------------------------------------ #

    def insert(self, key: Any, value: Any = None) -> bool:
        """Insert ``key -> value``; ``False`` if the key already existed
        (in which case the value is replaced in place)."""
        parent: RBNode | None = None
        node = self._root
        go_left = False
        while node is not None:
            parent = node
            if key < node.key:
                go_left = True
                node = node.left
            elif node.key < key:
                go_left = False
                node = node.right
            else:
                node.value = value
                self._count("updates")
                return False
        fresh = RBNode(key, value, RED)
        fresh.parent = parent
        if parent is None:
            self._root = fresh
        elif go_left:
            parent.left = fresh
        else:
            parent.right = fresh
        self._size += 1
        self._count("inserts")
        self._insert_fixup(fresh)
        return True

    def _insert_fixup(self, z: RBNode) -> None:
        """CLRS RB-INSERT-FIXUP: recolor (case 1) or rotate (2, 3)."""
        while z.parent is not None and z.parent.color == RED:
            g = z.parent.parent          # exists: root is always black
            if z.parent is g.left:
                uncle = g.right
                if uncle is not None and uncle.color == RED:
                    # Case 1: red parent + red uncle -> push black down,
                    # recolor grandparent red, climb.
                    self._count("insert_case1")
                    self._recolor(z.parent, BLACK)
                    self._recolor(uncle, BLACK)
                    self._recolor(g, RED)
                    z = g
                else:
                    if z is z.parent.right:
                        # Case 2: inner child -> rotate to make it outer.
                        self._count("insert_case2")
                        z = z.parent
                        self._rotate_left(z)
                    # Case 3: outer child -> one rotation + two recolors.
                    self._count("insert_case3")
                    self._recolor(z.parent, BLACK)
                    self._recolor(z.parent.parent, RED)
                    self._rotate_right(z.parent.parent)
            else:
                uncle = g.left
                if uncle is not None and uncle.color == RED:
                    self._count("insert_case1")
                    self._recolor(z.parent, BLACK)
                    self._recolor(uncle, BLACK)
                    self._recolor(g, RED)
                    z = g
                else:
                    if z is z.parent.left:
                        self._count("insert_case2")
                        z = z.parent
                        self._rotate_right(z)
                    self._count("insert_case3")
                    self._recolor(z.parent, BLACK)
                    self._recolor(z.parent.parent, RED)
                    self._rotate_left(z.parent.parent)
        if self._root is not None:
            self._recolor(self._root, BLACK)

    def _recolor(self, node: RBNode, color: str) -> None:
        if node.color != color:
            node.color = color
            self._count("recolors")

    # ------------------------------------------------------------------ #
    # delete
    # ------------------------------------------------------------------ #

    def delete(self, key: Any) -> bool:
        """Remove ``key``; return ``False`` if it was not present.

        Implements CLRS RB-DELETE with transplant + fixup when the
        removed node was black.
        """
        z = self._find(key)
        if z is None:
            return False
        y = z
        y_color = y.color
        if z.left is None:
            x = z.right
            x_parent = z.parent
            self._transplant(z, z.right)
        elif z.right is None:
            x = z.left
            x_parent = z.parent
            self._transplant(z, z.left)
        else:
            y = self._minimum(z.right)
            y_color = y.color
            x = y.right
            if y.parent is z:
                x_parent = y
            else:
                x_parent = y.parent
                self._transplant(y, y.right)
                y.right = z.right
                y.right.parent = y
            self._transplant(z, y)
            y.left = z.left
            y.left.parent = y
            y.color = z.color
        self._size -= 1
        self._count("deletes")
        if y_color == BLACK:
            # x may be None (a NIL); its parent must be tracked
            # separately because None carries no .parent link.
            self._delete_fixup(x, x_parent)
        return True

    def _transplant(self, u: RBNode, v: RBNode | None) -> None:
        """Replace subtree rooted at ``u`` with subtree ``v`` (CLRS)."""
        if u.parent is None:
            self._root = v
        elif u is u.parent.left:
            u.parent.left = v
        else:
            u.parent.right = v
        if v is not None:
            v.parent = u.parent

    def _minimum(self, node: RBNode) -> RBNode:
        while node.left is not None:
            node = node.left
        return node

    def _delete_fixup(self, x: RBNode | None, parent: RBNode | None) -> None:
        """CLRS RB-DELETE-FIXUP for a node ``x`` missing one black.

        ``parent`` is ``x.parent`` even when ``x`` is None (NIL), which
        the loop needs to find the sibling.  Cases 1–4 are counted.
        """
        while x is not self._root and (x is None or x.color == BLACK):
            if parent is None:          # only reachable if x is root
                break
            if parent.left is x:
                sibling = parent.right
                if sibling is None:     # impossible in a valid tree
                    break
                if sibling.color == RED:
                    # Case 1: red sibling -> rotate it away, sibling
                    # becomes black after the rotation.
                    self._count("delete_case1")
                    self._recolor(sibling, BLACK)
                    self._recolor(parent, RED)
                    self._rotate_left(parent)
                    sibling = parent.right
                near, far = sibling.left, sibling.right
                near_black = near is None or near.color == BLACK
                far_black = far is None or far.color == BLACK
                if near_black and far_black:
                    # Case 2: sibling black with black children ->
                    # give the sibling an extra black (paint red) and
                    # move the problem up to the parent.
                    self._count("delete_case2")
                    self._recolor(sibling, RED)
                    x = parent
                    parent = x.parent
                else:
                    if far_black:
                        # Case 3: near red, far black -> rotate the
                        # near child up so the far child becomes red
                        # (this becomes case 4).
                        self._count("delete_case3")
                        near.color = BLACK
                        self._recolor(sibling, RED)
                        self._rotate_right(sibling)
                        sibling = parent.right
                    # Case 4: far child red -> absorb the extra black
                    # into the sibling, then rotate the parent left.
                    self._count("delete_case4")
                    self._recolor(sibling, parent.color)
                    self._recolor(parent, BLACK)
                    sibling.right.color = BLACK
                    self._rotate_left(parent)
                    x = self._root
            else:
                sibling = parent.left
                if sibling is None:     # impossible in a valid tree
                    break
                if sibling.color == RED:
                    self._count("delete_case1")
                    self._recolor(sibling, BLACK)
                    self._recolor(parent, RED)
                    self._rotate_right(parent)
                    sibling = parent.left
                near, far = sibling.right, sibling.left
                near_black = near is None or near.color == BLACK
                far_black = far is None or far.color == BLACK
                if near_black and far_black:
                    self._count("delete_case2")
                    self._recolor(sibling, RED)
                    x = parent
                    parent = x.parent
                else:
                    if far_black:
                        self._count("delete_case3")
                        near.color = BLACK
                        self._recolor(sibling, RED)
                        self._rotate_left(sibling)
                        sibling = parent.left
                    self._count("delete_case4")
                    self._recolor(sibling, parent.color)
                    self._recolor(parent, BLACK)
                    sibling.left.color = BLACK
                    self._rotate_right(parent)
                    x = self._root
        if x is not None:
            self._recolor(x, BLACK)

    # ------------------------------------------------------------------ #
    # reads
    # ------------------------------------------------------------------ #

    def _find(self, key: Any) -> RBNode | None:
        node = self._root
        while node is not None:
            if key < node.key:
                node = node.left
            elif node.key < key:
                node = node.right
            else:
                return node
        return None

    def search(self, key: Any) -> bool:
        """``True`` iff ``key`` is in the tree."""
        return self._find(key) is not None

    def get(self, key: Any, default: Any = None) -> Any:
        """Value for ``key`` or ``default`` when absent."""
        node = self._find(key)
        return default if node is None else node.value

    def __contains__(self, key: Any) -> bool:
        return self.search(key)

    def __iter__(self) -> Iterator[Any]:
        """In-order (sorted) iteration over keys."""
        for node in self._inorder(self._root):
            yield node.key

    def _inorder(self, node: RBNode | None) -> Iterator[RBNode]:
        if node is None:
            return
        yield from self._inorder(node.left)
        yield node
        yield from self._inorder(node.right)

    def items(self) -> Iterator[tuple[Any, Any]]:
        """In-order ``(key, value)`` pairs."""
        for node in self._inorder(self._root):
            yield node.key, node.value

    def range_query(self, lo: Any = None, hi: Any = None) -> list:
        """Keys ``k`` with ``lo <= k <= hi`` in ascending order.

        Either bound may be ``None`` for an open side.  The walk prunes
        subtrees that cannot contain in-range keys, so the cost is
        O(log n + result size) for balanced-shaped queries.
        """
        out: list[Any] = []

        def walk(node: RBNode | None) -> None:
            if node is None:
                return
            # Left subtree can only contain keys < node.key, so it is
            # worth visiting only if something there could be >= lo.
            if lo is None or lo < node.key:
                walk(node.left)
            if (lo is None or not node.key < lo) and \
                    (hi is None or not hi < node.key):
                out.append(node.key)
            # Right subtree can only contain keys > node.key.
            if hi is None or node.key < hi:
                walk(node.right)

        walk(self._root)
        return out

    # ------------------------------------------------------------------ #
    # verification
    # ------------------------------------------------------------------ #

    def verify(self) -> bool:
        """Check all five RB properties + BST order + bookkeeping.

        Raises :class:`RBTreeError` naming the first violation;
        returns ``True`` so callers can assert on it.

        Properties (CLRS 13.1): (1) every node red or black; (2) root
        black; (3) NIL leaves black (``None`` is black by construction);
        (4) no red-red edges; (5) uniform black-height, computed
        bottom-up per subtree.  Additionally: strict in-order key
        ordering, parent-pointer consistency, and ``size`` accuracy.
        """
        root = self._root
        if root is not None and root.color != BLACK:
            raise RBTreeError("root is red")
        if root is not None and root.parent is not None:
            raise RBTreeError("root has a parent")

        count = 0

        def check(node: RBNode | None) -> int:
            """Return subtree black-height, validating as we go."""
            nonlocal count
            if node is None:
                return 0                       # NIL is black, bh 0
            if node.color not in (RED, BLACK):
                raise RBTreeError("node %r has invalid color %r"
                                  % (node.key, node.color))
            if node.color == RED:
                if (node.left is not None and node.left.color == RED) or \
                        (node.right is not None and node.right.color == RED):
                    raise RBTreeError("red node %r has a red child"
                                      % (node.key))
            if node.left is not None and node.left.parent is not node:
                raise RBTreeError("broken left parent link at %r"
                                  % node.key)
            if node.right is not None and node.right.parent is not node:
                raise RBTreeError("broken right parent link at %r"
                                  % node.key)
            left_bh = check(node.left)
            right_bh = check(node.right)
            if left_bh != right_bh:
                raise RBTreeError(
                    "black-height mismatch at %r: left=%d right=%d"
                    % (node.key, left_bh, right_bh))
            count += 1
            return left_bh + (1 if node.color == BLACK else 0)

        check(root)

        # BST ordering: in-order keys strictly increase.
        prev: Any = None
        have_prev = False
        for node in self._inorder(root):
            if have_prev and not prev < node.key:
                raise RBTreeError(
                    "BST order violated: %r not < %r" % (prev, node.key))
            prev = node.key
            have_prev = True

        if count != self._size:
            raise RBTreeError("size mismatch: counted %d, declared %d"
                              % (count, self._size))
        return True


# ---------------------------------------------------------------------- #
# Small self-demo so `python redblack_tree.py` shows the structure working.
# ---------------------------------------------------------------------- #
def _demo() -> None:  # pragma: no cover - illustrative only
    t = RBTree()
    for v in [10, 20, 30, 15, 25, 5, 1, 17]:
        t.insert(v, "v%d" % v)
    t.verify()
    print("sorted:", list(t))
    print("range [10, 25]:", t.range_query(10, 25))
    t.delete(20)
    t.verify()
    print("after delete 20:", list(t))
    print("stats:", t.stats())


if __name__ == "__main__":
    _demo()
