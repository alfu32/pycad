# PyQt Drawing Application Specification

## High-Level Overview

This application is a PyQt-based drawing tool that allows users to draw lines on a canvas. The application supports multiple layers, each with its own properties such as color, line width, and visibility. Users can manage these layers using a non-blocking modal layer manager. Lines drawn on the canvas are stored within the respective layers, and intersections are handled within each layer to split lines at intersection points. The application also provides functionality to add, delete, and manage layers, ensuring that the layers list cannot be empty and the first layer is selected by default.

## Detailed Requirements

### Application Purpose and Functionality
- A PyQt-based drawing application allowing users to draw lines on a canvas.
- Support for multiple layers, each with unique properties (color, line width, visibility).
- Non-blocking modal for managing layers.
- Ensures the layers list cannot be empty and the first layer is selected by default.
- Handles intersections within each layer, splitting lines at intersection points.

### Layer Class
- **Attributes**:
  - `name`: Name of the layer.
  - `color`: Color of lines in the layer.
  - `width`: Width of lines in the layer.
  - `visible`: Visibility of the layer.
  - `lines`: List of lines in the layer.
- **Methods**:
  - `add_line(line)`: Adds a line to the layer and triggers cleanup.
  - `cleanup()`: Calls `rescan_intersections()`, `remove_short_lines()`, and `cleanup_duplicates()`.
  - `rescan_intersections()`: Detects intersections between lines within the layer, splits lines at intersection points, and updates the lines list.
  - `sort_points_on_line(line, points)`: Sorts intersection points along a line.
  - `split_line_by_points(line, points)`: Splits a line into segments based on sorted intersection points.
  - `cleanup_duplicates()`: Removes duplicate lines from the layer.
  - `remove_short_lines()`: Removes lines shorter than a specified threshold from the layer.

### Line Class
- **Attributes**:
  - `start_point`: Starting point of the line.
  - `end_point`: Ending point of the line.
  - `color`: Color of the line.
  - `width`: Width of the line.
- **Methods**:
  - `contains_point(point)`: Checks if a point is on the line within a margin.
  - `intersect(other)`: Calculates the intersection point with another line if they intersect.
  - `_points_equal(p1, p2)`: Checks if two points are equal within a tolerance.
  - `is_short(threshold)`: Checks if the line is shorter than a specified threshold.
  - `__eq__(other)`: Checks if two lines are equal based on their start and end points.
  - `__hash__()`: Generates a hash for the line based on its points.

### DrawingManager Class
- **Attributes**:
  - `layers`: List of layers in the canvas.
  - `current_layer_index`: Index of the currently selected layer.
  - `current_line`: The line currently being drawn.
  - `zoom_factor`: Zoom factor for the canvas.
  - `offset`: Offset for panning the canvas.
- **Methods**:
  - `set_current_layer(index)`: Sets the current layer by index.
  - `add_layer(layer)`: Adds a new layer to the canvas.
  - `remove_layer(index)`: Removes a layer by index, ensuring at least one layer remains.
  - `wheelEvent(event)`: Handles zooming in and out.
  - `map_to_scene(point)`: Maps a point from the view to the scene coordinates.
  - `map_to_view(point)`: Maps a point from the scene to the view coordinates.
  - `mousePressEvent(event)`: Starts drawing a line or deletes a line on right-click.
  - `mouseMoveEvent(event)`: Updates the end point of the current line and updates its color and width from the current layer.
  - `mouseReleaseEvent(event)`: Finalizes the current line, adds it to the current layer, and triggers layer cleanup.
  - `paintEvent(event)`: Paints the lines of visible layers and the current line being drawn.
  - `draw_cross(painter, point)`: Draws a small red cross at a point.
  - `snap_to_angle(start_point, end_point)`: Snaps the end point to increments of 15 degrees from the start point when Ctrl is held.

### LayerItem Class
- Custom widget for displaying and editing a layer in the layer manager.
- **Components**:
  - `name_input`: QLineEdit for editing the layer name.
  - `width_input`: QSpinBox for setting the line width.
  - `color_button`: QPushButton for selecting the layer color.
  - `visibility_checkbox`: QCheckBox for toggling layer visibility.
  - `remove_button`: QPushButton for removing the layer.
- **Methods**:
  - `on_name_changed(text)`: Updates the layer name.
  - `on_width_changed(value)`: Updates the layer width.
  - `select_color()`: Opens a color dialog to select the layer color.
  - `on_visibility_changed(state)`: Updates the layer visibility.
  - `on_remove_clicked()`: Triggers the removal of the layer.

### LayerManager Class
- Non-blocking modal dialog for managing layers.
- **Components**:
  - `layer_list`: QListWidget for displaying layers.
  - `add_layer_button`: QPushButton for adding a new layer.
- **Methods**:
  - `update_layer_list()`: Updates the layer list with current layers, highlighting the selected layer.
  - `add_layer()`: Adds a new layer and updates the list.
  - `remove_layer(layer)`: Removes a layer and updates the list.

### MainWindow Class
- Main application window.
- **Attributes**:
  - `canvas`: Canvas widget for drawing.
  - `layer_manager`: Non-blocking modal layer manager.
- **Methods**:
  - `init_ui()`: Initializes the UI, sets up the canvas, and shows the layer manager.
- **Initialization**:
  - Sets the window title to "PySide6 Drawing Application".
  - Sets the initial size to 800x600.
  - Shows the layer manager and selects the first layer by default.

### Algorithms and Functional Solutions

#### Intersection Handling
- When a new line intersects an existing line, the intersection points are tracked in a table.
- Each line with intersections is grouped, and intersection points are sorted along the line.
- The original line is split at the intersection points, and new segments are created.
- Cleanup operations are performed within each layer to ensure no dependency across layers.

self intersecting lines will work out well with the following algorithm:


- add the new line to the model first
- rescan the entire model for intersections.
  - put each intersection in a table tracking the targeted line and the intersection point
  - group the table by line id ( getting an associated list of split points)
     - project the intersection points onto the target line, order them on the local line coordinates, generate the segments by successive pairs of points delete the original segment and add the new segments.

**Zooming About Point:**

Zooming About Point will work out well with the following algorithm.

- Get the current mouse position in screen coordinates.
- Compute the current mouse position in model coordinates using the current matrix.
- Scale the matrix according to the zoom.
- Translate the zoomed matrix so that the screen coordinates of the mouse model coordinates are the same as calculated in the first step.


### Non-Blocking Modal for Layer Manager
The layer manager is implemented as a QDialog and shown using show(), ensuring it does not block interaction with the main window.

### Selected Layer Marker
The selected layer in the layer manager is highlighted with a light blue background.

### Dynamic Line Properties
During drawing, the line's color and width are continuously updated to match the current layer's properties, ensuring consistency even when the layer properties change mid-draw.
