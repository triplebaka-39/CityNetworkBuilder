from __future__ import annotations

import math
import random
from itertools import permutations
from typing import Iterable, Literal, TypeAlias

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QMouseEvent,
    QPainter,
    QPen,
    QPolygonF,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPolygonItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QLabel,
    QWidget,
)

from graph import Graph, Position, Road
from prim import PrimStep
from styles import COLORS, TITLE_FONT, UI_FONT


def _font(size: int, bold: bool = False, title: bool = False) -> QFont:
    """Pixel font with a safe fallback if the bundled fonts did not load."""
    font = QFont()
    font.setFamilies([TITLE_FONT if title else UI_FONT, UI_FONT, "Segoe UI"])
    font.setPointSize(size)
    if bold:
        font.setWeight(QFont.Weight.Bold)
    font.setStyleStrategy(QFont.StyleStrategy.NoAntialias)
    return font


ToolName: TypeAlias = Literal["add_district", "add_road"]
RoadKey: TypeAlias = tuple[str, str]


class CityCanvas(QGraphicsView):
    districtPlacementRequested = Signal(QPointF)
    districtActivated = Signal(str)
    roadActivated = Signal(str, str)
    selectionChanged = Signal()
    statusMessageRequested = Signal(str)

    NODE_RADIUS = 30
    NODE_DIAMETER = NODE_RADIUS * 2
    MIN_DISTRICT_SPACING = 160.0
    GRID_SPACING = 190.0
    DISTRICT_DATA_ROLE = 0
    ROAD_START_DATA_ROLE = 1
    ROAD_END_DATA_ROLE = 2

    def __init__(self, graph: Graph, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.graph = graph
        self._active_tool: ToolName | None = None
        self._selected_district_id: str | None = None
        self._road_start_highlight_id: str | None = None
        self._selected_road: RoadKey | None = None
        self._prim_step: PrimStep | None = None
        self._manual_mode_active = False
        self._manual_visited_ids: frozenset[str] = frozenset()
        self._manual_eligible_roads: tuple[Road, ...] = ()
        self._manual_selected_roads: tuple[Road, ...] = ()
        self._step_notification = QLabel(self.viewport())
        self._step_notification.setObjectName("stepNotification")
        self._step_notification.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._step_notification.setWordWrap(True)
        self._step_notification.setFont(_font(10, bold=True))
        self._step_notification.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        self._step_notification.hide()
        self._step_notification_timer = QTimer(self)
        self._step_notification_timer.setSingleShot(True)
        self._step_notification_timer.timeout.connect(
            self._step_notification.hide
        )

        self.setObjectName("cityCanvas")
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setFrameShape(self.Shape.NoFrame)
        self.setBackgroundBrush(QColor(COLORS["cream"]))
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setMinimumSize(520, 360)

        self._update_scene_rect()
        self._assign_missing_positions()
        self.graph.add_change_listener(self.refresh)
        self.refresh()

    @property
    def selected_district_id(self) -> str | None:
        return self._selected_district_id

    @property
    def add_district_mode(self) -> bool:
        return self._active_tool == "add_district"

    def set_add_district_mode(self, enabled: bool) -> None:
        self.set_active_tool("add_district" if enabled else None)

    @property
    def active_tool(self) -> ToolName | None:
        return self._active_tool

    @property
    def selected_road(self) -> RoadKey | None:
        return self._selected_road

    @property
    def prim_step(self) -> PrimStep | None:
        return self._prim_step

    def set_prim_step(self, step: PrimStep | None) -> None:
        if self._prim_step == step:
            return
        self._prim_step = step
        self.refresh()

    def set_manual_state(
        self,
        active: bool,
        visited_ids: Iterable[str] = (),
        eligible_roads: Iterable[Road] = (),
        selected_roads: Iterable[Road] = (),
    ) -> None:
        self._manual_mode_active = active
        self._manual_visited_ids = frozenset(visited_ids) if active else frozenset()
        self._manual_eligible_roads = tuple(eligible_roads) if active else ()
        self._manual_selected_roads = tuple(selected_roads) if active else ()
        self.refresh()

    def show_step_notification(self, message: str) -> None:
        message = " ".join(message.split())
        if not message:
            self.clear_step_notification()
            return

        self._step_notification_timer.stop()
        self._step_notification.setText(message)
        self._position_step_notification()
        self._step_notification.show()
        self._step_notification.raise_()
        self._step_notification_timer.start(3000)

    def clear_step_notification(self) -> None:
        self._step_notification_timer.stop()
        self._step_notification.clear()
        self._step_notification.hide()

    def set_active_tool(self, tool: ToolName | None) -> None:
        if self._active_tool == tool:
            return
        self._active_tool = tool
        self._road_start_highlight_id = None
        self.setCursor(
            Qt.CursorShape.CrossCursor if tool is not None else Qt.CursorShape.ArrowCursor
        )
        self.clear_selection()

    def set_road_start_district(self, district_id: str | None) -> None:
        if self._road_start_highlight_id == district_id:
            return
        self._road_start_highlight_id = district_id
        self.refresh()

    def refresh(self) -> None:
        selection_changed = False
        if self._selected_district_id is not None:
            try:
                self.graph.get_district(self._selected_district_id)
            except ValueError:
                self._selected_district_id = None
                selection_changed = True
        if self._selected_road is not None:
            try:
                self.graph.get_road(*self._selected_road)
            except ValueError:
                self._selected_road = None
                selection_changed = True
        if self._road_start_highlight_id is not None:
            try:
                self.graph.get_district(self._road_start_highlight_id)
            except ValueError:
                self._road_start_highlight_id = None

        self._scene.clear()
        districts = self.graph.get_districts()
        roads = self.graph.get_roads()
        algorithm_active = (
            self._prim_step is not None or self._manual_mode_active
        )
        if self._prim_step is not None:
            visited_ids = frozenset(self._prim_step.visited_after)
            eligible_roads = {
                frozenset((road.start_id, road.end_id))
                for road in self._prim_step.eligible_roads
            }
            selected_roads = (
                {
                    frozenset(
                        (
                            self._prim_step.selected_road.start_id,
                            self._prim_step.selected_road.end_id,
                        )
                    )
                }
                if self._prim_step.selected_road is not None
                else set()
            )
        else:
            visited_ids = self._manual_visited_ids
            eligible_roads = {
                frozenset((road.start_id, road.end_id))
                for road in self._manual_eligible_roads
            }
            selected_roads = {
                frozenset((road.start_id, road.end_id))
                for road in self._manual_selected_roads
            }
        rejected_roads = (
            {
                frozenset((item.road.start_id, item.road.end_id))
                for item in self._prim_step.rejected_roads
            }
            if self._prim_step is not None
            else set()
        )
        district_obstacles = [
            self._district_obstacle_rect(district.name, district.position)
            for district in districts
            if district.position is not None
        ]
        road_label_obstacles: list[QRectF] = []

        for road in roads:
            start = self.graph.get_district(road.start_id).position
            end = self.graph.get_district(road.end_id).position
            if start is None or end is None:
                continue
            road_key = frozenset((road.start_id, road.end_id))
            selected = (
                road_key in selected_roads
                if algorithm_active
                else self._selected_road is not None
                and frozenset(self._selected_road) == road_key
            )
            self._draw_road(
                start,
                end,
                road.cost,
                (road.start_id, road.end_id),
                selected,
                road_key in eligible_roads,
                road_key in rejected_roads,
                road_label_obstacles,
                district_obstacles,
            )

        for district in districts:
            if district.position is not None:
                self._draw_district(
                    district.name,
                    district.district_id,
                    district.position,
                    not algorithm_active
                    and district.district_id
                    in (
                        self._selected_district_id,
                        self._road_start_highlight_id,
                    ),
                    algorithm_active and district.district_id in visited_ids,
                    algorithm_active,
                )

        if not districts:
            self._draw_empty_state()
        self._update_scene_rect()
        if selection_changed:
            self.selectionChanged.emit()

    def drawBackground(self, painter: QPainter, rect) -> None:
        painter.fillRect(rect, QColor(COLORS["cream"]))
        dot = QColor(COLORS["brown"])
        dot.setAlpha(45)
        step = 40
        first_x = int(rect.left() // step) * step
        first_y = int(rect.top() // step) * step
        y = first_y
        while y <= rect.bottom():
            x = first_x
            while x <= rect.right():
                painter.fillRect(int(x), int(y), 3, 3, dot)
                x += step
            y += step

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        position = self.mapToScene(event.position().toPoint())
        district_id = self._district_at(position)
        if self._active_tool == "add_district":
            if district_id is not None or self._overlaps_district(position):
                self.statusMessageRequested.emit(
                    "Choose an empty spot away from existing districts."
                )
            else:
                self.districtPlacementRequested.emit(position)
            event.accept()
            return

        if self._active_tool == "add_road":
            if district_id is None:
                self.statusMessageRequested.emit("Select a district to build a road.")
            else:
                self._set_selection(district_id, None)
                self.districtActivated.emit(district_id)
            event.accept()
            return

        if self._manual_mode_active:
            if district_id is not None:
                self.statusMessageRequested.emit(
                    "Choose a highlighted road, not a district, in Manual Mode."
                )
                event.accept()
                return
            road_key = self._road_at(position)
            if road_key is None:
                self.statusMessageRequested.emit(
                    "Select a road on the map to test your Prim's choice."
                )
            else:
                self.roadActivated.emit(*road_key)
            event.accept()
            return

        road_key = None if district_id is not None else self._road_at(position)
        self._set_selection(district_id, road_key)
        event.accept()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._update_scene_rect()
        if self._step_notification.isVisible():
            self._position_step_notification()

    def _position_step_notification(self) -> None:
        viewport = self.viewport()
        self._step_notification.setMaximumWidth(
            max(120, min(520, viewport.width() - 32))
        )
        self._step_notification.adjustSize()
        self._step_notification.move(
            max(8, (viewport.width() - self._step_notification.width()) // 2),
            max(
                8,
                viewport.height() - self._step_notification.height() - 14,
            ),
        )

    def distributed_positions(
        self,
        count: int,
        edges: Iterable[tuple[int, int]] = (),
    ) -> tuple[Position, ...]:
        if count <= 0:
            return ()

        bounds = self.mapToScene(self.viewport().rect()).boundingRect()
        margin = self.NODE_RADIUS + 30
        usable_width = max(
            self.GRID_SPACING,
            bounds.width() - 2 * margin,
        )
        usable_height = max(
            self.GRID_SPACING,
            bounds.height() - 2 * margin,
        )
        aspect_ratio = usable_width / usable_height
        desired_columns = math.ceil(math.sqrt(count * aspect_ratio))
        max_columns = max(
            1,
            int(usable_width // self.GRID_SPACING) + 1,
        )
        columns = min(count, desired_columns, max_columns)
        rows = math.ceil(count / columns)
        grid_height = (rows - 1) * self.GRID_SPACING
        start_y = (
            bounds.top() + margin
            if grid_height > usable_height
            else max(bounds.top() + margin, bounds.center().y() - grid_height / 2)
        )

        positions: list[Position] = []
        for index in range(count):
            row, column = divmod(index, columns)
            row_count = min(columns, count - row * columns)
            row_width = (row_count - 1) * self.GRID_SPACING
            start_x = max(
                bounds.left() + margin,
                bounds.center().x() - row_width / 2,
            )
            if start_x + row_width > bounds.right() - margin:
                start_x = (
                    bounds.right() - margin - row_width
                    if row_width <= usable_width
                    else bounds.left() + margin
                )
            positions.append(
                (
                    round(start_x + column * self.GRID_SPACING, 2),
                    round(start_y + row * self.GRID_SPACING, 2),
                )
            )
        edge_indices = tuple(
            (start, end)
            for start, end in edges
            if start != end
            and 0 <= start < count
            and 0 <= end < count
        )
        if edge_indices:
            positions = self._reduce_edge_crossings(positions, edge_indices)
        return tuple(positions)

    def _reduce_edge_crossings(
        self,
        positions: list[Position],
        edges: tuple[tuple[int, int], ...],
    ) -> list[Position]:
        edge_pairs = tuple(
            (edges[first], edges[second])
            for first in range(len(edges))
            for second in range(first + 1, len(edges))
            if not set(edges[first]).intersection(edges[second])
        )
        if not edge_pairs:
            return positions
        if len(positions) <= 8:
            return self._exact_edge_layout(positions, edges, edge_pairs)

        def score(order: list[int]) -> tuple[int, float]:
            assigned = [positions[index] for index in order]
            crossings = sum(
                self._segments_intersect(
                    assigned[first[0]],
                    assigned[first[1]],
                    assigned[second[0]],
                    assigned[second[1]],
                )
                for first, second in edge_pairs
            )
            total_length = sum(
                math.dist(assigned[start], assigned[end])
                for start, end in edges
            )
            return crossings, total_length

        seed = sum((start + 1) * 31 + (end + 1) * 17 for start, end in edges)
        rng = random.Random(seed)
        best_order = list(range(len(positions)))
        best_score = score(best_order)
        for restart in range(8):
            order = list(range(len(positions)))
            if restart:
                rng.shuffle(order)
            current_score = score(order)
            for step in range(400):
                first, second = rng.sample(range(len(order)), 2)
                order[first], order[second] = order[second], order[first]
                candidate_score = score(order)
                candidate_value = (
                    candidate_score[0] * 100
                    + candidate_score[1] / self.GRID_SPACING
                )
                current_value = (
                    current_score[0] * 100
                    + current_score[1] / self.GRID_SPACING
                )
                temperature = 20 * (1 - step / 400) + 0.1
                if candidate_value <= current_value or rng.random() < math.exp(
                    (current_value - candidate_value) / temperature
                ):
                    current_score = candidate_score
                else:
                    order[first], order[second] = order[second], order[first]
                if current_score < best_score:
                    best_score = current_score
                    best_order = order.copy()

        return [positions[index] for index in best_order]

    def _exact_edge_layout(
        self,
        positions: list[Position],
        edges: tuple[tuple[int, int], ...],
        edge_pairs: tuple[
            tuple[tuple[int, int], tuple[int, int]], ...
        ],
    ) -> list[Position]:
        assignments = permutations(range(len(positions)), 4)
        crossing_lookup = {
            assignment: self._segments_intersect(
                positions[assignment[0]],
                positions[assignment[1]],
                positions[assignment[2]],
                positions[assignment[3]],
            )
            for assignment in assignments
        }
        distance_lookup = [
            [
                math.dist(start, end)
                for end in positions
            ]
            for start in positions
        ]
        best_order = tuple(range(len(positions)))
        best_score = (len(edge_pairs) + 1, math.inf)
        for order in permutations(range(len(positions))):
            crossing_count = sum(
                crossing_lookup[
                    (
                        order[first[0]],
                        order[first[1]],
                        order[second[0]],
                        order[second[1]],
                    )
                ]
                for first, second in edge_pairs
            )
            if crossing_count > best_score[0]:
                continue
            total_length = sum(
                distance_lookup[order[start]][order[end]]
                for start, end in edges
            )
            candidate_score = (crossing_count, total_length)
            if candidate_score < best_score:
                best_order = order
                best_score = candidate_score
        return [positions[index] for index in best_order]

    @staticmethod
    def _segments_intersect(
        start_a: Position,
        end_a: Position,
        start_b: Position,
        end_b: Position,
    ) -> bool:
        def orientation(start: Position, end: Position, point: Position) -> float:
            return (
                (end[0] - start[0]) * (point[1] - start[1])
                - (end[1] - start[1]) * (point[0] - start[0])
            )

        def on_segment(start: Position, end: Position, point: Position) -> bool:
            return (
                min(start[0], end[0]) - 1e-8
                <= point[0]
                <= max(start[0], end[0]) + 1e-8
                and min(start[1], end[1]) - 1e-8
                <= point[1]
                <= max(start[1], end[1]) + 1e-8
            )

        o1 = orientation(start_a, end_a, start_b)
        o2 = orientation(start_a, end_a, end_b)
        o3 = orientation(start_b, end_b, start_a)
        o4 = orientation(start_b, end_b, end_a)
        if (
            ((o1 > 1e-8 and o2 < -1e-8) or (o1 < -1e-8 and o2 > 1e-8))
            and ((o3 > 1e-8 and o4 < -1e-8) or (o3 < -1e-8 and o4 > 1e-8))
        ):
            return True
        return (
            abs(o1) <= 1e-8 and on_segment(start_a, end_a, start_b)
            or abs(o2) <= 1e-8 and on_segment(start_a, end_a, end_b)
            or abs(o3) <= 1e-8 and on_segment(start_b, end_b, start_a)
            or abs(o4) <= 1e-8 and on_segment(start_b, end_b, end_a)
        )

    def position_for_new_district(
        self,
        requested: QPointF,
        name: str,
    ) -> Position:
        requested_position = (requested.x(), requested.y())
        if self._position_has_clearance(requested_position, name):
            return requested_position

        candidate_count = len(self.graph.get_districts()) + 1
        while True:
            available = [
                position
                for position in self.distributed_positions(candidate_count)
                if self._position_has_clearance(position, name)
            ]
            if available:
                return min(
                    available,
                    key=lambda position: math.dist(
                        requested_position,
                        position,
                    ),
                )
            candidate_count *= 2

    def ensure_position_visible(self, position: Position) -> None:
        self.ensureVisible(
            QRectF(
                position[0] - self.NODE_RADIUS,
                position[1] - self.NODE_RADIUS,
                self.NODE_DIAMETER,
                self.NODE_DIAMETER,
            ),
            20,
            20,
        )

    def _assign_missing_positions(self) -> None:
        districts = self.graph.get_districts()
        proposed_positions = self.distributed_positions(len(districts))
        for index, district in enumerate(districts):
            if district.position is not None:
                continue
            requested = QPointF(*proposed_positions[index])
            position = self.position_for_new_district(requested, district.name)
            self.graph.set_district_position(district.district_id, position)

    def _position_has_clearance(
        self,
        position: Position,
        name: str,
    ) -> bool:
        x, y = position
        node_rect = QRectF(
            x - self.NODE_RADIUS,
            y - self.NODE_RADIUS,
            self.NODE_DIAMETER,
            self.NODE_DIAMETER,
        ).adjusted(-8, -8, 8, 8)
        label_rect = self._district_label_rect(position, name)

        for district in self.graph.get_districts():
            other_position = district.position
            if other_position is None:
                continue
            if (
                math.dist(position, other_position)
                < self.MIN_DISTRICT_SPACING
            ):
                return False

            other_node_rect = QRectF(
                other_position[0] - self.NODE_RADIUS,
                other_position[1] - self.NODE_RADIUS,
                self.NODE_DIAMETER,
                self.NODE_DIAMETER,
            ).adjusted(-8, -8, 8, 8)
            other_label_rect = self._district_label_rect(
                other_position,
                district.name,
            )
            if (
                node_rect.intersects(other_node_rect)
                or node_rect.intersects(other_label_rect)
                or label_rect.intersects(other_node_rect)
                or label_rect.intersects(other_label_rect)
            ):
                return False
        return True

    def _district_label_rect(
        self,
        position: Position,
        name: str,
    ) -> QRectF:
        metrics = QFontMetricsF(_font(11, bold=True))
        label_width = metrics.horizontalAdvance(name)
        return QRectF(
            position[0] - label_width / 2,
            position[1] + self.NODE_RADIUS + 7,
            label_width,
            metrics.height(),
        ).adjusted(-6, -3, 6, 3)

    def _draw_road(
        self,
        start: Position,
        end: Position,
        cost: float,
        road_key: RoadKey,
        selected: bool,
        eligible: bool,
        rejected: bool,
        road_label_obstacles: list[QRectF],
        district_obstacles: list[QRectF],
    ) -> None:
        line_geometry = QLineF(QPointF(*start), QPointF(*end))
        outline_width = 0
        if selected:
            road_color = COLORS["teal"]
            line_style = Qt.PenStyle.SolidLine
            line_width = 5
            outline_width = 9
        elif rejected:
            road_color = COLORS["red"]
            line_style = Qt.PenStyle.DotLine
            line_width = 4
        elif eligible:
            road_color = COLORS["yellow"]
            line_style = Qt.PenStyle.DashLine
            line_width = 4
            outline_width = 8
        else:
            road_color = COLORS["brown"]
            line_style = Qt.PenStyle.SolidLine
            line_width = 3

        def make_pen(color: str, width: int, style: Qt.PenStyle) -> QPen:
            return QPen(
                QColor(color),
                width,
                style,
                Qt.PenCapStyle.FlatCap,
                Qt.PenJoinStyle.MiterJoin,
            )

        if outline_width:
            outline = QGraphicsLineItem(line_geometry)
            outline.setPen(
                make_pen(COLORS["brown"], outline_width, Qt.PenStyle.SolidLine)
            )
            outline.setZValue(0.9)
            self._scene.addItem(outline)

        line = QGraphicsLineItem(line_geometry)
        line.setData(self.ROAD_START_DATA_ROLE, road_key[0])
        line.setData(self.ROAD_END_DATA_ROLE, road_key[1])
        line.setPen(make_pen(road_color, line_width, line_style))
        line.setZValue(1)
        self._scene.addItem(line)

        label = QGraphicsSimpleTextItem(f"{cost:g}")
        label.setFont(_font(10, bold=True))
        label.setBrush(QColor(COLORS["brown"]))
        label_bounds = label.boundingRect()
        label_position, label_anchor = self._road_label_position(
            start,
            end,
            label_bounds,
            road_label_obstacles,
            district_obstacles,
        )
        label.setPos(label_position)
        connector_line = QLineF(
            label_anchor,
            label_position + label_bounds.center(),
        )
        if connector_line.length() > 6:
            connector = QGraphicsLineItem(connector_line)
            connector.setPen(
                make_pen(COLORS["brown"], 2, Qt.PenStyle.SolidLine)
            )
            connector.setZValue(1.5)
            self._scene.addItem(connector)
        background = QGraphicsRectItem(label_bounds.adjusted(-6, -2, 6, 2))
        background.setPos(label.pos())
        background.setBrush(
            QColor(COLORS["yellow"] if eligible or selected else COLORS["cream"])
        )
        background.setPen(
            make_pen(
                COLORS["red"] if rejected else COLORS["brown"],
                3 if selected else 2,
                Qt.PenStyle.SolidLine,
            )
        )
        background.setData(self.ROAD_START_DATA_ROLE, road_key[0])
        background.setData(self.ROAD_END_DATA_ROLE, road_key[1])
        background.setZValue(2)
        road_label_obstacles.append(
            background.rect().translated(background.pos()).adjusted(-3, -3, 3, 3)
        )
        label.setData(self.ROAD_START_DATA_ROLE, road_key[0])
        label.setData(self.ROAD_END_DATA_ROLE, road_key[1])
        label.setZValue(3)
        self._scene.addItem(background)
        self._scene.addItem(label)

    def _road_label_position(
        self,
        start: Position,
        end: Position,
        label_bounds: QRectF,
        road_label_obstacles: list[QRectF],
        district_obstacles: list[QRectF],
    ) -> tuple[QPointF, QPointF]:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.hypot(dx, dy) or 1
        normal_x = -dy / length
        normal_y = dx / length
        obstacles = road_label_obstacles + district_obstacles
        best_position: QPointF | None = None
        best_anchor: QPointF | None = None
        best_collisions: int | None = None

        along_shifts = tuple(
            dict.fromkeys(
                min(length * fraction, 90.0)
                for fraction in (0.05, 0.1, 0.15, 0.2, 0.25, 0.3)
            )
        )
        fractions = [0.5]
        for shift in along_shifts:
            fractions.extend(
                (
                    max(0.2, 0.5 + shift / length),
                    min(0.8, 0.5 - shift / length),
                )
            )
        fractions = list(dict.fromkeys(fractions))

        candidates = sorted(
            (
                (fraction, offset)
                for fraction in fractions
                for offset in (0, 12, -12, 24, -24, 36, -36, 48, -48)
            ),
            key=lambda candidate: (
                math.hypot(
                    (candidate[0] - 0.5) * length,
                    candidate[1],
                ),
                abs((candidate[0] - 0.5) * length),
            ),
        )
        for fraction, offset in candidates:
            center_x = start[0] + dx * fraction + normal_x * offset
            center_y = start[1] + dy * fraction + normal_y * offset
            position = QPointF(
                round(center_x - label_bounds.width() / 2),
                round(center_y - label_bounds.height() / 2),
            )
            anchor = QPointF(
                start[0] + dx * fraction,
                start[1] + dy * fraction,
            )
            background_rect = label_bounds.translated(position).adjusted(
                -9, -5, 9, 5
            )
            collisions = sum(
                background_rect.intersects(obstacle)
                for obstacle in obstacles
            )
            if collisions == 0:
                return position, anchor
            if best_collisions is None or collisions < best_collisions:
                best_position = position
                best_anchor = anchor
                best_collisions = collisions

        if best_position is not None and best_anchor is not None:
            return best_position, best_anchor
        return (
            QPointF(
                round((start[0] + end[0]) / 2 - label_bounds.width() / 2),
                round((start[1] + end[1]) / 2 - label_bounds.height() / 2),
            ),
            QPointF((start[0] + end[0]) / 2, (start[1] + end[1]) / 2),
        )

    def _district_obstacle_rect(
        self,
        name: str,
        position: Position,
    ) -> QRectF:
        label_metrics = QFontMetricsF(_font(11, bold=True))
        half_width = max(
            self.NODE_RADIUS,
            label_metrics.horizontalAdvance(name) / 2 + 6,
        )
        top = position[1] - self.NODE_RADIUS - 4
        bottom = (
            position[1]
            + self.NODE_RADIUS
            + 7
            + label_metrics.height()
            + 3
        )
        return QRectF(
            position[0] - half_width,
            top,
            half_width * 2,
            bottom - top,
        )

    def _node_polygon(self, radius: float, cut: float = 9.0) -> QPolygonF:
        """Square with chamfered corners: a chunky pixel-style node shape."""
        r, c = radius, cut
        return QPolygonF(
            [
                QPointF(-r + c, -r),
                QPointF(r - c, -r),
                QPointF(r, -r + c),
                QPointF(r, r - c),
                QPointF(r - c, r),
                QPointF(-r + c, r),
                QPointF(-r, r - c),
                QPointF(-r, -r + c),
            ]
        )

    def _draw_district(
        self,
        name: str,
        district_id: str,
        position: Position,
        selected: bool,
        visited: bool,
        algorithm_active: bool,
    ) -> None:
        if selected:
            node_color = COLORS["teal"]
        elif algorithm_active and visited:
            node_color = COLORS["yellow"]
        else:
            node_color = COLORS["cream"]
        marker_color = COLORS["cream"] if selected else COLORS["brown"]

        shadow = QGraphicsPolygonItem(self._node_polygon(self.NODE_RADIUS))
        shadow.setPos(position[0] + 4, position[1] + 4)
        shadow.setBrush(QColor(COLORS["brown"]))
        shadow.setPen(QPen(Qt.PenStyle.NoPen))
        shadow.setZValue(4)
        self._scene.addItem(shadow)

        node = QGraphicsPolygonItem(self._node_polygon(self.NODE_RADIUS))
        node.setPos(QPointF(*position))
        node.setData(self.DISTRICT_DATA_ROLE, district_id)
        node.setBrush(QColor(node_color))
        node.setPen(
            QPen(
                QColor(COLORS["brown"]),
                4 if selected else 3,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.FlatCap,
                Qt.PenJoinStyle.MiterJoin,
            )
        )
        node.setZValue(5)

        marker = QGraphicsRectItem(-6, -6, 12, 12, node)
        marker.setBrush(QColor(marker_color))
        marker.setPen(QPen(Qt.PenStyle.NoPen))
        marker.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        label = QGraphicsSimpleTextItem(name, node)
        label.setFont(_font(11, bold=True))
        label.setBrush(QColor(COLORS["brown"]))
        label_bounds = label.boundingRect()
        label_x = round(-label_bounds.width() / 2)
        label_y = self.NODE_RADIUS + 7
        label.setPos(label_x, label_y)
        label.setZValue(1)
        label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        label_bg = QGraphicsRectItem(
            label_bounds.adjusted(-4, -1, 4, 1), node
        )
        label_bg.setPos(label_x, label_y)
        label_bg.setBrush(QColor(COLORS["cream"]))
        label_bg.setPen(QPen(QColor(COLORS["brown"]), 2))
        label_bg.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        # Insert the background beneath the text.
        label_bg.setParentItem(node)
        label_bg.stackBefore(label)
        self._scene.addItem(node)

    def _draw_empty_state(self) -> None:
        title = self._scene.addSimpleText(
            "A FRESH MAP FOR A NEW CITY", _font(12, title=True)
        )
        title.setBrush(QColor(COLORS["brown"]))
        title.setPos(40, 40)

        hint = self._scene.addSimpleText(
            "Select Add District, then click an empty spot on the map.",
            _font(12),
        )
        hint.setBrush(QColor(COLORS["brown"]))
        hint.setPos(40, 82)

    def _district_at(self, position: QPointF) -> str | None:
        font = _font(11, bold=True)
        label_metrics = QFontMetricsF(font)
        for district in reversed(self.graph.get_districts()):
            if district.position is None:
                continue
            dx = position.x() - district.position[0]
            dy = position.y() - district.position[1]
            if math.hypot(dx, dy) <= self.NODE_RADIUS:
                return district.district_id
            label_half_width = label_metrics.horizontalAdvance(district.name) / 2
            label_top = self.NODE_RADIUS + 7
            if (
                abs(dx) <= label_half_width
                and label_top <= dy <= label_top + label_metrics.height()
            ):
                return district.district_id
        return None

    def _road_at(self, position: QPointF) -> RoadKey | None:
        closest_road: RoadKey | None = None
        closest_distance = 8.0
        for road in self.graph.get_roads():
            start = self.graph.get_district(road.start_id).position
            end = self.graph.get_district(road.end_id).position
            if start is None or end is None:
                continue
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length_squared = dx * dx + dy * dy
            if length_squared == 0:
                distance = math.dist((position.x(), position.y()), start)
            else:
                projection = (
                    (position.x() - start[0]) * dx
                    + (position.y() - start[1]) * dy
                ) / length_squared
                projection = min(1.0, max(0.0, projection))
                closest_point = (
                    start[0] + projection * dx,
                    start[1] + projection * dy,
                )
                distance = math.dist(
                    (position.x(), position.y()),
                    closest_point,
                )
            if distance <= closest_distance:
                closest_distance = distance
                closest_road = (road.start_id, road.end_id)
        return closest_road

    def clear_selection(self) -> None:
        self._set_selection(None, None)

    def _set_selection(
        self,
        district_id: str | None,
        road_key: RoadKey | None,
    ) -> None:
        if (
            self._selected_district_id == district_id
            and self._selected_road == road_key
        ):
            return
        self._selected_district_id = district_id
        self._selected_road = road_key
        self.refresh()
        self.selectionChanged.emit()

    def _overlaps_district(self, position: QPointF) -> bool:
        return any(
            district.position is not None
            and math.dist(
                (position.x(), position.y()),
                district.position,
            )
            < self.NODE_DIAMETER
            for district in self.graph.get_districts()
        )

    def _update_scene_rect(self) -> None:
        positions = [
            district.position
            for district in self.graph.get_districts()
            if district.position is not None
        ]
        margin = self.NODE_RADIUS + 50
        left = min([0.0] + [position[0] - margin for position in positions])
        top = min([0.0] + [position[1] - margin for position in positions])
        right = max(
            [float(self.viewport().width())]
            + [position[0] + margin for position in positions]
        )
        bottom = max(
            [float(self.viewport().height())]
            + [position[1] + margin for position in positions]
        )
        self._scene.setSceneRect(left, top, right - left, bottom - top)