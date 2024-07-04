### Layered Drawing Application Specification

#### Initial Setup
- Implement a PyQt desktop application using PySide6.
- The application should be cross-platform.
- The initial window size should be 800x600.

#### Drawing Canvas
- The main application window should include a drawing canvas for drawing lines, dimensions, and text.
- Lines are drawn by clicking and dragging the mouse.
- The canvas should support zooming in and out centered around the current mouse position using the mouse wheel.
- Line widths and dash patterns should be transformed to model space, adjusting with the zoom.

#### Layers
- The application should support multiple layers, each with an associated name, color, line width, linetype, and visibility.
- Layers should support adding lines, rescan for intersections, and cleanup (remove short lines and duplicates).
- The layer list should have a default layer named "Layer-0".
- Provide a UI to manage layers, including creating, deleting, and modifying layers.
- Each layer item in the list should include inputs for name, width, color (color picker), visibility (checkbox), linetype (dropdown), and a remove button.
- Changes to layer properties should be automatically saved on change.
- The selected layer should be indicated with a light blue background.
- Ensure the first layer is selected by default at initialization.
- A non-blocking modal should always display the layer manager.

#### Line Drawing
- Lines should be drawn with the color and width specified by the current layer.
- Intersections within a layer should split the lines at the intersection points.
- Short lines (length < 1.0) should be automatically removed after drawing.
- Controls and interactions:
  - Left-click and drag to draw a line.
  - Right-click to delete a line.
  - Ctrl+drag to snap the line to 15-degree increments.

#### Dimension Drawing
- Dimensions should be constructed the same way as lines.
- Stored as DXF dimension objects if supported.

#### Text Drawing
- Text should use the first point as the anchor and the second point to determine the orientation.
- Text input via a dialog after setting orientation.

#### UI Controls
- Toggle Grid Snap (checkbox).
- Toggle AutoCut (checkbox).
- Toggle Vertex Snap (checkbox).
- Linetype selection via QComboBox.
- Drawing mode buttons for Line, Dimension, and Text modes.
- One-line status text at the bottom of the interface.

#### Layer Manager
- Layers saved/loaded as DXF with layer definitions.
- Saving should happen automatically on line add/remove.
- Read and write linetypes and custom attributes (XDATA) in DXF.
- Handle zooming by transforming the current and future matrices, ensuring mouse model coordinates remain consistent.

#### Detailed Solutions

**AutoCut and Cleanup:**

Use this solution, that's proved correct and generates the correct source code:

- Add the new line to the model first.
- Rescan the entire model for intersections.
  - Put each intersection in a table tracking the targeted line and the intersection point.
  - Group the table by line id (getting an associated list of split points).
    - Project the intersection points onto the target line, order them on the local line coordinates, generate the segments by successive pairs of points, delete the original segment, and add the new segments.


**Zooming About Point:**

You need to take into account the current and future transform matrix.
Try this:
- Get the current mouse position in screen coordinates.
- Compute the current mouse position in model coordinates using the current matrix.
- Scale the matrix according to the zoom.
- Translate the zoomed matrix so that the screen coordinates of the mouse model coordinates are the same as calculated in the first step.
