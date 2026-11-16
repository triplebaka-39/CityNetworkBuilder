from __future__ import annotations

import heapq
from dataclasses import dataclass
from itertools import count
from typing import Iterable, Literal

from graph import Graph, Road


CYCLE_REJECTION_REASON = (
    "Both districts are already in the tree; selecting this road would create a cycle."
)


@dataclass(frozen=True)
class RejectedRoad:
    road: Road
    reason: str


@dataclass(frozen=True)
class PrimStep:
    """One decision; eligibility is pre-decision and cost is post-decision.

    Rejections processed before a selection are grouped with that selection.
    """

    step_number: int
    action: Literal["start", "select", "reject"]
    visited_before: tuple[str, ...]
    visited_after: tuple[str, ...]
    eligible_roads: tuple[Road, ...]
    selected_road: Road | None
    rejected_roads: tuple[RejectedRoad, ...]
    total_cost: float


@dataclass(frozen=True)
class PrimResult:
    """MST result; total_cost is None unless a complete spanning tree exists."""

    start_id: str | None
    selected_roads: tuple[Road, ...]
    total_cost: float | None
    steps: tuple[PrimStep, ...]
    is_spanning_tree: bool
    unreached_districts: tuple[str, ...]


def get_eligible_roads(
    graph: Graph,
    visited_ids: Iterable[str],
) -> tuple[Road, ...]:
    """Return roads crossing from the visited set to its unvisited complement."""
    visited = set(visited_ids)
    return tuple(
        road
        for road in graph.get_roads()
        if (road.start_id in visited) != (road.end_id in visited)
    )


def minimum_eligible_cost(roads: Iterable[Road]) -> float | None:
    """Return the cheapest eligible road cost, or ``None`` for no candidates."""
    costs = (road.cost for road in roads)
    return min(costs, default=None)


def prim_mst(graph: Graph, start_id: str | None = None) -> PrimResult:
    """Build a minimum spanning tree and record each algorithm event.

    A missing start district defaults to the graph's first district. For a
    disconnected graph, reached-component roads and steps are returned, but
    ``total_cost`` is ``None`` because no complete MST exists.
    """
    districts = graph.get_districts()
    adjacency = graph.get_adjacency_list()

    if not districts:
        if start_id is not None:
            raise ValueError(f"Starting district ID {start_id!r} does not exist.")
        return PrimResult(
            start_id=None,
            selected_roads=(),
            total_cost=None,
            steps=(),
            is_spanning_tree=False,
            unreached_districts=(),
        )

    if start_id is None:
        start_id = districts[0].district_id
    if not isinstance(start_id, str) or start_id not in adjacency:
        raise ValueError(f"Starting district ID {start_id!r} does not exist.")

    visited = {start_id}
    visited_order = [start_id]
    selected_roads: list[Road] = []
    steps: list[PrimStep] = []
    frontier: dict[frozenset[str], Road] = {}
    priority_queue: list[tuple[float, int, str, str]] = []
    sequence = count()
    total_cost = 0.0

    def edge_key(first_id: str, second_id: str) -> frozenset[str]:
        return frozenset((first_id, second_id))

    def eligible_snapshot() -> tuple[Road, ...]:
        eligible_keys = {
            edge_key(road.start_id, road.end_id)
            for road in get_eligible_roads(graph, visited)
        }
        return tuple(
            road
            for key, road in frontier.items()
            if key in eligible_keys
        )

    def add_frontier_edges(district_id: str) -> None:
        for neighbor_id, cost in adjacency[district_id].items():
            key = edge_key(district_id, neighbor_id)
            if neighbor_id in visited:
                frontier.pop(key, None)
            elif key not in frontier:
                road = graph.get_road(district_id, neighbor_id)
                frontier[key] = road
                heapq.heappush(
                    priority_queue,
                    (cost, next(sequence), district_id, neighbor_id),
                )

    add_frontier_edges(start_id)
    steps.append(
        PrimStep(
            step_number=0,
            action="start",
            visited_before=(),
            visited_after=(start_id,),
            eligible_roads=eligible_snapshot(),
            selected_road=None,
            rejected_roads=(),
            total_cost=total_cost,
        )
    )

    pending_rejections: list[RejectedRoad] = []
    while priority_queue:
        cost, _, from_id, to_id = heapq.heappop(priority_queue)
        key = edge_key(from_id, to_id)
        road = graph.get_road(from_id, to_id)

        if to_id in visited:
            frontier.pop(key, None)
            pending_rejections.append(
                RejectedRoad(road, CYCLE_REJECTION_REASON)
            )
            continue

        visited_before = tuple(visited_order)
        eligible_roads = eligible_snapshot()
        frontier.pop(key)
        visited.add(to_id)
        visited_order.append(to_id)
        selected_roads.append(road)
        total_cost += cost
        add_frontier_edges(to_id)
        steps.append(
            PrimStep(
                step_number=len(steps),
                action="select",
                visited_before=visited_before,
                visited_after=tuple(visited_order),
                eligible_roads=eligible_roads,
                selected_road=road,
                rejected_roads=tuple(pending_rejections),
                total_cost=total_cost,
            )
        )
        pending_rejections.clear()

    if pending_rejections:
        visited_snapshot = tuple(visited_order)
        steps.append(
            PrimStep(
                step_number=len(steps),
                action="reject",
                visited_before=visited_snapshot,
                visited_after=visited_snapshot,
                eligible_roads=eligible_snapshot(),
                selected_road=None,
                rejected_roads=tuple(pending_rejections),
                total_cost=total_cost,
            )
        )

    unreached = tuple(
        district.district_id
        for district in districts
        if district.district_id not in visited
    )
    is_spanning_tree = not unreached and bool(districts)
    return PrimResult(
        start_id=start_id,
        selected_roads=tuple(selected_roads),
        total_cost=total_cost if is_spanning_tree else None,
        steps=tuple(steps),
        is_spanning_tree=is_spanning_tree,
        unreached_districts=unreached,
    )
