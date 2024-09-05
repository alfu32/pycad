import math
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, override

import ezdxf
from PySide6.QtCore import QPoint, QRect, Signal, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QPushButton

from pycad.Drawable import Drawable, HotspotClasses, HotspotHandler
from pycad.Plugin import BaseTool
from pycad.TextSignalData import TextSignalData
from pycad.util_geometry import line_intersects_rect, line_contains_point, _points_equal, Segment, HasSegment
from ezdxf.document import Drawing as DXFDrawing
from ezdxf.document import Modelspace as DXFModelspace


class PolyLine(Drawable, ABC):

    def __init__(self):
        super(Drawable, self).__init__()
        self.segment: Segment = Segment(QPoint(0, 0), QPoint(0, 0))
        self._points = 0
        self.points: List[QPoint] = []
        self.moving_point: QPoint = None
        self.max_points: int = 2

    def get_segments(self, with_moving_point=False) -> list[Segment]:
        segments: list[Segment] = []
        if len(self.points) == 0:
            return segments
        elif len(self.points) == 1:
            if with_moving_point and self.moving_point is not None:
                return [Segment(self.points[0], self.moving_point)]
            else:
                return segments
        else:
            for i, point in enumerate(self.points[1:]):
                segment = Segment(self.points[i - 1], self.points[i])
                segments.append(segment)
            if with_moving_point and self.moving_point is not None:
                segments.append(Segment(self.points[-1], self.moving_point))
        return segments

    @override
    def is_done(self):
        return self._points >= 2

    def isin(self, rect: QRect) -> bool:
        for s in self.get_segments():
            if s.is_in(rect):
                return True
        return False

    def intersects(self, rect: QRect) -> bool:
        for s in self.get_segments():
            if s.intersects(rect):
                return True
        return False

    def set_start_point(self, value: QPoint):
        self.segment.set(value, self.segment.b)

    def set_send_point(self, value: QPoint):
        self.segment.set(self.segment.a, value)

    def get_hotspots(self) -> List[Tuple[HotspotClasses, QPoint, HotspotHandler]]:
        hotspots: List[Tuple[HotspotClasses, QPoint, HotspotHandler]] = []
        for s in self.get_segments():
            a = s.a
            b = s.b
            hotspots.append((HotspotClasses.ENDPOINT, a, s.set_a))
            hotspots.append((HotspotClasses.ENDPOINT, b, s.set_b))
        return hotspots

    def get_snap_points(self) -> List[Tuple[HotspotClasses, QPoint]]:
        snap_points: List[Tuple[HotspotClasses, QPoint]] = []
        for s in self.get_segments():
            a = s.a
            b = s.b
            snap_points.append((HotspotClasses.ENDPOINT, a))
            snap_points.append((HotspotClasses.MIDPOINT, (a + b) / 2))
            snap_points.append((HotspotClasses.ENDPOINT, b))
        return snap_points

    # TODO remove 1000
    def update(self, painter: QPainter):
        pass

    # TODO remove 1000
    def set_next_point(self, point: QPoint):
        self.set_send_point(point)
        self.finished.emit(True)

    def contains_point(self, point):
        return self.segment.contains_point(point)

    def intersect(self, other: HasSegment) -> Optional[QPoint]:
        return self.segment.intersect(other.segment)

    def is_empty(self, threshold=1.0):
        length = math.hypot(self.segment.a.x() - self.segment.b.x(), self.segment.a.y() - self.segment.b.y())
        return length < threshold

    def __eq__(self, other: 'PolyLine'):
        return False

    def __hash__(self):
        start_tuple = (self.segment.a.x(), self.segment.a.y())
        end_tuple = (self.segment.b.x(), self.segment.b.y())
        return hash((min(start_tuple, end_tuple), max(start_tuple, end_tuple)))

    def draw(self, painter: QPainter):
        a = self.segment.a
        b = self.segment.b if self._points >= 2 else self.moving_point
        painter.drawLine(a.x(), a.y(), b.x(), b.y())

    def save_to_dxf(self, doc: DXFDrawing, layer_name: str):
        msp: DXFModelspace = doc.modelspace()

        msp.add_line(
            (self.segment.a.x(), self.segment.a.y()),
            (self.segment.b.x(), self.segment.b.y()),
            dxfattribs={
                'layer': layer_name,
            }
        )

    @classmethod
    def from_dxf(cls, entity_data: ezdxf.entities.Line):
        start_point = QPoint(entity_data.dxf.start.x, entity_data.dxf.start.y)
        end_point = QPoint(entity_data.dxf.end.x, entity_data.dxf.end.y)
        return cls(start_point, end_point)


class MultipointTool(BaseTool):
    drawable_ready = Signal(Drawable)
    point_received = Signal(QPoint)
    text_received = Signal(str)
    drawable_started = Signal(Drawable)

    def __init__(self):
        super(BaseTool, self).__init__()
        self.identifier = "core_plugin_polyline"
        self.name = "Polyline"
        self.built_object = []
        self.button = QPushButton(f"{self.name}")
        self.button.clicked.connect(self.start)
        self.is_active = False
        print(f"{self.identifier} initialized", flush=True)

    def get_ui_fragment(self):
        return self.button

    def start(self):
        if self.is_active:
            pass
        else:
            self.built_object = []
            print(f"{self.identifier}::start", flush=True)
            try:
                self.drawable_started.emit(self.built_object)
            except:
                pass
            self.button.setChecked(True)
            self.is_active = True

    def push_model_point(self, point: QPoint):
        if self.is_active:
            if len(self.built_object) > 0 and point == self.built_object[0]:
                print(f"{self.identifier} finished by close point", flush=True)
                self.drawable_ready.emit(self.built_object)
                self.is_active = False
            self.built_object.append(point)
            try:
                self.point_received.emit(point)
            except:
                pass

            print(f"{self.identifier}::push_model_point {point} , points:{self.built_object}", flush=True)

    def push_user_text(self, text: TextSignalData):
        if self.is_active:
            try:
                self.text_received.emit(text.text)
            except:
                pass
            if text.key == Qt.Key_Escape:
                print(f"{self.identifier} finished by escape", flush=True)
                self.is_active = False
            else:
                print(f"{self.identifier}::push_user_text {text.text}", flush=True)

    def draw(self, painter: QPainter, moving_point: QPoint):
        r = self.built_object
        l = len(r)
        # print(f"drawing Polyline Plugin figure {l} points : {r}", flush=True)
        if l > 1:
            a = r[0]
            b = r[1]
            painter.drawLine(a.x(), a.y(), b.x(), b.y())
            for i, p in enumerate(self.built_object):
                if i == 0:
                    continue
                else:
                    a = r[i]
                    b = r[i + 1] if (i + 1) < l else moving_point
                    painter.drawLine(a.x(), a.y(), b.x(), b.y())
        elif l > 0:
            a = r[0]
            b = moving_point
            painter.drawLine(a.x(), a.y(), b.x(), b.y())
        else:
            pass

        # raise NotImplementedError(f"{self.identifier} must implement draw method")

    def finalize(self):
        try:
            self.drawable_ready.emit(self.built_object)
        except:
            pass
        self.button.setChecked(False)
        self.is_active = False
        return self.built_object

    def build(self):
        return self.built_object

    def destroy(self):
        pass
