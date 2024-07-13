from PySide6.QtCore import QPoint


class UserEventsCollector:

    def __init__(self):
        self.points: list[QPoint] = []
        self.last_point: QPoint = None
        self.text_lines: list[str] = []
        self.last_text: str = None

    def reset(self):
        self.points: list[QPoint] = []
        self.last_point: QPoint = None
        self.text_lines: list[str] = []
        self.last_text: str = None

    def get_data(self) -> tuple[list[QPoint], list[str]]:
        return [p for p in self.points], [t for t in self.text_lines]

    def point(self, point: QPoint):
        self.points.append(point)

    def text(self, text: str):
        self.text_lines.append(text)

