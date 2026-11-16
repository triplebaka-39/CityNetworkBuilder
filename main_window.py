import math
import random
from typing import Iterable

from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from city_canvas import CityCanvas, ToolName
from graph import Graph, Road
from prim import (
    PrimResult,
    PrimStep,
    get_eligible_roads,
    minimum_eligible_cost,
    prim_mst,
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("City Network Builder")
        self.setMinimumSize(980, 620)
        self.resize(1360, 800)
        self.graph = Graph()
        self._next_district_number = 1
        self._road_start_id: str | None = None
        self._prim_result: PrimResult | None = None
        self._prim_start_id: str | None = None
        self._prim_step_index = -1
        self._manual_mode_active = False
        self._manual_completed = False
        self._manual_disconnected = False
        self._manual_start_id: str | None = None
        self._manual_visited: set[str] = set()
        self._manual_selected_roads: list[Road] = []
        self._manual_rejected_choices: list[str] = []
        self._manual_total_cost = 0.0
        self._manual_last_explanation = ""
        self._results_restore_height: int | None = None
        self._results_expanded_height: int | None = None

        page = QWidget()
        page.setObjectName("page")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(14, 10, 14, 10)
        page_layout.setSpacing(10)

        header = QFrame()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 12, 18, 12)
        header_layout.setSpacing(12)

        title_block = QWidget()
        title_layout = QVBoxLayout(title_block)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(3)

        title = QLabel("CITY NETWORK BUILDER")
        title.setObjectName("appTitle")
        subtitle = QLabel("Plan a connected city, one road at a time.")
        subtitle.setObjectName("appSubtitle")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)

        self.reset_button = QPushButton("Reset Network")
        self.reset_button.setObjectName("dangerButton")
        self.reset_button.setToolTip("Remove every district and road.")
        self.reset_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_button.clicked.connect(self.reset_city)

        self.add_district_button = QPushButton("Add District")
        self.add_district_button.setObjectName("toolButton")
        self.add_district_button.setCheckable(True)
        self.add_district_button.setToolTip("Click an empty spot on the map to place a district.")
        self.add_district_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_district_button.clicked.connect(
            lambda: self._toggle_tool("add_district")
        )

        self.add_road_button = QPushButton("Add Road")
        self.add_road_button.setObjectName("toolButton")
        self.add_road_button.setCheckable(True)
        self.add_road_button.setToolTip("Click two districts, then enter the construction cost.")
        self.add_road_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_road_button.clicked.connect(
            lambda: self._toggle_tool("add_road")
        )

        self.delete_road_button = QPushButton("Delete Road")
        self.delete_road_button.setObjectName("dangerButton")
        self.delete_road_button.setToolTip("Delete the road currently selected on the map.")
        self.delete_road_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_road_button.clicked.connect(self.delete_selected_road)
        self.delete_road_button.setEnabled(False)

        self.delete_district_button = QPushButton("Delete District")
        self.delete_district_button.setObjectName("dangerButton")
        self.delete_district_button.setToolTip("Delete the selected district and its roads.")
        self.delete_district_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_district_button.clicked.connect(self.delete_selected_district)
        self.delete_district_button.setEnabled(False)

        self.generate_random_network_button = QPushButton(
            "Generate Random Network"
        )
        self.generate_random_network_button.setObjectName("secondaryButton")
        self.generate_random_network_button.setToolTip("Replace the map with a random connected network.")
        self.generate_random_network_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.generate_random_network_button.clicked.connect(
            self.generate_random_network
        )

        self.automatic_mode_button = QPushButton("Automatic Mode")
        self.automatic_mode_button.setObjectName("toolButton")
        self.automatic_mode_button.setCheckable(True)
        self.automatic_mode_button.setToolTip("Let Prim's Algorithm run step by step for the selected start.")
        self.automatic_mode_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.automatic_mode_button.clicked.connect(self.prepare_automatic_mode)

        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_visualization)
        self.start_button.setEnabled(False)

        self.previous_step_button = QPushButton("Previous Step")
        self.previous_step_button.setObjectName("secondaryButton")
        self.previous_step_button.clicked.connect(self.previous_prim_step)
        self.previous_step_button.setEnabled(False)

        self.next_step_button = QPushButton("Next Step")
        self.next_step_button.clicked.connect(self.next_prim_step)
        self.next_step_button.setEnabled(False)

        self.reset_visualization_button = QPushButton("Reset Visualization")
        self.reset_visualization_button.setObjectName("secondaryButton")
        self.reset_visualization_button.clicked.connect(
            self.reset_visualization
        )
        self.reset_visualization_button.setEnabled(False)

        self.manual_mode_button = QPushButton("Manual Mode")
        self.manual_mode_button.setObjectName("manualModeButton")
        self.manual_mode_button.setCheckable(True)
        self.manual_mode_button.setToolTip("Pick each road yourself; the app checks every choice.")
        self.manual_mode_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.manual_mode_button.clicked.connect(self.start_manual_mode)

        self.reset_manual_button = QPushButton("Reset Manual Mode")
        self.reset_manual_button.setObjectName("secondaryButton")
        self.reset_manual_button.clicked.connect(self.reset_manual_mode)
        self.reset_manual_button.setEnabled(False)

        header_layout.addWidget(title_block)
        header_layout.addStretch()
        page_layout.addWidget(header)

        # ---------- LEFT: city network canvas ----------
        self.canvas = CityCanvas(self.graph)
        self.canvas.districtPlacementRequested.connect(self.add_district_at)
        self.canvas.districtActivated.connect(self._handle_road_district)
        self.canvas.roadActivated.connect(self._handle_manual_road)
        self.canvas.selectionChanged.connect(self._on_canvas_selection_changed)
        self.canvas.statusMessageRequested.connect(self._show_status_message)
        self.canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # ---------- RIGHT: scrollable control + information panel ----------
        panel_content = QWidget()
        panel_content.setObjectName("panelContent")
        panel_layout = QVBoxLayout(panel_content)
        panel_layout.setContentsMargins(2, 2, 8, 2)
        panel_layout.setSpacing(6)

        def make_group(title: str, object_name: str | None = None):
            group = QGroupBox(title)
            if object_name:
                group.setObjectName(object_name)
            layout = QVBoxLayout(group)
            layout.setContentsMargins(8, 10, 8, 8)
            layout.setSpacing(6)
            return group, layout

        def hint(text: str) -> QLabel:
            label = QLabel(text)
            label.setObjectName("algorithmInfo")
            label.setWordWrap(True)
            return label

        # A. Network Builder
        builder_group, builder_layout = make_group("1 NETWORK")
        builder_layout.addWidget(
            hint("Build the city: place districts, then connect them with roads.")
        )
        tools = QWidget()
        tools.setObjectName("tools")
        tools_grid = QGridLayout(tools)
        tools_grid.setContentsMargins(0, 0, 0, 0)
        tools_grid.setSpacing(6)
        tools_grid.addWidget(self.add_district_button, 0, 0)
        tools_grid.addWidget(self.add_road_button, 0, 1)
        tools_grid.addWidget(self.delete_road_button, 1, 0)
        tools_grid.addWidget(self.delete_district_button, 1, 1)
        tools_grid.addWidget(self.generate_random_network_button, 2, 0, 1, 2)
        tools_grid.addWidget(self.reset_button, 3, 0, 1, 2)
        builder_layout.addWidget(tools)
        panel_layout.addWidget(builder_group)

        # B. Algorithm Setup
        setup_group, setup_layout = make_group("2 SETUP")
        self.start_district_label = QLabel()
        self.start_district_label.setObjectName("primResultsStart")
        self.start_district_label.setWordWrap(True)
        setup_layout.addWidget(self.start_district_label)
        setup_layout.addWidget(
            hint(
                "A minimum spanning tree (MST) connects every district using "
                "the lowest possible total road cost. Select a starting "
                "district, then choose a mode."
            )
        )
        mode_row = QWidget()
        mode_layout = QHBoxLayout(mode_row)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(6)
        mode_layout.addWidget(self.automatic_mode_button)
        mode_layout.addWidget(self.manual_mode_button)
        setup_layout.addWidget(mode_row)
        self.mode_label = QLabel()
        self.mode_label.setObjectName("phaseLabel")
        setup_layout.addWidget(self.mode_label)
        panel_layout.addWidget(setup_group)

        # C. Algorithm Controls (only the controls for the active mode)
        controls_group, controls_layout = make_group("3 RUN")
        self.automatic_controls = QWidget()
        self.automatic_controls.setObjectName("algorithmControls")
        automatic_grid = QGridLayout(self.automatic_controls)
        automatic_grid.setContentsMargins(0, 0, 0, 0)
        automatic_grid.setSpacing(6)
        automatic_grid.addWidget(self.start_button, 0, 0, 1, 2)
        automatic_grid.addWidget(self.previous_step_button, 1, 0)
        automatic_grid.addWidget(self.next_step_button, 1, 1)
        automatic_grid.addWidget(self.reset_visualization_button, 2, 0, 1, 2)
        controls_layout.addWidget(self.automatic_controls)

        self.manual_controls = QWidget()
        self.manual_controls.setObjectName("manualControls")
        manual_layout = QVBoxLayout(self.manual_controls)
        manual_layout.setContentsMargins(0, 0, 0, 0)
        manual_layout.setSpacing(6)
        manual_layout.addWidget(
            hint("Click a highlighted minimum-cost road on the map.")
        )
        manual_layout.addWidget(self.reset_manual_button)
        controls_layout.addWidget(self.manual_controls)
        panel_layout.addWidget(controls_group)

        # D. Algorithm Information
        self.algorithm_panel = QGroupBox("4 PROGRESS")
        self.algorithm_panel.setObjectName("algorithmPanel")
        explanation_layout = QVBoxLayout(self.algorithm_panel)
        explanation_layout.setContentsMargins(8, 10, 8, 8)
        explanation_layout.setSpacing(6)
        self.algorithm_info = QLabel(
            "Select a starting district, then choose Automatic or Manual Mode."
        )
        self.algorithm_info.setObjectName("algorithmInfo")
        self.algorithm_info.setWordWrap(True)
        self.algorithm_results = QListWidget()
        self.algorithm_results.setObjectName("algorithmResults")
        self.algorithm_results.setMinimumHeight(110)
        self.algorithm_results.setWordWrap(True)
        explanation_layout.addWidget(self.algorithm_info)
        explanation_layout.addWidget(self.algorithm_results)
        panel_layout.addWidget(self.algorithm_panel)

        # E. Final Results
        self.prim_results_panel = QGroupBox("5 RESULTS")
        self.prim_results_panel.setObjectName("primResultsPanel")
        results_layout = QVBoxLayout(self.prim_results_panel)
        results_layout.setContentsMargins(8, 10, 8, 8)
        results_layout.setSpacing(5)
        self.prim_results_status = QLabel()
        self.prim_results_status.setObjectName("primResultsStatus")
        self.prim_results_status.setWordWrap(True)
        self.prim_results_cost = QLabel()
        self.prim_results_cost.setObjectName("primResultsCost")
        self.prim_results_cost.setWordWrap(True)
        self.prim_results_district_count = QLabel()
        self.prim_results_district_count.setObjectName(
            "primResultsDistrictCount"
        )
        self.prim_results_road_count = QLabel()
        self.prim_results_road_count.setObjectName("primResultsRoadCount")
        self.prim_results_road_count.setWordWrap(True)
        self.prim_results_start = QLabel()
        self.prim_results_start.setObjectName("primResultsStart")
        self.prim_results_detail = QLabel()
        self.prim_results_detail.setObjectName("primResultsDetail")
        self.prim_results_detail.setWordWrap(True)
        self.prim_results_roads = QListWidget()
        self.prim_results_roads.setObjectName("primResultsRoads")
        self.prim_results_roads.setMinimumHeight(110)
        self.prim_results_roads.setWordWrap(True)
        results_layout.addWidget(self.prim_results_status)
        results_layout.addWidget(self.prim_results_cost)
        results_layout.addWidget(self.prim_results_district_count)
        results_layout.addWidget(self.prim_results_road_count)
        results_layout.addWidget(self.prim_results_start)
        results_layout.addWidget(self.prim_results_detail)
        results_layout.addWidget(self.prim_results_roads)
        panel_layout.addWidget(self.prim_results_panel)
        self.prim_results_panel.hide()
        panel_layout.addStretch()

        self.panel_scroll = QScrollArea()
        self.panel_scroll.setWidgetResizable(True)
        self.panel_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.panel_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.panel_scroll.setWidget(panel_content)
        self.panel_scroll.setMinimumWidth(340)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(12)
        body_layout.addWidget(self.canvas, stretch=68)
        body_layout.addWidget(self.panel_scroll, stretch=32)
        page_layout.addLayout(body_layout, stretch=1)

        self.setCentralWidget(page)
        self.graph.add_change_listener(self._on_graph_changed)
        self._set_algorithm_results([])
        self._update_edit_buttons()
        self._update_algorithm_controls()
        self._update_manual_controls()
        self._refresh_mode_ui()

    def add_district_at(self, position: QPointF) -> None:
        if self._manual_mode_active:
            return
        name, accepted = QInputDialog.getText(
            self,
            "Add District",
            "District name:",
        )
        if not accepted:
            return

        district_id = f"district-{self._next_district_number}"
        while any(
            district.district_id == district_id
            for district in self.graph.get_districts()
        ):
            self._next_district_number += 1
            district_id = f"district-{self._next_district_number}"

        requested_position = (position.x(), position.y())
        district_position = self.canvas.position_for_new_district(
            position,
            name,
        )
        try:
            self.graph.add_district(
                district_id,
                name,
                district_position,
            )
        except ValueError as error:
            QMessageBox.warning(self, "Unable to Add District", str(error))
            return
        self._next_district_number += 1
        if district_position != requested_position:
            self.canvas.ensure_position_visible(district_position)
            self._show_status_message(
                "Placed the district in a clear spot to keep the map readable."
            )

    def reset_city(self) -> None:
        if self._manual_mode_active:
            return
        self.canvas.clear_step_notification()
        self._road_start_id = None
        self._set_active_tool(None)
        self.canvas.clear_selection()
        self.graph.clear()

    def generate_random_network(self) -> None:
        if self._manual_mode_active:
            return
        if self.graph.get_districts():
            answer = QMessageBox.question(
                self,
                "Generate Random Network",
                "Replace the current city network with a generated one?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        rng = random.Random()
        district_count = 8
        district_ids = [
            f"random-district-{index + 1}"
            for index in range(district_count)
        ]
        rng.shuffle(district_ids)

        tree_edges: list[tuple[str, str]] = []
        for index in range(1, district_count):
            parent_id = district_ids[rng.randrange(index)]
            tree_edges.append((parent_id, district_ids[index]))
        tree_edge_keys = {
            frozenset((start_id, end_id))
            for start_id, end_id in tree_edges
        }

        possible_extra_edges = [
            (district_ids[first], district_ids[second])
            for first in range(district_count)
            for second in range(first + 1, district_count)
            if frozenset(
                (district_ids[first], district_ids[second])
            )
            not in tree_edge_keys
        ]
        rng.shuffle(possible_extra_edges)
        extra_count = rng.randint(2, min(5, len(possible_extra_edges)))
        generated_edges = tree_edges + possible_extra_edges[:extra_count]
        generated_roads = [
            (start_id, end_id, rng.randint(1, 20))
            for start_id, end_id in generated_edges
        ]

        self._road_start_id = None
        self._set_active_tool(None)
        self.reset_visualization()
        self.graph.clear()
        district_indices = {
            district_id: index
            for index, district_id in enumerate(district_ids)
        }
        position_edges = tuple(
            (district_indices[start_id], district_indices[end_id])
            for start_id, end_id in generated_edges
        )
        positions = self.canvas.distributed_positions(
            district_count,
            position_edges,
        )
        districts = [
            (
                f"random-district-{index + 1}",
                _district_name(index),
                positions[index],
            )
            for index in range(district_count)
        ]
        for district_id, name, position in districts:
            self.graph.add_district(district_id, name, position)
        for start_id, end_id, cost in generated_roads:
            self.graph.add_road(start_id, end_id, cost)

        self.algorithm_info.setText(
            f"Generated a connected network with {district_count} districts "
            f"and {len(generated_roads)} roads. Select a starting district "
            "to use Automatic or Manual Mode."
        )
        self._set_algorithm_results([])
        self._update_edit_buttons()
        self._update_algorithm_controls()
        self._update_manual_controls()
        self._show_status_message(
            f"Generated {district_count} districts and "
            f"{len(generated_roads)} roads."
        )

    def prepare_automatic_mode(self) -> None:
        if self._manual_mode_active:
            self.automatic_mode_button.setChecked(False)
            return
        start_id = self.canvas.selected_district_id
        if start_id is None:
            self.automatic_mode_button.setChecked(False)
            self._show_error(
                "Starting District Required",
                "Select a starting district on the map first.",
            )
            return

        self._hide_prim_results()
        try:
            result = prim_mst(self.graph, start_id)
        except ValueError as error:
            self.automatic_mode_button.setChecked(False)
            self._show_error("Unable to Start Prim's Algorithm", str(error))
            return

        self._prim_result = result
        self._prim_start_id = start_id
        self._prim_step_index = -1
        self.canvas.set_prim_step(None)
        self._set_algorithm_results([])
        self.automatic_mode_button.setChecked(True)
        if result.is_spanning_tree:
            self.algorithm_info.setText(
                f"Ready to start at "
                f"{self.graph.get_district(start_id).name}. "
                "We'll add the lowest-cost roads needed to reach every "
                "district."
            )
        else:
            not_reached = ", ".join(
                self.graph.get_district(district_id).name
                for district_id in result.unreached_districts
            )
            self.algorithm_info.setText(
                "Some districts cannot be reached from "
                f"{self.graph.get_district(start_id).name}, so the whole "
                "network cannot be connected. Not connected: "
                f"{not_reached}."
            )
        self._update_algorithm_controls()

    def start_visualization(self) -> None:
        if self._prim_result is None or not self._prim_result.steps:
            self._show_status_message(
                "Choose Automatic Mode with a selected starting district first."
            )
            return
        self._show_prim_step(0)

    def next_prim_step(self) -> None:
        if (
            self._prim_result is None
            or self._prim_step_index + 1 >= len(self._prim_result.steps)
        ):
            return
        self._show_prim_step(self._prim_step_index + 1)

    def previous_prim_step(self) -> None:
        if self._prim_result is None or self._prim_step_index <= 0:
            return
        self._show_prim_step(self._prim_step_index - 1)

    def reset_visualization(self) -> None:
        if self._manual_mode_active:
            return
        self.canvas.clear_step_notification()
        self._hide_prim_results()
        self._prim_result = None
        self._prim_start_id = None
        self._prim_step_index = -1
        self.automatic_mode_button.setChecked(False)
        self.canvas.set_prim_step(None)
        self.canvas.clear_selection()
        self.algorithm_info.setText(
            "Visualization reset; the city network is unchanged. "
            "Select a starting district, then choose Automatic Mode."
        )
        self._set_algorithm_results([])
        self._update_algorithm_controls()

    def start_manual_mode(self) -> None:
        if self._manual_mode_active:
            self.manual_mode_button.setChecked(True)
            return
        start_id = self.canvas.selected_district_id
        if start_id is None:
            self.manual_mode_button.setChecked(False)
            self._show_error(
                "Starting District Required",
                "Select a starting district on the map first.",
            )
            return

        if self._prim_result is not None:
            self.reset_visualization()

        self._manual_mode_active = True
        self._manual_completed = False
        self._manual_disconnected = False
        self._manual_start_id = start_id
        self._manual_visited = {start_id}
        self._manual_selected_roads = []
        self._manual_rejected_choices = []
        self._manual_total_cost = 0.0
        start_name = self.graph.get_district(start_id).name
        self._manual_last_explanation = (
            f"We start at {start_name}; it is the first district in our "
            "network. Total cost: 0."
        )
        self._hide_prim_results()
        self.manual_mode_button.setChecked(True)
        self._update_manual_display()
        self._update_edit_buttons()
        self._update_algorithm_controls()
        self._update_manual_controls()
        if self._manual_completed:
            notification = (
                f"We start at {start_name}; the network is already connected."
            )
        elif self._manual_disconnected:
            notification = (
                "No road reaches the other districts, so the network is incomplete."
            )
        else:
            notification = f"We start at {start_name}."
        self.canvas.show_step_notification(notification)

    def reset_manual_mode(self) -> None:
        if not self._manual_mode_active:
            return
        self._reset_manual_state(
            "Manual Mode reset; the city network is unchanged. "
            "Select a starting district to begin again."
        )

    def _reset_manual_state(self, message: str) -> None:
        self._manual_mode_active = False
        self._manual_completed = False
        self._manual_disconnected = False
        self._manual_start_id = None
        self._manual_visited.clear()
        self._manual_selected_roads.clear()
        self._manual_rejected_choices.clear()
        self._manual_total_cost = 0.0
        self._manual_last_explanation = ""
        self.canvas.clear_step_notification()
        self._hide_prim_results()
        self.manual_mode_button.setChecked(False)
        self.canvas.set_manual_state(False)
        self.canvas.clear_selection()
        self.algorithm_info.setText(message)
        self._set_algorithm_results([])
        self._update_edit_buttons()
        self._update_algorithm_controls()
        self._update_manual_controls()

    def _handle_manual_road(self, start_id: str, end_id: str) -> None:
        if not self._manual_mode_active:
            return
        try:
            road = self.graph.get_road(start_id, end_id)
        except ValueError as error:
            self._show_manual_rejection(
                f"That road is no longer available: {error}"
            )
            return

        if self._manual_completed:
            self._show_manual_rejection(
                "Every district is connected. Reset Manual Mode to start over.",
                road,
            )
            return
        if self._manual_disconnected:
            self._show_manual_rejection(
                "This network has districts no road can reach, so it cannot "
                "be fully connected.",
                road,
            )
            return

        visited_start = start_id in self._manual_visited
        visited_end = end_id in self._manual_visited
        if visited_start and visited_end:
            self._show_manual_rejection(
                f"{self._format_road(road)} joins two districts already in "
                "our network, so it would make a loop.",
                road,
            )
            return
        if not visited_start and not visited_end:
            self._show_manual_rejection(
                f"{self._format_road(road)} does not reach our network yet. "
                "Choose a road with one end in the network and one end at a "
                "new district.",
                road,
            )
            return

        eligible_roads = get_eligible_roads(
            self.graph,
            self._manual_visited,
        )
        eligible_keys = {
            frozenset((item.start_id, item.end_id))
            for item in eligible_roads
        }
        if frozenset((start_id, end_id)) not in eligible_keys:
            self._show_manual_rejection(
                f"{self._format_road(road)} does not connect our network to "
                "a new district.",
                road,
            )
            return

        minimum_cost = minimum_eligible_cost(eligible_roads)
        if minimum_cost is None:
            self._show_manual_rejection(
                f"No road can extend our network using "
                f"{self._format_road(road)}.",
                road,
            )
            return
        if road.cost > minimum_cost:
            minimum_roads = [
                candidate
                for candidate in eligible_roads
                if candidate.cost == minimum_cost
            ]
            alternatives = ", ".join(
                self._format_road(candidate) for candidate in minimum_roads
            )
            self._show_manual_rejection(
                f"{self._format_road(road)} costs more than the lowest-cost "
                f"choice. Choose {alternatives} first.",
                road,
            )
            return

        new_district_id = end_id if visited_start else start_id
        connected_name = self.graph.get_district(
            start_id if visited_start else end_id
        ).name
        new_name = self.graph.get_district(new_district_id).name
        minimum_count = sum(
            candidate.cost == minimum_cost for candidate in eligible_roads
        )
        minimum_explanation = (
            f"ties for the lowest cost ({minimum_cost:g})"
            if minimum_count > 1
            else f"has the lowest cost ({minimum_cost:g})"
        )
        previous_total = self._manual_total_cost
        self._manual_selected_roads.append(road)
        self._manual_total_cost += road.cost
        self._manual_visited.add(new_district_id)
        self._manual_last_explanation = (
            f"Choose {self._format_road(road)} because it "
            f"{minimum_explanation}. It connects our network at "
            f"{connected_name} to new district {new_name} without making a "
            f"loop. Total cost rises from {previous_total:g} to "
            f"{self._manual_total_cost:g}."
        )
        self._update_manual_display()
        if self._manual_completed:
            notification = (
                f"We chose {self._format_road(road)} to reach {new_name}; "
                "every district is now connected."
            )
        elif self._manual_disconnected:
            unreached = next(
                district.name
                for district in self.graph.get_districts()
                if district.district_id not in self._manual_visited
            )
            notification = (
                f"We chose {self._format_road(road)} to reach {new_name}, "
                f"but {unreached} cannot be reached."
            )
        else:
            notification = (
                f"We chose {self._format_road(road)} to reach {new_name}."
            )
        self.canvas.show_step_notification(notification)

    def _update_manual_display(self) -> None:
        eligible_roads = get_eligible_roads(
            self.graph,
            self._manual_visited,
        )
        self.canvas.set_manual_state(
            True,
            self._manual_visited,
            eligible_roads,
            self._manual_selected_roads,
        )
        self._set_algorithm_results(self._manual_result_entries())
        district_count = len(self.graph.get_districts())
        if (
            len(self._manual_visited) == district_count
            and len(self._manual_selected_roads) == district_count - 1
        ):
            if not self._show_complete_mst_results(
                self._manual_selected_roads,
                self._manual_total_cost,
                self._manual_start_id,
            ):
                self.algorithm_info.setText(
                    "The selected roads did not pass the final MST checks. "
                    "Reset Manual Mode and try again."
                )
                return
            self._manual_completed = True
            self.algorithm_info.setText(
                f"{self._manual_last_explanation} "
                f"All {district_count} districts are now connected with "
                f"{district_count - 1} roads. Final total cost: "
                f"{self._manual_total_cost:g}."
            )
            return

        if not eligible_roads and len(self._manual_visited) < district_count:
            self._manual_disconnected = True
            not_reached_ids = tuple(
                district.district_id
                for district in self.graph.get_districts()
                if district.district_id not in self._manual_visited
            )
            not_reached = ", ".join(
                self.graph.get_district(district_id).name
                for district_id in not_reached_ids
            )
            self._show_incomplete_mst_results(
                self._manual_selected_roads,
                self._manual_start_id,
                not_reached_ids,
            )
            self.algorithm_info.setText(
                f"{self._manual_last_explanation} "
                "No road reaches the remaining districts, so we cannot "
                "connect everyone. Still outside the network: "
                f"{not_reached}. Total so far: "
                f"{self._manual_total_cost:g} (incomplete)."
            )
            return

        if not self._manual_last_explanation:
            return
        self.algorithm_info.setText(
            f"Manual Mode: {self._manual_last_explanation} "
            "Next, choose a highlighted road with the lowest cost that "
            "reaches a new district."
        )

    def _show_manual_rejection(
        self,
        message: str,
        road: Road | None = None,
    ) -> None:
        if road is not None:
            self._manual_rejected_choices.append(
                f"Rejected: {self._format_road(road)}"
            )
        self._set_algorithm_results(self._manual_result_entries())
        self.algorithm_info.setText(
            f"Manual Mode: {message} "
            f"Total cost stays at {self._manual_total_cost:g}."
        )
        self._show_status_message(message)
        self.canvas.show_step_notification(
            self._manual_rejection_notification(message, road)
        )

    def _manual_rejection_notification(
        self,
        message: str,
        road: Road | None,
    ) -> str:
        if road is None:
            return "That road is no longer available."
        road_text = self._format_road(road)
        if "would make a loop" in message:
            reason = "it would make a loop"
        elif "costs more than the lowest-cost choice" in message:
            reason = "a cheaper road must go first"
        elif (
            "does not reach our network" in message
            or "does not connect our network" in message
        ):
            reason = "it does not reach a new district"
        elif "cannot be fully connected" in message:
            reason = "some districts cannot be reached"
        elif "already connected" in message:
            reason = "all districts are already connected"
        else:
            reason = "it cannot be chosen right now"
        return f"We skipped {road_text} because {reason}."

    def _format_road(self, road: Road) -> str:
        start = self.graph.get_district(road.start_id).name
        end = self.graph.get_district(road.end_id).name
        return f"{start} - {end} (cost {road.cost:g})"

    def _hide_prim_results(self) -> None:
        self.prim_results_panel.hide()
        self.prim_results_roads.clear()

    def _present_prim_results(self) -> None:
        self.prim_results_panel.show()
        self.panel_scroll.widget().layout().activate()
        self.panel_scroll.ensureWidgetVisible(self.prim_results_panel)

    def _show_complete_mst_results(
        self,
        roads: Iterable[Road],
        total_cost: float | None,
        start_id: str | None,
    ) -> bool:
        selected_roads = tuple(roads)
        districts = self.graph.get_districts()
        district_names = {
            district.district_id: district.name for district in districts
        }
        district_count = len(districts)
        start_name = district_names.get(start_id)
        expected_road_count = district_count - 1
        actual_cost = sum((road.cost for road in selected_roads), 0.0)

        failure_reason = None
        if start_name is None:
            failure_reason = "The starting district is unavailable."
        elif district_count == 0:
            failure_reason = "The network has no districts."
        elif len(selected_roads) != expected_road_count:
            failure_reason = (
                f"Expected {expected_road_count} selected roads for "
                f"{district_count} districts, but received "
                f"{len(selected_roads)}."
            )
        elif total_cost is None:
            failure_reason = "The algorithm did not provide a complete MST cost."
        elif not math.isclose(actual_cost, total_cost):
            failure_reason = (
                "The selected-road costs do not match the algorithm's total."
            )

        self.prim_results_district_count.setText(
            f"Districts: {district_count}"
        )
        self.prim_results_start.setText(
            f"Starting district: {start_name or 'Unavailable'}"
        )
        self.prim_results_road_count.setText(
            f"Selected roads: {len(selected_roads)}"
        )
        self.prim_results_roads.clear()
        if failure_reason is not None:
            self.prim_results_status.setText(
                "MST Completion Could Not Be Verified"
            )
            self.prim_results_cost.setText(
                "Total MST construction cost: Unavailable"
            )
            self.prim_results_detail.setText(
                f"{failure_reason} No result is reported as a completed MST."
            )
            self.prim_results_roads.addItem(
                "No complete MST road list is available."
            )
            self._present_prim_results()
            return False

        self.prim_results_status.setText("MST Completed")
        self.prim_results_cost.setText(
            f"Total MST construction cost: {total_cost:g}"
        )
        self.prim_results_detail.setText(
            f"Verified: {len(selected_roads)} roads connect all "
            f"{district_count} districts (one fewer road than districts)."
        )
        for index, road in enumerate(selected_roads, start=1):
            start = district_names.get(road.start_id, road.start_id)
            end = district_names.get(road.end_id, road.end_id)
            self.prim_results_roads.addItem(
                f"{index}. {start} - {end} (cost {road.cost:g})"
            )
        if not selected_roads:
            self.prim_results_roads.addItem(
                "No roads are required for a one-district network."
            )
        self._present_prim_results()
        return True

    def _show_incomplete_mst_results(
        self,
        roads_selected_so_far: Iterable[Road],
        start_id: str | None,
        unreached_ids: Iterable[str],
    ) -> None:
        districts = self.graph.get_districts()
        district_names = {
            district.district_id: district.name for district in districts
        }
        start_name = district_names.get(start_id, "Unavailable")
        unreached_names = [
            district_names.get(district_id, district_id)
            for district_id in unreached_ids
        ]
        unreached = ", ".join(unreached_names) or "unknown"

        self.prim_results_status.setText(
            "Complete MST Could Not Be Created"
        )
        self.prim_results_cost.setText(
            "Total MST construction cost: Unavailable"
        )
        self.prim_results_district_count.setText(
            f"Districts: {len(districts)}"
        )
        self.prim_results_road_count.setText(
            f"Selected so far: {len(tuple(roads_selected_so_far))} "
            "(partial; not an MST)"
        )
        self.prim_results_start.setText(
            f"Starting district: {start_name}"
        )
        self.prim_results_detail.setText(
            f"These districts cannot be reached from {start_name}: "
            f"{unreached}. Not every district can be connected."
        )
        self.prim_results_roads.clear()
        self.prim_results_roads.addItem(
            "No complete MST road list is available for this network."
        )
        self._present_prim_results()

    def _set_algorithm_results(self, entries: list[str]) -> None:
        self.algorithm_results.clear()
        self.algorithm_results.addItems(
            entries if entries else ["No roads selected or rejected yet."]
        )

    def _manual_result_entries(self) -> list[str]:
        selected = [
            f"Selected: {self._format_road(road)}"
            for road in self._manual_selected_roads
        ]
        return selected + self._manual_rejected_choices

    def _automatic_result_entries(self, index: int) -> list[str]:
        if self._prim_result is None:
            return []
        entries: list[str] = []
        for step in self._prim_result.steps[: index + 1]:
            if step.selected_road is not None:
                entries.append(
                    f"Selected: {self._format_road(step.selected_road)}"
                )
            for rejected in step.rejected_roads:
                reason = self._simple_rejection_reason(
                    rejected.road,
                    rejected.reason,
                )
                entries.append(
                    f"Rejected: {self._format_road(rejected.road)} - {reason}"
                )
        return entries

    def _show_prim_step(self, index: int) -> None:
        result = self._prim_result
        if result is None:
            return
        self._prim_step_index = index
        step = result.steps[index]
        self.canvas.set_prim_step(step)
        self._set_algorithm_results(self._automatic_result_entries(index))
        step_count = len(result.steps)
        description = self._describe_prim_step(step)
        if step.selected_road is not None:
            previous_total = step.total_cost - step.selected_road.cost
            cost_text = (
                f"Total construction cost: {step.total_cost:g} "
                f"(up from {previous_total:g} after adding this road)."
            )
        elif step.action == "reject":
            cost_text = (
                f"Total cost stays at {step.total_cost:g}; no road was added."
            )
        else:
            cost_text = f"Total construction cost so far: {step.total_cost:g}."

        completion = ""
        if index == step_count - 1:
            if result.is_spanning_tree:
                if self._show_complete_mst_results(
                    result.selected_roads,
                    result.total_cost,
                    result.start_id,
                ):
                    completion = (
                        "\nEvery district is connected at the lowest "
                        "possible total road cost. Final total: "
                        f"{result.total_cost:g}."
                    )
                else:
                    completion = (
                        "\nWe could not verify a complete network, so no "
                        "final result is shown."
                    )
            else:
                not_reached = ", ".join(
                    self.graph.get_district(district_id).name
                    for district_id in result.unreached_districts
                )
                self._show_incomplete_mst_results(
                    result.selected_roads,
                    result.start_id,
                    result.unreached_districts,
                )
                completion = (
                    "\nNo road reaches the remaining districts, so we "
                    "cannot connect everyone. Not connected yet: "
                    f"{not_reached}."
                )
        else:
            self._hide_prim_results()

        self.algorithm_info.setText(
            f"Step {step.step_number + 1} of {step_count}: {description}\n"
            f"{cost_text}{completion}"
        )
        self.canvas.show_step_notification(
            self._prim_step_notification(step, result, index)
        )
        self._update_algorithm_controls()

    def _prim_step_notification(
        self,
        step: PrimStep,
        result: PrimResult,
        index: int,
    ) -> str:
        last_step = index == len(result.steps) - 1
        if step.action == "start":
            start_name = self.graph.get_district(step.visited_after[0]).name
            if not step.eligible_roads and len(self.graph.get_districts()) > 1:
                return (
                    f"We start at {start_name}, but no road reaches a new district."
                )
            if len(self.graph.get_districts()) == 1:
                return (
                    f"We start at {start_name}; the network is already connected."
                )
            return f"We start at {start_name}."

        if step.action == "select" and step.selected_road is not None:
            road = step.selected_road
            new_district_id = next(
                (
                    district_id
                    for district_id in step.visited_after
                    if district_id not in step.visited_before
                ),
                None,
            )
            new_name = (
                self.graph.get_district(new_district_id).name
                if new_district_id is not None
                else "a new district"
            )
            road_text = self._format_road(road)
            if last_step and not result.is_spanning_tree:
                unreached = self.graph.get_district(
                    result.unreached_districts[0]
                ).name
                return (
                    f"We chose {road_text} to reach {new_name}, but "
                    f"{unreached} cannot be reached."
                )
            if last_step:
                return (
                    f"We chose {road_text} to reach {new_name}; "
                    "every district is now connected."
                )
            return f"We chose {road_text} to reach {new_name}."

        if step.action == "reject" and step.rejected_roads:
            rejected = step.rejected_roads[0]
            road_text = self._format_road(rejected.road)
            if "cycle" in rejected.reason.lower():
                reason = "it would make a loop"
            else:
                reason = "it does not reach a new district"
            if last_step and result.unreached_districts:
                unreached = self.graph.get_district(
                    result.unreached_districts[0]
                ).name
                return (
                    f"We skipped {road_text} because {reason}, and "
                    f"{unreached} cannot be reached."
                )
            if last_step and result.is_spanning_tree:
                return (
                    f"We skipped {road_text} because {reason}; "
                    "every district is already connected."
                )
            return f"We skipped {road_text} because {reason}."

        return "No road was added in this step."

    def _describe_prim_step(self, step: PrimStep) -> str:
        if step.action == "start":
            start_name = self.graph.get_district(step.visited_after[0]).name
            if not step.eligible_roads:
                return (
                    f"We start at {start_name}; it is the first district in "
                    "our network. No road from it reaches another district."
                )
            minimum_cost = minimum_eligible_cost(step.eligible_roads)
            if minimum_cost is None:
                return f"We start at {start_name}. No road reaches a new district."
            minimum_roads = [
                road
                for road in step.eligible_roads
                if road.cost == minimum_cost
            ]
            cheapest = ", ".join(
                self._format_road(road) for road in minimum_roads
            )
            return (
                f"We start at {start_name}; it is our first district. "
                "A next road must reach a district not yet connected. "
                f"Cheapest option(s): {cheapest}."
            )

        if step.action == "select" and step.selected_road is not None:
            selected = step.selected_road
            minimum_cost = minimum_eligible_cost(step.eligible_roads)
            if minimum_cost is None:
                return (
                    f"We chose {self._format_road(selected)}, but no "
                    "available road was recorded for this step."
                )
            newly_visited = next(
                district_id
                for district_id in step.visited_after
                if district_id not in step.visited_before
            )
            selected_visited_id = next(
                district_id
                for district_id in (selected.start_id, selected.end_id)
                if district_id in step.visited_before
            )
            visited_name = self.graph.get_district(selected_visited_id).name
            unvisited_name = self.graph.get_district(newly_visited).name
            tie_count = sum(
                road.cost == minimum_cost
                for road in step.eligible_roads
            )
            minimum_reason = (
                "ties for the lowest cost"
                if tie_count > 1
                else "has the lowest cost"
            )
            explanation = (
                f"Choose {self._format_road(selected)} because it "
                f"{minimum_reason} ({minimum_cost:g}). It connects our "
                f"network at {visited_name} to new district {unvisited_name} "
                "without making a loop."
            )
            if step.rejected_roads:
                rejected = "; ".join(
                    f"We skipped {self._format_road(item.road)} because "
                    f"{self._simple_rejection_reason(item.road, item.reason)}"
                    for item in step.rejected_roads
                )
                explanation += f" {rejected}."
            return explanation

        if step.action == "reject":
            return "; ".join(
                f"We skipped {self._format_road(item.road)} because "
                f"{self._simple_rejection_reason(item.road, item.reason)}."
                for item in step.rejected_roads
            )
        return "No road was added in this step."

    def _simple_rejection_reason(self, road: Road, reason: str) -> str:
        if "cycle" not in reason.lower():
            return reason
        start = self.graph.get_district(road.start_id).name
        end = self.graph.get_district(road.end_id).name
        return (
            f"{start} and {end} are already connected, so this road would "
            "make a loop"
        )

    def _on_canvas_selection_changed(self) -> None:
        self._update_edit_buttons()
        self._update_algorithm_controls()
        self._update_manual_controls()
        if (
            self._prim_result is not None
            and self.canvas.selected_district_id != self._prim_start_id
        ):
            self._invalidate_algorithm_run(
                "Starting district changed; the previous algorithm run was "
                "cleared. Choose Automatic Mode to calculate a new run."
            )

    def _on_graph_changed(self) -> None:
        if self._manual_mode_active:
            self._reset_manual_state(
                "The city network changed, so Manual Mode was reset."
            )
        if self._prim_result is not None:
            self._invalidate_algorithm_run(
                "The city network changed; the previous algorithm run was "
                "cleared. Choose a starting district and run Automatic Mode again."
            )

    def _invalidate_algorithm_run(self, message: str) -> None:
        self.canvas.clear_step_notification()
        self._hide_prim_results()
        self._prim_result = None
        self._prim_start_id = None
        self._prim_step_index = -1
        self.automatic_mode_button.setChecked(False)
        self.canvas.set_prim_step(None)
        self.algorithm_info.setText(message)
        self._set_algorithm_results([])
        self._update_algorithm_controls()
        self._update_manual_controls()

    def _update_algorithm_controls(self) -> None:
        self._refresh_mode_ui()
        has_history = (
            self._prim_result is not None
            and bool(self._prim_result.steps)
        )
        self.automatic_mode_button.setEnabled(
            not self._manual_mode_active
            and self.canvas.selected_district_id is not None
        )
        self.start_button.setEnabled(has_history and not self._manual_mode_active)
        self.previous_step_button.setEnabled(
            self._prim_step_index > 0 and not self._manual_mode_active
        )
        self.next_step_button.setEnabled(
            has_history
            and not self._manual_mode_active
            and self._prim_step_index >= 0
            and self._prim_result is not None
            and self._prim_step_index < len(self._prim_result.steps) - 1
        )
        self.reset_visualization_button.setEnabled(
            not self._manual_mode_active
            and (
                self._prim_result is not None
                or self.canvas.prim_step is not None
            )
        )

    def delete_selected_road(self) -> None:
        if self._manual_mode_active:
            return
        road_key = self.canvas.selected_road
        if road_key is None:
            return
        try:
            self.graph.delete_road(*road_key)
        except ValueError as error:
            self._show_error("Unable to Delete Road", str(error))

    def delete_selected_district(self) -> None:
        if self._manual_mode_active:
            return
        district_id = self.canvas.selected_district_id
        if district_id is None:
            return
        district = self.graph.get_district(district_id)
        answer = QMessageBox.question(
            self,
            "Delete District",
            (
                f"Delete {district.name}? "
                "Its connected roads will also be removed."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.graph.delete_district(district_id)
        except ValueError as error:
            self._show_error("Unable to Delete District", str(error))

    def _toggle_tool(self, tool: ToolName) -> None:
        if self._manual_mode_active:
            return
        self._road_start_id = None
        self._set_active_tool(
            None if self.canvas.active_tool == tool else tool
        )

    def _set_active_tool(self, tool: ToolName | None) -> None:
        self._road_start_id = None
        self.canvas.set_active_tool(tool)
        self.add_district_button.setChecked(tool == "add_district")
        self.add_road_button.setChecked(tool == "add_road")
        if tool == "add_district":
            self._show_status_message("Click an empty spot to place a district.")
        elif tool == "add_road":
            self._show_status_message(
                "Select two districts to create a road."
            )
        else:
            self.statusBar().clearMessage()
        self._update_edit_buttons()

    def _handle_road_district(self, district_id: str) -> None:
        if self._road_start_id is None:
            self._road_start_id = district_id
            self.canvas.set_road_start_district(district_id)
            district = self.graph.get_district(district_id)
            self._show_status_message(
                f"{district.name} selected. Choose a second district."
            )
            return

        start_id = self._road_start_id
        if district_id == start_id:
            self._show_error(
                "Cannot Create Road",
                "A road must connect two different districts.",
            )
            return
        if district_id in self.graph.get_neighbors(start_id):
            self._show_error(
                "Cannot Create Road",
                "A road already connects these districts.",
            )
            return

        cost_text, accepted = QInputDialog.getText(
            self,
            "Add Road",
            "Construction cost (non-negative number):",
        )
        if not accepted:
            self._clear_pending_road()
            return
        if not cost_text.strip():
            self._show_error("Unable to Add Road", "Enter a construction cost.")
            self._clear_pending_road()
            return
        try:
            cost = float(cost_text)
        except ValueError:
            self._show_error(
                "Unable to Add Road",
                "Enter a valid numeric construction cost.",
            )
            self._clear_pending_road()
            return
        try:
            self.graph.add_road(start_id, district_id, cost)
        except ValueError as error:
            self._show_error("Unable to Add Road", str(error))
            self._clear_pending_road()
            return

        self._clear_pending_road()
        if self.canvas.active_tool == "add_road":
            self._show_status_message(
                "Road added. Select two districts for another road."
            )

    def _clear_pending_road(self) -> None:
        self._road_start_id = None
        self.canvas.set_road_start_district(None)
        self.canvas.clear_selection()

    def _update_edit_buttons(self) -> None:
        can_edit = (
            self.canvas.active_tool is None and not self._manual_mode_active
        )
        self.add_district_button.setEnabled(not self._manual_mode_active)
        self.add_road_button.setEnabled(not self._manual_mode_active)
        self.generate_random_network_button.setEnabled(
            not self._manual_mode_active
        )
        self.delete_road_button.setEnabled(
            can_edit and self.canvas.selected_road is not None
        )
        self.delete_district_button.setEnabled(
            can_edit and self.canvas.selected_district_id is not None
        )
        self.reset_button.setEnabled(not self._manual_mode_active)

    def _update_manual_controls(self) -> None:
        can_start = (
            self.canvas.selected_district_id is not None
            and self.canvas.active_tool is None
        )
        self.manual_mode_button.setEnabled(
            self._manual_mode_active or can_start
        )
        self.manual_mode_button.setChecked(self._manual_mode_active)
        self.reset_manual_button.setEnabled(self._manual_mode_active)
        self._refresh_mode_ui()

    def _refresh_mode_ui(self) -> None:
        if not hasattr(self, "mode_label"):
            return
        if self._manual_mode_active:
            mode = "ACTIVE MODE: MANUAL"
        elif self._prim_result is not None:
            mode = "ACTIVE MODE: AUTOMATIC"
        else:
            mode = "ACTIVE MODE: NONE YET"
        self.mode_label.setText(mode)
        self.automatic_controls.setVisible(not self._manual_mode_active)
        self.manual_controls.setVisible(self._manual_mode_active)
        district_id = self.canvas.selected_district_id
        name = None
        if district_id is not None:
            try:
                name = self.graph.get_district(district_id).name
            except ValueError:
                name = None
        self.start_district_label.setText(
            f"Starting district: {name}" if name else "Starting district: none selected"
        )

    def _show_status_message(self, message: str) -> None:
        self.statusBar().showMessage(message, 4000)

    def _show_error(self, title: str, message: str) -> None:
        QMessageBox.warning(self, title, message)


def _district_name(index: int) -> str:
    suffix = ""
    while True:
        index, remainder = divmod(index, 26)
        suffix = chr(ord("A") + remainder) + suffix
        if index == 0:
            break
        index -= 1
    return f"District {suffix}"