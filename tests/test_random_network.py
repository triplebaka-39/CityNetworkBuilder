import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import math

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
)

import main_window
from main_window import MainWindow
from prim import get_eligible_roads, minimum_eligible_cost, prim_mst


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


def select_district(window: MainWindow, district_id: str) -> None:
    position = window.graph.get_district(district_id).position
    assert position is not None
    click_scene_point(window, QPointF(*position))


def test_generated_network_is_connected_and_works_in_both_modes(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    confirmations: list[str] = []
    def reject_unexpected_confirmation(*args):
        confirmations.append(args[2])
        return main_window.QMessageBox.StandardButton.No

    monkeypatch.setattr(
        main_window.QMessageBox,
        "question",
        reject_unexpected_confirmation,
    )
    window = MainWindow()
    window.resize(1100, 720)
    window.show()
    qapp.processEvents()

    window.generate_random_network_button.click()

    districts = window.graph.get_districts()
    roads = window.graph.get_roads()
    assert confirmations == []
    assert len(districts) == 8
    assert [district.name for district in districts] == [
        "District A",
        "District B",
        "District C",
        "District D",
        "District E",
        "District F",
        "District G",
        "District H",
    ]
    positions = [district.position for district in districts]
    assert all(position is not None for position in positions)
    assert len(set(positions)) == len(positions)
    assert all(
        math.dist(positions[first], positions[second])
        >= window.canvas.GRID_SPACING
        for first in range(len(positions))
        for second in range(first + 1, len(positions))
    )
    assert len(roads) >= len(districts) - 1
    assert len(roads) <= len(districts) - 1 + 5
    assert all(road.start_id != road.end_id and road.cost >= 0 for road in roads)
    assert len(
        {frozenset((road.start_id, road.end_id)) for road in roads}
    ) == len(roads)
    assert sum(
        isinstance(item, QGraphicsLineItem)
        and item.data(window.canvas.ROAD_START_DATA_ROLE) is not None
        and item.data(window.canvas.ROAD_END_DATA_ROLE) is not None
        for item in window.canvas.scene().items()
    ) == len(roads)
    cost_labels = [
        item
        for item in window.canvas.scene().items()
        if isinstance(item, QGraphicsSimpleTextItem)
        and item.data(window.canvas.ROAD_START_DATA_ROLE) is not None
    ]
    for label in cost_labels:
        road = window.graph.get_road(
            label.data(window.canvas.ROAD_START_DATA_ROLE),
            label.data(window.canvas.ROAD_END_DATA_ROLE),
        )
        start = window.graph.get_district(road.start_id).position
        end = window.graph.get_district(road.end_id).position
        assert start is not None and end is not None
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.hypot(dx, dy)
        center = label.sceneBoundingRect().center()
        along = (
            (center.x() - start[0]) * dx
            + (center.y() - start[1]) * dy
        ) / (length * length)
        away_from_road = abs(
            dx * (center.y() - start[1])
            - dy * (center.x() - start[0])
        ) / length
        assert 0.19 <= along <= 0.81
        assert away_from_road <= 48.5
    assert sum(
        isinstance(item, QGraphicsSimpleTextItem)
        and item.data(window.canvas.ROAD_START_DATA_ROLE) is not None
        for item in window.canvas.scene().items()
    ) == len(roads)
    cost_label_backgrounds = [
        item
        for item in window.canvas.scene().items()
        if isinstance(item, QGraphicsRectItem)
        and item.data(window.canvas.ROAD_START_DATA_ROLE) is not None
    ]
    assert all(
        not first.sceneBoundingRect().intersects(second.sceneBoundingRect())
        for index, first in enumerate(cost_label_backgrounds)
        for second in cost_label_backgrounds[index + 1 :]
    )

    start_id = districts[0].district_id
    expected_result = prim_mst(window.graph, start_id)
    assert expected_result.is_spanning_tree
    assert len(expected_result.selected_roads) == len(districts) - 1
    assert expected_result.total_cost is not None

    select_district(window, start_id)
    window.automatic_mode_button.click()
    assert window._prim_result is not None
    assert window._prim_result.is_spanning_tree
    window.start_button.click()
    while window.next_step_button.isEnabled():
        window.next_step_button.click()
    assert window.prim_results_status.text() == "MST Completed"
    assert window.prim_results_cost.text() == (
        f"Total MST construction cost: {expected_result.total_cost:g}"
    )

    window.reset_visualization_button.click()
    select_district(window, start_id)
    window.manual_mode_button.click()
    for _ in range(len(districts) - 1):
        eligible = get_eligible_roads(window.graph, window._manual_visited)
        minimum_cost = minimum_eligible_cost(eligible)
        assert minimum_cost is not None
        selected = next(road for road in eligible if road.cost == minimum_cost)
        window._handle_manual_road(selected.start_id, selected.end_id)

    assert window._manual_completed
    assert len(window._manual_selected_roads) == len(districts) - 1
    assert window.prim_results_status.text() == "MST Completed"
    assert window.prim_results_cost.text() == (
        f"Total MST construction cost: {window._manual_total_cost:g}"
    )
    window.close()


def test_replacing_existing_network_requires_confirmation_and_resets_run(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = MainWindow()
    window.resize(1000, 700)
    window.show()
    qapp.processEvents()
    window.graph.add_district("north", "North", (150, 150))
    window.graph.add_district("south", "South", (350, 150))
    window.graph.add_road("north", "south", 4)
    select_district(window, "north")
    window.automatic_mode_button.click()
    window.start_button.click()
    while window.next_step_button.isEnabled():
        window.next_step_button.click()
    original_state = window.graph.get_state()

    answers = iter(
        (
            main_window.QMessageBox.StandardButton.No,
            main_window.QMessageBox.StandardButton.Yes,
        )
    )
    questions: list[str] = []

    def confirm_replacement(*args):
        questions.append(args[2])
        return next(answers)

    monkeypatch.setattr(
        main_window.QMessageBox,
        "question",
        confirm_replacement,
    )

    window.generate_random_network_button.click()
    assert window.graph.get_state() == original_state
    assert window._prim_result is not None
    assert window.prim_results_panel.isVisible()

    window.generate_random_network_button.click()
    assert len(questions) == 2
    assert len(window.graph.get_districts()) == 8
    assert all(
        district.name not in ("North", "South")
        for district in window.graph.get_districts()
    )
    assert window._prim_result is None
    assert window.canvas.prim_step is None
    assert window.canvas.selected_district_id is None
    assert not window.prim_results_panel.isVisible()
    assert window.algorithm_panel.isVisible()
    window.close()
