import pytest

from graph import District, Graph, Road


def build_graph() -> Graph:
    graph = Graph()
    graph.add_district("north", "North", (10, 20))
    graph.add_district("south", "South")
    graph.add_district("east", "East")
    return graph


def test_add_district_and_retrieve_graph_state() -> None:
    graph = Graph()

    district = graph.add_district("north", "North", (12, 34))
    state = graph.get_state()

    assert district == District("north", "North", (12.0, 34.0))
    assert graph.get_district("north") == district
    assert graph.get_districts() == (district,)
    assert graph.get_adjacency_list() == {"north": {}}
    assert state.districts == (district,)
    assert state.roads == ()
    assert state.adjacency == {"north": {}}


def test_add_district_rejects_duplicate_id_and_blank_fields() -> None:
    graph = Graph()
    graph.add_district("north", "North")

    with pytest.raises(ValueError, match="already exists"):
        graph.add_district("north", "Other North")
    with pytest.raises(ValueError, match="District ID"):
        graph.add_district(" ", "South")
    with pytest.raises(ValueError, match="District name"):
        graph.add_district("south", " ")


def test_delete_district_removes_connected_roads() -> None:
    graph = build_graph()
    graph.add_road("north", "south", 4)
    graph.add_road("north", "east", 2)

    deleted = graph.delete_district("north")

    assert deleted == District("north", "North", (10.0, 20.0))
    assert [district.district_id for district in graph.get_districts()] == [
        "south",
        "east",
    ]
    assert graph.get_roads() == ()
    assert graph.get_neighbors("south") == {}
    assert graph.get_neighbors("east") == {}
    assert graph.get_adjacency_list() == {"south": {}, "east": {}}


def test_delete_unknown_district_reports_error() -> None:
    with pytest.raises(ValueError, match="does not exist"):
        Graph().delete_district("missing")


def test_add_road_is_undirected_and_updates_adjacency() -> None:
    graph = build_graph()

    road = graph.add_road("north", "south", 2.5)

    assert road == Road("north", "south", 2.5)
    assert graph.get_road("north", "south") is road
    assert graph.get_road("south", "north") is road
    assert graph.get_roads() == (road,)
    assert graph.get_neighbors("north") == {"south": road}
    assert graph.get_neighbors("south") == {"north": road}
    assert graph.get_adjacency_list() == {
        "north": {"south": 2.5},
        "south": {"north": 2.5},
        "east": {},
    }


def test_add_road_requires_distinct_existing_districts() -> None:
    graph = build_graph()

    with pytest.raises(ValueError, match="different districts"):
        graph.add_road("north", "north", 1)
    with pytest.raises(ValueError, match="does not exist"):
        graph.add_road("north", "missing", 1)


def test_duplicate_road_is_rejected_in_either_direction() -> None:
    graph = build_graph()
    graph.add_road("north", "south", 2)

    with pytest.raises(ValueError, match="already exists"):
        graph.add_road("south", "north", 3)

    assert len(graph.get_roads()) == 1


@pytest.mark.parametrize(
    "cost",
    [
        -1,
        float("nan"),
        float("inf"),
        float("-inf"),
        "2.5",
        None,
        True,
    ],
)
def test_add_road_rejects_invalid_costs(cost: object) -> None:
    graph = build_graph()

    with pytest.raises(ValueError, match="finite number"):
        graph.add_road("north", "south", cost)  # type: ignore[arg-type]


def test_zero_cost_is_valid_and_road_can_be_deleted() -> None:
    graph = build_graph()
    road = graph.add_road("north", "south", 0)

    assert graph.delete_road("south", "north") is road
    assert graph.get_roads() == ()
    assert graph.get_neighbors("north") == {}
    assert graph.get_neighbors("south") == {}


def test_delete_missing_road_reports_error() -> None:
    graph = build_graph()

    with pytest.raises(ValueError, match="No road exists"):
        graph.delete_road("north", "south")


def test_get_neighbors_returns_a_copy() -> None:
    graph = build_graph()
    road = graph.add_road("north", "south", 1)

    neighbors = graph.get_neighbors("north")
    neighbors.clear()

    assert graph.get_neighbors("north") == {"south": road}


def test_change_listeners_are_notified_after_graph_updates() -> None:
    graph = Graph()
    changes: list[str] = []
    graph.add_change_listener(lambda: changes.append("changed"))

    graph.add_district("north", "North")
    graph.set_district_position("north", (10, 20))
    graph.add_district("south", "South")
    graph.add_road("north", "south", 3)
    graph.delete_road("north", "south")
    graph.clear()

    assert changes == ["changed"] * 6


@pytest.mark.parametrize(
    "position",
    [
        (1,),
        (1, float("nan")),
        (float("inf"), 2),
        ("x", 2),
    ],
)
def test_add_district_rejects_invalid_positions(position: tuple[object, ...]) -> None:
    with pytest.raises(ValueError, match="finite coordinates"):
        Graph().add_district("north", "North", position)  # type: ignore[arg-type]
