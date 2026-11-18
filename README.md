# City Network Builder

City Network Builder is a visual desktop application for learning weighted
graphs and Minimum Spanning Trees (MST). It allows users to place districts,
connect them with roads that have construction costs, and use Prim's Algorithm
to find or practice building the lowest-cost connected network.

The application is built with Python and PySide6.

## Minimum Spanning Tree

A graph is a collection of:

- **Vertices** (districts in this app): points or locations.
- **Edges** (roads in this app): connections between two vertices.
- **Weights** (costs in this app): values assigned to edges.

A spanning tree connects every vertex in a graph without creating a cycle. It
contains exactly `V - 1` edges when the graph has `V` vertices.

A Minimum Spanning Tree is the spanning tree with the smallest possible total
edge cost. MSTs are useful for designing systems such as road networks, power
grids, and communication networks, where every location must be connected while
construction cost is minimized.

For example, roads costing 4, 2, and 5 may form the minimum network at a total
cost of 11. Another network with the same districts may have a higher cost.

## Prim's Algorithm

Prim's Algorithm grows a tree from a starting district:

1. Mark the starting district as visited.
2. Look at every road that connects a visited district to an unvisited district.
3. Select the road with the lowest cost.
4. Mark the other district as visited.
5. Repeat until every district is visited.

The algorithm does not need to consider roads that connect two visited districts
because such a road would create a cycle. In a disconnected network, the
algorithm can reach only one connected component, so it cannot produce a valid
spanning tree for the entire graph.

The order of selected roads can vary when two roads have the same cost, but a
minimum spanning tree will have the same minimum total cost.

## Using the App

### Create a network

1. Run `python main.py`.
2. Click **Add District**.
3. Click an empty area of the map to place a district.
4. Click **Add Road**.
5. Select two districts.
6. Enter a positive construction cost in the dialog.

The same road cannot be added twice, and a road cannot connect a district to
itself. District names are generated automatically.

### Edit the network

- **Delete District** removes the selected district and all roads connected to it.
- **Delete Road** removes the selected road.
- **Reset Network** removes every district and road.
- **Generate Random Network** replaces the current map with a random connected
  network.

### Automatic Mode

Automatic Mode demonstrates Prim's Algorithm:

1. Place at least two districts and connect them.
2. Click **Automatic Mode**.
3. Select a starting district.
4. Click **Start**.
5. Use **Next Step** and **Previous Step** to move through the algorithm.
6. Read the side panel and map highlights to see eligible roads, selections,
   rejected roads, visited districts, and total cost.

**Reset Visualization** clears the visualization while keeping the network.

### Manual Mode

Manual Mode lets the user build the minimum spanning tree:

1. Build a connected network.
2. Click **Manual Mode**.
3. Select the cheapest eligible road from the visited part of the network.
4. Continue until all districts are visited.

The app highlights eligible roads and reports incorrect choices, rejected roads,
visited districts, and the resulting total cost. **Reset Manual Mode** starts
the exercise again without clearing the network.

## Project Files

| File | Purpose |
| --- | --- |
| `main.py` | Starts the PySide6 application and creates the main window. |
| `main_window.py` | Defines the window layout and coordinates building, automatic, manual, delete, reset, and random-network actions. |
| `city_canvas.py` | Draws districts and roads with PySide6 graphics and handles canvas selection and highlighting. |
| `graph.py` | Stores districts, roads, positions, costs, and graph adjacency data. It provides validation and graph change notifications. |
| `prim.py` | Implements Prim's Algorithm and builds detailed algorithm steps for the automatic and manual modes. |
| `styles.py` | Defines the application color palette, pixel-style controls, and bundled font loading. |
| `sounds.py` | Loads and plays the application's sound effects. |
| `requirements.txt` | Lists the runtime and test dependencies. |
| `CityNetworkBuilder.spec` | Defines the PyInstaller build settings, assets, icon, and windowed executable mode. |
| `.gitignore` | Excludes caches, virtual environments, build output, and editor/OS files from Git. |

### Assets

| Path | Purpose |
| --- | --- |
| `assets/fonts/` | Pixel-style fonts used by the interface. |
| `assets/sfx/` | Short sound effects for network actions. |
| `assets/app_icon.ico` | Windows executable and application icon. |
| `assets/app_icon.png` | PNG version of the application icon. |

### Tests

The `tests/` directory contains pytest coverage for graph operations, Prim's
Algorithm, automatic mode, manual mode, city-canvas behavior, and random network
generation.

## Requirements

- Windows
- Python 3.10 or newer
- PySide6
- pytest

The project only requires packages listed in `requirements.txt`.

## Setup

From the project directory:

```powershell
python -m pip install -r requirements.txt
```

Run the app:

```powershell
python main.py
```

Run the tests:

```powershell
python -m pytest -q
```

## Build a Windows Executable

Install PyInstaller:

```powershell
python -m pip install pyinstaller
```

Build from the existing specification:

```powershell
python -m PyInstaller --clean --noconfirm CityNetworkBuilder.spec
```

The executable is created at:

```text
dist\CityNetworkBuilder.exe
```

The build includes the files in `assets/`, so the fonts, icons, and sound effects
remain available to the application.
