import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsLineItem,
    QGraphicsPolygonItem,
    QGraphicsSimpleTextItem,
    QPushButton,
    QWidget,
)

import main_window
from main_window import MainWindow
from styles import APP_STYLE, COLORS


@pytest.fixture
def qapp() -> QApplication:
    application = QApplication.instance() or QApplication([])
    return application


def click_scene_point(window: MainWindow, point: QPointF) -> None:
    viewport_point = window.canvas.mapFromScene(point)
    QTest.mouseClick(
        window.canvas.viewport(),
        Qt.MouseButton.LeftButton,
        pos=viewport_point,
    )
    QApplication.processEvents()


def test_layout_fits_minimum_window_and_canvas_tracks_resize(
    qapp: QApplication,
) -> None:
    previous_style = qapp.styleSheet()
    qapp.setStyleSheet(APP_STYLE)
    window = MainWindow()
    try:
        window.resize(980, 620)
        window.show()
        qapp.processEvents()

        assert window.width() >= 980
        assert window.height() >= 620
        assert window.canvas.width() >= 520
        assert window.panel_scroll.width() >= 340
        assert (
            window.canvas.geometry().right()
            < window.panel_scroll.geometry().left()
        )
        for name in ("tools", "algorithmControls", "manualControls"):
            row = window.findChild(QWidget, name)
            assert row is not None
            assert all(
                button.geometry().right() < row.width()
                for button in row.findChildren(QPushButton)
            )
        assert window.canvas.horizontalScrollBar().maximum() == 0
        assert window.canvas.verticalScrollBar().maximum() == 0

        previous_width = window.canvas.width()
        window.resize(1120, 740)
        qapp.processEvents()
        assert window.canvas.width() > previous_width
        assert window.canvas.horizontalScrollBar().maximum() == 0
        assert window.canvas.verticalScrollBar().maximum() == 0
    finally:
        window.close()
        qapp.setStyleSheet(previous_style)


def test_adding_and_selecting_districts_and_refreshing_roads(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    names = iter(("North", "Market", "Harbor"))
    monkeypatch.setattr(
        main_window.QInputDialog,
        "getText",
        lambda *_args: (next(names), True),
    )
    window = MainWindow()
    window.resize(1000, 700)
    window.show()
    qapp.processEvents()

    window.add_district_button.click()
    positions = (
        QPointF(160, 150),
        QPointF(360, 150),
        QPointF(560, 150),
    )
    for position in positions:
        click_scene_point(window, position)

    districts = window.graph.get_districts()
    assert [district.name for district in districts] == [
        "North",
        "Market",
        "Harbor",
    ]
    assert [district.position for district in districts] == [
        (160.0, 150.0),
        (360.0, 150.0),
        (560.0, 150.0),
    ]

    before_overlap = len(districts)
    click_scene_point(window, positions[0])
    assert len(window.graph.get_districts()) == before_overlap

    window.add_district_button.click()
    click_scene_point(window, positions[1])
    assert window.canvas.selected_district_id == districts[1].district_id
    selected_node = next(
        item
        for item in window.canvas.scene().items()
        if isinstance(item, QGraphicsPolygonItem)
        and item.data(window.canvas.DISTRICT_DATA_ROLE)
        == districts[1].district_id
    )
    assert (
        selected_node.brush().color().name().lower()
        == COLORS["teal"].lower()
    )

    window.graph.add_road(
        districts[0].district_id,
        districts[1].district_id,
        12.5,
    )
    qapp.processEvents()
    assert any(
        isinstance(item, QGraphicsSimpleTextItem)
        and item.data(window.canvas.ROAD_START_DATA_ROLE) is not None
        and item.text() == "12.5"
        for item in window.canvas.scene().items()
    )
    window.close()


def test_crowded_district_placement_uses_a_clear_grid_position(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main_window.QInputDialog,
        "getText",
        lambda *_args: ("Market", True),
    )
    window = MainWindow()
    window.resize(1000, 700)
    window.show()
    window.graph.add_district("north", "North", (300, 200))
    qapp.processEvents()

    window.add_district_button.click()
    click_scene_point(window, QPointF(380, 200))

    districts = window.graph.get_districts()
    assert len(districts) == 2
    assert districts[0].position == (300.0, 200.0)
    assert districts[1].position is not None
    assert math.dist(districts[0].position, districts[1].position) >= (
        window.canvas.MIN_DISTRICT_SPACING
    )
    assert districts[1].position != (380.0, 200.0)
    assert "clear spot" in window.statusBar().currentMessage()
    window.close()


def test_network_layout_reduces_road_crossings(qapp: QApplication) -> None:
    window = MainWindow()
    window.resize(1360, 800)
    window.show()
    qapp.processEvents()

    edges = ((0, 5), (1, 4), (2, 7), (3, 6))
    default_positions = window.canvas.distributed_positions(8)
    arranged_positions = window.canvas.distributed_positions(8, edges)

    def crossing_count(positions: tuple[tuple[float, float], ...]) -> int:
        return sum(
            window.canvas._segments_intersect(
                positions[first_start],
                positions[first_end],
                positions[second_start],
                positions[second_end],
            )
            for first_index, (first_start, first_end) in enumerate(edges)
            for second_start, second_end in edges[first_index + 1 :]
        )

    assert crossing_count(arranged_positions) < crossing_count(default_positions)
    assert set(arranged_positions) == set(default_positions)
    window.close()


def test_road_cost_label_tracks_district_movement(qapp: QApplication) -> None:
    window = MainWindow()
    window.resize(1000, 700)
    window.show()
    window.graph.add_district("north", "North", (150, 150))
    window.graph.add_district("south", "South", (350, 150))
    window.graph.add_road("north", "south", 7)
    qapp.processEvents()

    def cost_label() -> QGraphicsSimpleTextItem:
        return next(
            item
            for item in window.canvas.scene().items()
            if isinstance(item, QGraphicsSimpleTextItem)
            and item.data(window.canvas.ROAD_START_DATA_ROLE) == "north"
        )

    original_label = cost_label()
    original_center = original_label.sceneBoundingRect().center()
    window.graph.set_district_position("south", (450, 350))
    qapp.processEvents()

    updated_label = cost_label()
    updated_center = updated_label.sceneBoundingRect().center()
    road_line = next(
        item
        for item in window.canvas.scene().items()
        if isinstance(item, QGraphicsLineItem)
        and item.data(window.canvas.ROAD_START_DATA_ROLE) == "north"
        and item.data(window.canvas.ROAD_END_DATA_ROLE) == "south"
    )
    line = road_line.line()
    dx = line.dx()
    dy = line.dy()
    length = line.length()
    along = (
        (updated_center.x() - line.x1()) * dx
        + (updated_center.y() - line.y1()) * dy
    ) / (length * length)
    away_from_road = abs(
        dx * (updated_center.y() - line.y1())
        - dy * (updated_center.x() - line.x1())
    ) / length

    assert updated_label.text() == "7"
    assert (updated_label.data(window.canvas.ROAD_START_DATA_ROLE),
            updated_label.data(window.canvas.ROAD_END_DATA_ROLE)) == (
        "north",
        "south",
    )
    assert updated_center != original_center
    assert 0.19 <= along <= 0.81
    assert away_from_road <= 48.5
    window.close()


def test_five_district_network_and_road_and_district_deletion(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = iter(
        ("North", "Market", "Harbor", "East", "West", "5", "2", "3", "4", "8")
    )
    monkeypatch.setattr(
        main_window.QInputDialog,
        "getText",
        lambda *_args: (next(values), True),
    )
    monkeypatch.setattr(
        main_window.QMessageBox,
        "question",
        lambda *_args: main_window.QMessageBox.StandardButton.Yes,
    )
    window = MainWindow()
    window.resize(1100, 720)
    window.show()
    qapp.processEvents()

    positions = (
        QPointF(150, 150),
        QPointF(350, 150),
        QPointF(550, 150),
        QPointF(550, 350),
        QPointF(150, 350),
    )
    window.add_district_button.click()
    for position in positions:
        click_scene_point(window, position)
    window.add_district_button.click()

    districts = window.graph.get_districts()
    assert len(districts) == 5

    road_endpoints = ((0, 1), (1, 2), (2, 3), (3, 4), (0, 4))
    window.add_road_button.click()
    for start_index, end_index in road_endpoints:
        click_scene_point(window, positions[start_index])
        click_scene_point(window, positions[end_index])

    assert len(window.graph.get_roads()) == 5
    assert {
        frozenset((road.start_id, road.end_id)): road.cost
        for road in window.graph.get_roads()
    } == {
        frozenset((districts[start].district_id, districts[end].district_id)): cost
        for (start, end), cost in zip(road_endpoints, (5, 2, 3, 4, 8))
    }

    window.add_road_button.click()
    click_scene_point(window, QPointF(250, 150))
    selected_road = window.canvas.selected_road
    assert selected_road == (
        districts[0].district_id,
        districts[1].district_id,
    )
    assert window.delete_road_button.isEnabled()
    window.delete_road_button.click()
    assert len(window.graph.get_roads()) == 4
    assert window.canvas.selected_road is None

    click_scene_point(window, positions[2])
    assert window.canvas.selected_district_id == districts[2].district_id
    assert window.delete_district_button.isEnabled()
    window.delete_district_button.click()

    assert len(window.graph.get_districts()) == 4
    remaining_roads = window.graph.get_roads()
    assert len(remaining_roads) == 2
    assert all(
        districts[2].district_id not in (road.start_id, road.end_id)
        for road in remaining_roads
    )
    window.close()


def test_add_road_reports_invalid_selections_and_costs(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    names_and_costs = iter(("North", "Market", "Harbor", "2.5", "-1"))
    errors: list[str] = []
    monkeypatch.setattr(
        main_window.QInputDialog,
        "getText",
        lambda *_args: (next(names_and_costs), True),
    )
    monkeypatch.setattr(
        main_window.QMessageBox,
        "warning",
        lambda *_args: errors.append(_args[2]),
    )
    window = MainWindow()
    window.resize(1000, 700)
    window.show()
    qapp.processEvents()

    positions = (QPointF(150, 150), QPointF(350, 150), QPointF(550, 150))
    window.add_district_button.click()
    for position in positions:
        click_scene_point(window, position)
    window.add_district_button.click()

    window.add_road_button.click()
    click_scene_point(window, positions[0])
    click_scene_point(window, positions[0])
    click_scene_point(window, positions[1])
    click_scene_point(window, positions[0])
    click_scene_point(window, positions[1])
    window.add_road_button.click()
    window.add_road_button.click()
    click_scene_point(window, positions[1])
    click_scene_point(window, positions[2])

    assert len(window.graph.get_roads()) == 1
    assert len(errors) == 3
    assert "different districts" in errors[0]
    assert "already connects" in errors[1]
    assert "finite number" in errors[2]
    window.close()
