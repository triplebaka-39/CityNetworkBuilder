from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real
from typing import Callable, TypeAlias


Position: TypeAlias = tuple[float, float]
AdjacencyList: TypeAlias = dict[str, dict[str, float]]


@dataclass(frozen=True)
class District:
    district_id: str
    name: str
    position: Position | None = None


@dataclass(frozen=True)
class Road:
    start_id: str
    end_id: str
    cost: float


@dataclass(frozen=True)
class GraphState:
    districts: tuple[District, ...]
    roads: tuple[Road, ...]
    adjacency: AdjacencyList


class Graph:
    """Mutable weighted undirected graph of city districts and roads."""

    def __init__(self) -> None:
        self._districts: dict[str, District] = {}
        self._adjacency: dict[str, dict[str, Road]] = {}
        self._change_listeners: list[Callable[[], None]] = []

    def add_change_listener(self, listener: Callable[[], None]) -> None:
        if listener not in self._change_listeners:
            self._change_listeners.append(listener)

    def remove_change_listener(self, listener: Callable[[], None]) -> None:
        if listener in self._change_listeners:
            self._change_listeners.remove(listener)

    def clear(self) -> None:
        if not self._districts:
            return
        self._districts.clear()
        self._adjacency.clear()
        self._notify_changed()

    def add_district(
        self,
        district_id: str,
        name: str,
        position: Position | None = None,
    ) -> District:
        district_id = self._validate_text(district_id, "District ID")
        name = self._validate_text(name, "District name")
        if district_id in self._districts:
            raise ValueError(f"District ID {district_id!r} already exists.")

        validated_position = self._validate_position(position)
        district = District(district_id, name, validated_position)
        self._districts[district_id] = district
        self._adjacency[district_id] = {}
        self._notify_changed()
        return district

    def delete_district(self, district_id: str) -> District:
        self._require_district(district_id)
        district = self._districts.pop(district_id)
        for neighbor_id in tuple(self._adjacency[district_id]):
            del self._adjacency[neighbor_id][district_id]
        del self._adjacency[district_id]
        self._notify_changed()
        return district

    def set_district_position(self, district_id: str, position: Position) -> District:
        self._require_district(district_id)
        validated_position = self._validate_position(position)
        if validated_position is None:
            raise ValueError("Position must be a pair of finite coordinates.")
        district = self._districts[district_id]
        if district.position == validated_position:
            return district
        updated_district = District(
            district.district_id,
            district.name,
            validated_position,
        )
        self._districts[district_id] = updated_district
        self._notify_changed()
        return updated_district

    def add_road(self, start_id: str, end_id: str, cost: Real) -> Road:
        self._require_district(start_id)
        self._require_district(end_id)
        if start_id == end_id:
            raise ValueError("A road must connect two different districts.")
        validated_cost = self._validate_cost(cost)
        if end_id in self._adjacency[start_id]:
            raise ValueError(
                f"A road between {start_id!r} and {end_id!r} already exists."
            )

        road = Road(start_id, end_id, validated_cost)
        self._adjacency[start_id][end_id] = road
        self._adjacency[end_id][start_id] = road
        self._notify_changed()
        return road

    def delete_road(self, start_id: str, end_id: str) -> Road:
        self._require_district(start_id)
        self._require_district(end_id)
        road = self._adjacency[start_id].get(end_id)
        if road is None:
            raise ValueError(
                f"No road exists between {start_id!r} and {end_id!r}."
            )
        del self._adjacency[start_id][end_id]
        del self._adjacency[end_id][start_id]
        self._notify_changed()
        return road

    def get_district(self, district_id: str) -> District:
        self._require_district(district_id)
        return self._districts[district_id]

    def get_districts(self) -> tuple[District, ...]:
        return tuple(self._districts.values())

    def get_road(self, start_id: str, end_id: str) -> Road:
        self._require_district(start_id)
        self._require_district(end_id)
        road = self._adjacency[start_id].get(end_id)
        if road is None:
            raise ValueError(
                f"No road exists between {start_id!r} and {end_id!r}."
            )
        return road

    def get_roads(self) -> tuple[Road, ...]:
        roads: list[Road] = []
        seen: set[frozenset[str]] = set()
        for start_id, neighbors in self._adjacency.items():
            for end_id, road in neighbors.items():
                key = frozenset((start_id, end_id))
                if key not in seen:
                    roads.append(road)
                    seen.add(key)
        return tuple(roads)

    def get_neighbors(self, district_id: str) -> dict[str, Road]:
        """Return neighboring district IDs mapped to their shared road."""
        self._require_district(district_id)
        return self._adjacency[district_id].copy()

    def get_adjacency_list(self) -> AdjacencyList:
        """Return a detached district-to-neighbor-to-cost adjacency list."""
        return {
            district_id: {
                neighbor_id: road.cost for neighbor_id, road in neighbors.items()
            }
            for district_id, neighbors in self._adjacency.items()
        }

    def get_state(self) -> GraphState:
        """Return a detached snapshot of all districts, roads, and costs."""
        return GraphState(
            districts=self.get_districts(),
            roads=self.get_roads(),
            adjacency=self.get_adjacency_list(),
        )

    def _require_district(self, district_id: str) -> None:
        if not isinstance(district_id, str) or not district_id.strip():
            raise ValueError("District ID must be a non-empty string.")
        if district_id not in self._districts:
            raise ValueError(f"District ID {district_id!r} does not exist.")

    def _notify_changed(self) -> None:
        for listener in tuple(self._change_listeners):
            listener()

    @staticmethod
    def _validate_text(value: str, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} must be a non-empty string.")
        return value.strip()

    @staticmethod
    def _validate_position(position: Position | None) -> Position | None:
        if position is None:
            return None
        if not isinstance(position, tuple) or len(position) != 2:
            raise ValueError("Position must be a pair of finite coordinates.")
        coordinates = position
        if any(isinstance(value, bool) or not isinstance(value, Real) for value in coordinates):
            raise ValueError("Position must be a pair of finite coordinates.")
        try:
            x, y = float(coordinates[0]), float(coordinates[1])
        except OverflowError as error:
            raise ValueError("Position must be a pair of finite coordinates.") from error
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("Position must be a pair of finite coordinates.")
        return x, y

    @staticmethod
    def _validate_cost(cost: Real) -> float:
        if isinstance(cost, bool) or not isinstance(cost, Real):
            raise ValueError(
                "Road cost must be a finite number greater than or equal to zero."
            )
        try:
            validated_cost = float(cost)
        except OverflowError as error:
            raise ValueError(
                "Road cost must be a finite number greater than or equal to zero."
            ) from error
        if not math.isfinite(validated_cost) or validated_cost < 0:
            raise ValueError(
                "Road cost must be a finite number greater than or equal to zero."
            )
        return validated_cost
