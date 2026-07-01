"""tidytree.py — a deterministic tidy layout for a small hierarchy.

PURE module (no pptx, no brand values). Given a nested node dict
`{"children": [...], ...}`, it assigns each node an abstract `(x, depth)`:

- every leaf gets the next integer x, left to right;
- every parent is centred over its children (`(first + last) / 2`).

For the small, capped trees the composed pipeline draws (≤ 8 nodes, depth ≤ 3)
this is guaranteed non-overlapping — sibling subtrees occupy disjoint x-ranges,
so two nodes at the same depth always land at distinct x. It is the tidy-tree
idea (Reingold–Tilford) without the thread/apportion machinery of Buchheim's
linear-time variant, which only earns its keep on large or lopsided trees the
element cap forbids here. primitives.plan_tree scales these coordinates onto the
content grid.
"""


def layout(root):
    """Return (rows, max_x, max_depth) where rows is [(node, x, depth), ...].

    x is a float in [0, max_x]; depth is 0 at the root. Post-order, so a parent's
    x is computed from its already-placed children.
    """
    rows = []
    counter = [0]

    def walk(node, depth):
        children = node.get("children", []) or []
        if not children:
            x = float(counter[0])
            counter[0] += 1
        else:
            child_xs = [walk(c, depth + 1) for c in children]
            x = (child_xs[0] + child_xs[-1]) / 2.0
        rows.append((node, x, depth))
        return x

    walk(root, 0)
    max_x = max((x for _, x, _ in rows), default=0.0)
    max_depth = max((d for _, _, d in rows), default=0)
    return rows, max_x, max_depth


def count_nodes(root):
    """Total node count of the tree."""
    return 1 + sum(count_nodes(c) for c in (root.get("children") or []))
