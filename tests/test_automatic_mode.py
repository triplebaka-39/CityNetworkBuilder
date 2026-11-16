import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsLineItem,
    QGraphicsPolygonItem,
    QLabel,
)

import main_window
from graph import Graph
from main_window import MainWindow
from prim import prim_mst
from styles import COLORS


@pytest.fixture
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def click_scene_point(window: MainWindow, point: QPointF) -> None:
    QTest.mouseClick(
        window.canvas.viewport(),
        Qt.MouseButton.LeftButton,
        pos=window.canvas.mapFromScene(point),
    )
    QApplication.processEvents()


def make_connected_window(qapp: QApplication) -> MainWindow:
    window = MainWindow()
    window.resize(1100, 720)
    window.show()
    districts = (
        ("a", "Alpha", (150, 150)),
        ("b", "Bravo", (350, 150)),
        ("c", "Charlie", (550, 150)),
        ("d", "Delta", (550, 350)),
        ("e", "Echo", (150, 350)),
    )
    for district_id, name, position in districts:
        window.graph.add_district(district_id, name, position)
    for start_id, end_id, cost in (
        ("a", "b", 1),
        ("a", "c", 4),
        ("b", "c", 2),
        ("b", "d", 5),
        ("c", "d", 1),
        ("c", "e", 5),
        ("d", "e", 1),
    ):
        window.graph.add_road(start_id, end_id, cost)
    qapp.processEvents()
    return window


def graphics_item_for_road(
    window: MainWindow,
    start_id: str,
    end_id: str,
) -> QGraphicsLineItem:
    return next(
        item
        for item in window.canvas.scene().items()
        if isinstance(item, QGraphicsLineItem)
        and frozenset(
            (
                item.data(window.canvas.ROAD_START_DATA_ROLE),
                item.data(window.canvas.ROAD_END_DATA_ROLE),
            )
        )
        == frozenset((start_id, end_id))
    )


def graphics_item_for_district(
    window: MainWindow,
    district_id: str,
) -> QGraphicsPolygonItem:
    return next(
        item
        for item in window.canvas.scene().items()
        if isinstance(item, QGraphicsPolygonItem)
        and item.data(window.canvas.DISTRICT_DATA_ROLE) == district_id
    )


def test_automatic_mode_uses_step_history_and_restores_graph(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = make_connected_window(qapp)
    original_state = window.graph.get_state()
    calls = 0
    actual_prim_mst = main_window.prim_mst

    def counted_prim_mst(graph: Graph, start_id: str | None = None):
        nonlocal calls
        calls += 1
        return actual_prim_mst(graph, start_id)

    monkeypatch.setattr(main_window, "prim_mst", counted_prim_mst)
    click_scene_point(window, QPointF(150, 150))
    window.automatic_mode_button.click()
    assert any(
        "minimum spanning tree (MST)" in label.text()
        for label in window.panel_scroll.widget().findChildren(QLabel)
    )

    expected_result = prim_mst(window.graph, "a")
    assert window._prim_result == expected_result
    assert calls == 1
    assert len(window._prim_result.steps) > 5
    assert any(step.rejected_roads for step in window._prim_result.steps)
    assert window.canvas.prim_step is None

    window.start_button.click()
    notification = window.canvas.findChild(QLabel, "stepNotification")
    assert notification is not None
    assert notification.isVisible()
    assert notification.text() == "We start at Alpha."
    assert window.canvas.prim_step == window._prim_result.steps[0]
    assert window._prim_step_index == 0
    assert "first district" in window.algorithm_info.text()
    assert "Total construction cost so far: 0" in (
        window.algorithm_info.text()
    )

    window.next_step_button.click()
    assert notification.text() == (
        "We chose Alpha - Bravo (cost 1) to reach Bravo."
    )
    selected_step = window._prim_result.steps[1]
    assert window.canvas.prim_step == selected_step
    assert window._prim_step_index == 1
    assert "has the lowest cost" in window.algorithm_info.text()
    assert "Alpha - Bravo (cost 1)" in window.algorithm_info.text()
    assert "connects our network at Alpha to new district Bravo" in (
        window.algorithm_info.text()
    )
    assert "Total construction cost: 1 (up from 0" in (
        window.algorithm_info.text()
    )
    assert any(
        "Selected: Alpha - Bravo (cost 1)" in
        window.algorithm_results.item(index).text()
        for index in range(window.algorithm_results.count())
    )
    selected_road = selected_step.selected_road
    assert selected_road is not None
    assert (
        graphics_item_for_road(
            window,
            selected_road.start_id,
            selected_road.end_id,
        )
        .pen()
        .color()
        .name()
        .lower()
        == COLORS["teal"].lower()
    )
    assert (
        graphics_item_for_district(window, "a")
        .brush()
        .color()
        .name()
        .lower()
        == COLORS["yellow"].lower()
    )

    eligible_road = next(
        road
        for road in selected_step.eligible_roads
        if road != selected_road
    )
    eligible_item = graphics_item_for_road(
        window,
        eligible_road.start_id,
        eligible_road.end_id,
    )
    assert eligible_item.pen().style() == Qt.PenStyle.DashLine

    window.previous_step_button.click()
    assert window._prim_step_index == 0
    explained_rejection = False
    while window.next_step_button.isEnabled():
        window.next_step_button.click()
        if "We skipped" in window.algorithm_info.text():
            assert "would make a loop" in window.algorithm_info.text()
            explained_rejection = True
    assert explained_rejection
    rejected = next(
        rejected_road
        for step in window._prim_result.steps
        for rejected_road in step.rejected_roads
    )
    rejected_item = graphics_item_for_road(
        window,
        rejected.road.start_id,
        rejected.road.end_id,
    )
    assert rejected_item.pen().style() == Qt.PenStyle.DotLine
    rejected_names = (
        window.graph.get_district(rejected.road.start_id).name,
        window.graph.get_district(rejected.road.end_id).name,
    )
    expected_rejected = (
        f"Rejected: {rejected_names[0]} - {rejected_names[1]} "
        f"(cost {rejected.road.cost:g})"
    )
    assert any(
        expected_rejected in window.algorithm_results.item(index).text()
        for index in range(window.algorithm_results.count())
    )
    assert "Every district is connected" in window.algorithm_info.text()
    assert "Final total: 5" in window.algorithm_info.text()
    assert "every district is already connected" in notification.text()
    assert notification.text().count(".") == 1
    assert window.prim_results_panel.isVisible()
    assert window.prim_results_status.text() == "MST Completed"
    assert window.prim_results_cost.text() == (
        "Total MST construction cost: 5"
    )
    assert window.prim_results_district_count.text() == "Districts: 5"
    assert window.prim_results_road_count.text() == "Selected roads: 4"
    assert window.prim_results_start.text() == "Starting district: Alpha"
    assert [
        window.prim_results_roads.item(index).text()
        for index in range(window.prim_results_roads.count())
    ] == [
        f"{index}. "
        f"{window.graph.get_district(road.start_id).name} - "
        f"{window.graph.get_district(road.end_id).name} "
        f"(cost {road.cost:g})"
        for index, road in enumerate(
            window._prim_result.selected_roads,
            start=1,
        )
    ]
    assert any(
        window.algorithm_results.item(index).text().startswith("Rejected:")
        for index in range(window.algorithm_results.count())
    )
    assert calls == 1

    window.previous_step_button.click()
    assert not window.prim_results_panel.isVisible()
    assert window.algorithm_panel.isVisible()
    window.next_step_button.click()
    assert window.prim_results_panel.isVisible()

    window.reset_visualization_button.click()
    assert window.graph.get_state() == original_state
    assert not window.prim_results_panel.isVisible()
    assert window.algorithm_panel.isVisible()
    assert window.canvas.prim_step is None
    assert window._prim_result is None
    assert all(
        graphics_item_for_district(window, district_id)
        .brush()
        .color()
        .name()
        .lower()
        == COLORS["cream"].lower()
        for district_id in ("a", "b", "c", "d", "e")
    )

    click_scene_point(window, QPointF(150, 150))
    window.automatic_mode_button.click()
    window.start_button.click()
    window.graph.add_road("a", "d", 9)
    assert window._prim_result is None
    assert window.canvas.prim_step is None
    assert window.graph.get_road("a", "d").cost == 9

    click_scene_point(window, QPointF(150, 150))
    window.automatic_mode_button.click()
    window.start_button.click()
    click_scene_point(window, QPointF(350, 150))
    assert window._prim_result is None
    assert window.canvas.prim_step is None
    window.close()


def test_disconnected_automatic_mode_never_claims_an_mst(
    qapp: QApplication,
) -> None:
    window = MainWindow()
    window.resize(1000, 700)
    window.show()
    window.graph.add_district("north", "North", (150, 150))
    window.graph.add_district("south", "South", (350, 150))
    window.graph.add_district("island", "Island", (550, 150))
    window.graph.add_road("north", "south", 4)
    qapp.processEvents()

    click_scene_point(window, QPointF(150, 150))
    window.automatic_mode_button.click()
    assert not window._prim_result.is_spanning_tree
    assert "cannot be reached from North" in window.algorithm_info.text()

    window.start_button.click()
    while window.next_step_button.isEnabled():
        window.next_step_button.click()
    assert "No road reaches the remaining districts" in (
        window.algorithm_info.text()
    )
    assert "Not connected yet: Island" in window.algorithm_info.text()
    assert "Final total:" not in window.algorithm_info.text()
    assert "Total construction cost: 4" in window.algorithm_info.text()
    notification = window.canvas.findChild(QLabel, "stepNotification")
    assert notification is not None
    assert "cannot be reached" in notification.text()
    assert window.prim_results_panel.isVisible()
    assert window.prim_results_status.text() == (
        "Complete MST Could Not Be Created"
    )
    assert window.prim_results_cost.text() == (
        "Total MST construction cost: Unavailable"
    )
    assert window.prim_results_district_count.text() == "Districts: 3"
    assert window.prim_results_road_count.text() == (
        "Selected so far: 1 (partial; not an MST)"
    )
    assert window.prim_results_roads.count() == 1
    assert "No complete MST road list" in (
        window.prim_results_roads.item(0).text()
    )
    assert not any(
        window.algorithm_results.item(index).text().startswith("Rejected:")
        for index in range(window.algorithm_results.count())
    )
    window.close()
