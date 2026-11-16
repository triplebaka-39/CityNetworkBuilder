import pytest

from graph import Graph
from prim import CYCLE_REJECTION_REASON, prim_mst


def make_graph(district_ids: tuple[str, ...], roads: tuple[tuple[str, str, float], ...]) -> Graph:
    graph = Graph()
    for district_id in district_ids:
        graph.add_district(district_id, district_id.title())
    for start_id, end_id, cost in roads:
        graph.add_road(start_id, end_id, cost)
    return graph


def test_prim_finds_known_minimum_spanning_tree_in_order() -> None:
    graph = make_graph(
        ("A", "B", "C", "D"),
        (
            ("A", "B", 1),
            ("A", "C", 4),
            ("B", "C", 2),
            ("B", "D", 5),
            ("C", "D", 1),
        ),
    )

    result = prim_mst(graph, "A")

    assert result.is_spanning_tree
    assert result.start_id == "A"
    assert [(road.start_id, road.end_id) for road in result.selected_roads] == [
        ("A", "B"),
        ("B", "C"),
        ("C", "D"),
    ]
    assert result.total_cost == 4
    assert len(result.selected_roads) == len(graph.get_districts()) - 1


def test_prim_chooses_low_cost_route_among_multiple_paths() -> None:
    graph = make_graph(
        ("A", "B", "C", "D", "E"),
        (
            ("A", "B", 10),
            ("A", "C", 1),
            ("B", "C", 2),
            ("B", "D", 2),
            ("C", "D", 8),
            ("C", "E", 5),
            ("D", "E", 1),
        ),
    )

    result = prim_mst(graph, "A")

    assert result.is_spanning_tree
    assert result.total_cost == 6
    assert len(result.selected_roads) == 4


def test_prim_uses_the_requested_starting_district() -> None:
    graph = make_graph(
        ("A", "B", "C"),
        (("A", "B", 5), ("B", "C", 2), ("A", "C", 1)),
    )

    result = prim_mst(graph, "B")

    assert result.start_id == "B"
    assert result.steps[0].visited_after == ("B",)
    assert result.total_cost == 3
    assert len(result.selected_roads) == 2


def test_equal_weight_choices_are_valid_minimum_edges() -> None:
    graph = make_graph(
        ("A", "B", "C", "D"),
        (
            ("A", "B", 1),
            ("A", "C", 1),
            ("B", "C", 1),
            ("B", "D", 1),
            ("C", "D", 1),
        ),
    )

    result = prim_mst(graph, "A")

    assert result.is_spanning_tree
    assert result.total_cost == 3
    assert len(result.selected_roads) == 3
    for step in result.steps:
        if step.action != "select":
            continue
        assert step.selected_road in step.eligible_roads
        assert step.selected_road is not None
        assert step.selected_road.cost == min(
            road.cost for road in step.eligible_roads
        )
        visited_before = set(step.visited_before)
        road_endpoints = {
            step.selected_road.start_id,
            step.selected_road.end_id,
        }
        assert len(visited_before & road_endpoints) == 1


def test_one_district_has_a_zero_cost_spanning_tree() -> None:
    graph = make_graph(("A",), ())

    result = prim_mst(graph, "A")

    assert result.is_spanning_tree
    assert result.selected_roads == ()
    assert result.total_cost == 0
    assert result.unreached_districts == ()
    assert [step.action for step in result.steps] == ["start"]


def test_empty_graph_has_no_spanning_tree() -> None:
    result = prim_mst(Graph())

    assert not result.is_spanning_tree
    assert result.start_id is None
    assert result.selected_roads == ()
    assert result.total_cost is None
    assert result.steps == ()


def test_disconnected_graph_reports_unreached_districts_without_mst_cost() -> None:
    graph = make_graph(
        ("A", "B", "C", "D"),
        (("A", "B", 2), ("C", "D", 1)),
    )

    result = prim_mst(graph, "A")

    assert not result.is_spanning_tree
    assert result.selected_roads == (graph.get_road("A", "B"),)
    assert result.total_cost is None
    assert result.unreached_districts == ("C", "D")
    assert all(not step.rejected_roads for step in result.steps)


def test_multiple_districts_without_roads_are_disconnected() -> None:
    graph = make_graph(("A", "B"), ())

    result = prim_mst(graph, "A")

    assert not result.is_spanning_tree
    assert result.selected_roads == ()
    assert result.total_cost is None
    assert result.unreached_districts == ("B",)


def test_cycle_candidate_is_rejected_with_reason() -> None:
    graph = make_graph(
        ("A", "B", "C"),
        (("A", "B", 1), ("A", "C", 3), ("B", "C", 2)),
    )

    result = prim_mst(graph, "A")
    rejected = [
        rejected_road
        for step in result.steps
        for rejected_road in step.rejected_roads
    ]

    assert result.is_spanning_tree
    assert len(rejected) == 1
    assert rejected[0].road == graph.get_road("A", "C")
    assert rejected[0].reason == CYCLE_REJECTION_REASON


def test_invalid_start_district_is_reported() -> None:
    graph = make_graph(("A",), ())

    with pytest.raises(ValueError, match="Starting district ID"):
        prim_mst(graph, "missing")


def test_steps_record_eligible_roads_and_cumulative_cost() -> None:
    graph = make_graph(
        ("A", "B", "C"),
        (("A", "B", 2), ("A", "C", 4), ("B", "C", 1)),
    )

    result = prim_mst(graph, "A")
    selections = [step for step in result.steps if step.action == "select"]

    assert [step.total_cost for step in selections] == [2, 3]
    assert selections[0].visited_before == ("A",)
    assert selections[0].visited_after == ("A", "B")
    assert {road.cost for road in selections[0].eligible_roads} == {2, 4}
    assert {road.cost for road in selections[1].eligible_roads} == {1, 4}
