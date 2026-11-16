# redblack-tree

The red-black tree from CLRS — **insert and full delete with every
fixup case** — implemented honestly, instrumented, and provably correct
by a property checker. Zero dependencies (stdlib only).

**Why it's special:** most red-black implementations quietly skip the
hard part (RB-DELETE-FIXUP's four-case sibling walk) or ship it
untested because its branches are so hard to reach. Here every branch
is a **named counter**: `insert_case1..3`, `delete_case1..4`,
`rotations_left`, `rotations_right`, `recolors`. The test suite asserts
that a crafted-shape sequence plus a seeded 3,000-delete workload drives
**every single counter above zero** — no dead fixup branches are
possible without the suite going red.

`verify()` is not a smoke test. It checks all **five CLRS red-black
properties** — (1) every node red or black, (2) root black, (3) NIL
leaves black by construction, (4) no red-red edges, (5) uniform
**black-height** computed bottom-up and compared across siblings — plus
strict BST ordering, parent-pointer consistency, and the declared
`size`. Corruption tests prove each check actually fires.

Also included: **in-order iteration**, an **open/closed `range_query`
with subtree pruning**, O(1) `len()`, and a documented duplicates
policy (unique keys; re-inserting replaces the value and returns
`False`).

## Architecture

```
redblack_tree.py
├── RBNode        key, value, color, parent/left/right (__slots__)
├── RBTree
│   ├── _rotate_left/_rotate_right   CLRS ROTATE, each counted
│   ├── insert + _insert_fixup       cases 1 (recolor), 2 (inner
│   │                                rotation), 3 (outer rotation + recolor)
│   ├── delete + _delete_fixup       transplant, then cases 1–4 with
│   │                                NIL-aware sibling walking
│   ├── range_query                  pruned in-order walk
│   └── verify                       5 properties + BST + links + size
└── _demo         runnable self-check (python redblack_tree.py)
```

Nil nodes (`None`) carry no parent pointer, so `_delete_fixup` takes the
parent explicitly — the classic source of off-by-one bugs in delete
fixup, handled head-on.

## Runnable example

```python
from redblack_tree import RBTree

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
```

Output:

```
sorted: [1, 5, 10, 15, 17, 20, 25, 30]
range [10, 25]: [10, 15, 17, 20, 25]
after delete 20: [1, 5, 10, 15, 17, 25, 30]
stats: {'rotations_left': 1, 'rotations_right': 0, 'insert_case1': 2, 'insert_case2': 0, 'insert_case3': 1, 'delete_case1': 0, 'delete_case2': 0, 'delete_case3': 0, 'delete_case4': 0, 'recolors': 10, 'inserts': 8, 'updates': 0, 'deletes': 1, 'size': 7}
```

## Tests

```
python -m unittest discover -s tests -v
```

19 tests: insert/search/get roundtrip; sorted in-order iteration over
500 shuffled values; **every fixup case and both rotation directions
asserted to fire**; a seeded 6,000-op workload matched against a dict
oracle with `verify()` every 500 ops; repeated **root deletion** with
`verify()` after every step; ascending insert/delete cycles; a 10k-op
stress run asserting the RB **height bound** `2·⌈log2(n+1)⌉`; range
queries (inclusive bounds, open bounds, empty, exact-hit); duplicates
policy; and four corruption tests proving `verify()` rejects a red
root, a red-red edge, a BST violation, and a wrong size.

## License

MIT — see [LICENSE](LICENSE).
