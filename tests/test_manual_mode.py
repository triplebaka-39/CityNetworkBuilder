import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QGraphicsLineItem, QLabel

from main_window import MainWindow
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


def click_road(window: MainWindow, start_id: str, end_id: str) -> None:
    start = window.graph.get_district(start_id).position
    end = window.graph.get_district(end_id).position
    assert start is not None and end is not None
    click_scene_point(
        window,
        QPointF((start[0] + end[0]) / 2, (start[1] + end[1]) / 2),
    )


def road_item(window: MainWindow, start_id: str, end_id: str) -> QGraphicsLineItem:
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


def make_manual_window(qapp: QApplication) -> MainWindow:
    window = MainWindow()
    window.resize(1100, 720)
    window.show()
    for district_id, name, position in (
        ("a", "Alpha", (150, 250)),
        ("b", "Bravo", (300, 130)),
        ("c", "Charlie", (450, 250)),
        ("d", "Delta", (380, 420)),
        ("e", "Echo", (200, 420)),
    ):
        window.graph.add_district(district_id, name, position)
    for start_id, end_id, cost in (
        ("a", "b", 2),
        ("a", "c", 2),
        ("a", "e", 5),
        ("b", "c", 1),
        ("b", "d", 3),
        ("c", "d", 3),
        ("d", "e", 1),
        ("c", "e", 8),
    ):
        window.graph.add_road(start_id, end_id, cost)
    qapp.processEvents()
    return window


def test_manual_mode_validates_choices_and_completes_equal_cost_tree(
    qapp: QApplication,
) -> None:
    window = make_manual_window(qapp)
    original_state = window.graph.get_state()

    click_scene_point(window, QPointF(150, 250))
    window.manual_mode_button.click()
    notification = window.canvas.findChild(QLabel, "stepNotification")
    assert notification is not None
    assert notification.isVisible()
    assert notification.text() == "We start at Alpha."
    assert window._manual_visited == {"a"}
    assert "first district in our network" in window.algorithm_info.text()
    assert "Total cost: 0" in window.algorithm_info.text()
    assert window.manual_mode_button.isChecked()
    assert window.reset_manual_button.isEnabled()
    assert not window.add_district_button.isEnabled()
    assert not window.add_road_button.isEnabled()
    assert not window.delete_road_button.isEnabled()
    assert not window.delete_district_button.isEnabled()
    assert not window.generate_random_network_button.isEnabled()
    assert not window.reset_button.isEnabled()

    assert road_item(window, "a", "b").pen().style() == Qt.PenStyle.DashLine
    assert road_item(window, "a", "c").pen().style() == Qt.PenStyle.DashLine
    assert road_item(window, "b", "d").pen().style() == Qt.PenStyle.SolidLine

    click_road(window, "a", "e")
    assert notification.text() == (
        "We skipped Alpha - Echo (cost 5) because a cheaper road must go first."
    )
    assert window._manual_visited == {"a"}
    assert "costs more than the lowest-cost choice" in (
        window.algorithm_info.text()
    )
    assert "Alpha - Echo (cost 5)" in window.algorithm_info.text()
    assert "Alpha - Bravo (cost 2)" in window.algorithm_info.text()
    assert "Total cost stays at 0" in window.algorithm_info.text()
    assert any(
        "Rejected: Alpha - Echo (cost 5)"
        in window.algorithm_results.item(index).text()
        for index in range(window.algorithm_results.count())
    )

    click_road(window, "b", "d")
    assert notification.text() == (
        "We skipped Bravo - Delta (cost 3) because it does not reach a new district."
    )
    assert window._manual_visited == {"a"}
    assert "does not reach our network yet" in window.algorithm_info.text()
    assert "Bravo - Delta (cost 3)" in window.algorithm_info.text()

    click_road(window, "a", "c")
    assert notification.text() == (
        "We chose Alpha - Charlie (cost 2) to reach Charlie."
    )
    assert window._manual_visited == {"a", "c"}
    assert window._manual_total_cost == 2
    assert "ties for the lowest cost (2)" in (
        window.algorithm_info.text()
    )
    assert "connects our network at Alpha to new district Charlie" in (
        window.algorithm_info.text()
    )
    assert "Total cost rises from 0 to 2" in window.algorithm_info.text()
    assert (
        road_item(window, "a", "c").pen().color().name().lower()
        == COLORS["teal"].lower()
    )

    click_road(window, "a", "c")
    assert notification.text() == (
        "We skipped Alpha - Charlie (cost 2) because it would make a loop."
    )
    assert len(window._manual_selected_roads) == 1
    assert "would make a loop" in window.algorithm_info.text()
    assert "Total cost stays at 2" in window.algorithm_info.text()
    assert "Alpha - Charlie (cost 2)" in window.algorithm_info.text()
    assert any(
        window.algorithm_results.item(index).text()
        == "Selected: Alpha - Charlie (cost 2)"
        for index in range(window.algorithm_results.count())
    )

    click_road(window, "b", "c")
    assert window._manual_visited == {"a", "b", "c"}
    assert window._manual_total_cost == 3
    click_road(window, "b", "d")
    assert window._manual_visited == {"a", "b", "c", "d"}
    click_road(window, "d", "e")
    assert "every district is now connected" in notification.text()
    assert notification.text().count(".") == 1

    assert window._manual_completed
    assert len(window._manual_selected_roads) == 4
    assert window._manual_total_cost == 7
    assert "Final total cost: 7" in window.algorithm_info.text()
    assert window.prim_results_panel.isVisible()
    assert window.prim_results_status.text() == "MST Completed"
    assert window.prim_results_cost.text() == (
        "Total MST construction cost: 7"
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
            window._manual_selected_roads,
            start=1,
        )
    ]

    window.reset_manual_button.click()
    assert window.graph.get_state() == original_state
    assert not window.prim_results_panel.isVisible()
    assert window.algorithm_panel.isVisible()
    assert not window._manual_mode_active
    assert window.canvas._manual_mode_active is False
    assert window.add_district_button.isEnabled()
    assert "network is unchanged" in window.algorithm_info.text()
    window.close()


def test_manual_mode_reports_disconnection_and_graph_changes_invalidate(
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
    window.manual_mode_button.click()
    click_road(window, "north", "south")
    notification = window.canvas.findChild(QLabel, "stepNotification")
    assert notification is not None
    assert notification.text() == (
        "We chose North - South (cost 4) to reach South, but Island cannot be reached."
    )
    assert window._manual_visited == {"north", "south"}
    assert window._manual_disconnected
    assert "No road reaches the remaining districts" in (
        window.algorithm_info.text()
    )
    assert "cannot connect everyone" in window.algorithm_info.text()
    assert "Total so far: 4 (incomplete)" in window.algorithm_info.text()
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

    window.graph.add_road("south", "island", 2)
    assert not window._manual_mode_active
    assert not window.prim_results_panel.isVisible()
    assert window.canvas._manual_mode_active is False
    assert window.graph.get_road("south", "island").cost == 2
    assert "network changed" in window.algorithm_info.text()
    window.close()
