from fractions import Fraction
from math import ceil
from typing import List, Optional, Sequence


class Edge:
    """Any object that defines an edge (such as Layout)."""

    size: Optional[int] = None
    ratio: int = 1
    minimum_size: int = 1

    def __init__(self, size=None, ratio=1, minimum_size=1):
        self.size = size
        self.ratio = ratio
        self.minimum_size = minimum_size


def ratio_resolve(total: int, edges: Sequence[Edge]) -> List[int]:
    """Divide total space to satisfy size, ratio, and minimum_size, constraints.

    The returned list of integers should add up to total in most cases, unless it is
    impossible to satisfy all the constraints. For instance, if there are two edges
    with a minimum size of 20 each and `total` is 30 then the returned list will be
    greater than total. In practice, this would mean that a Layout object would
    clip the rows that would overflow the screen height.

    Args:
        total (int): Total number of characters.
        edges (List[Edge]): Edges within total space.

    Returns:
        List[int]: Number of characters for each edge.
    """
    # Size of edge or None for yet to be determined
    sizes = [(edge.size or None) for edge in edges]

    _Fraction = Fraction

    # While any edges haven't been calculated
    while None in sizes:
        # Get flexible edges and index to map these back on to sizes list
        flexible_edges = [
            (index, edge)
            for index, (size, edge) in enumerate(zip(sizes, edges))
            if size is None
        ]
        # Remaining space in total
        remaining = total
        if remaining <= 0:
            # No room for flexible edges
            return [
                ((edge.minimum_size or 1) if size is None else size)
                for size, edge in zip(sizes, edges)
            ]
        # Calculate number of characters in a ratio portion
        portion = _Fraction(
            remaining, sum((edge.ratio or 1) for _, edge in flexible_edges)
        )

        # If any edges will be less than their minimum, replace size with the minimum
        for index, edge in flexible_edges:
            if portion * edge.ratio <= edge.minimum_size:
                sizes[index] = edge.minimum_size
                # New fixed size will invalidate calculations, so we need to repeat the process
                break
        else:
            # Distribute flexible space and compensate for rounding error
            # Since edge sizes can only be integers we need to add the remainder
            # to the following line
            remainder = _Fraction(0)
            for index, edge in flexible_edges:
                size, remainder = divmod(portion * edge.ratio + remainder, 1)
                sizes[index] = int(size)
            break
    # Sizes now contains integers only
    return sizes  # type: ignore[return-value]
