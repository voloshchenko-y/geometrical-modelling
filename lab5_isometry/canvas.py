import math

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtCore import Qt, QPointF

AXIS_LENGTH = 150.0  # довжина осей


class Canvas(QWidget):
    def __init__(self, scene, parent=None):
        super().__init__(parent)
        self.setMinimumSize(700, 600)
        self.scene = scene
        self.zoom = 3.0  # px / од.
        self.pan_x = 0.0
        self.pan_y = 120.0  # нижче центра
        self.show_axes = True
        self.show_pivot = True
        self._pan = None

    def reset_view(self):
        self.zoom, self.pan_x, self.pan_y = 3.0, 0.0, 120.0
        self.update()

    def to_screen(self, x, y):
        return QPointF(self.width() / 2.0 + self.pan_x + x * self.zoom,
                       self.height() / 2.0 + self.pan_y - y * self.zoom)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(255, 255, 255))
        if self.show_axes:
            self._axes(p)
        self._body(p)
        if self.show_pivot:
            self._pivot(p)

    def _axes(self, p):
        p.setFont(QFont("Segoe UI", 11, QFont.Bold))
        for name, col, a, b in self.scene.axes_2d(AXIS_LENGTH):
            qa, qb = self.to_screen(*a), self.to_screen(*b)
            p.setPen(QPen(QColor(*col), 3))
            p.drawLine(qa, qb)
            dx, dy = qb.x() - qa.x(), qb.y() - qa.y()
            n = math.hypot(dx, dy) or 1.0
            p.drawText(QPointF(qb.x() + 8 * dx / n - 4, qb.y() + 14 * dy / n + 4), name)

    def _body(self, p):
        p.setPen(QPen(QColor(10, 10, 10), 1.6))
        for a, b in self.scene.edges_2d():
            p.drawLine(self.to_screen(*a), self.to_screen(*b))

    def _pivot(self, p):
        c = self.to_screen(*self.scene.pivot_2d())
        p.setPen(QPen(QColor(210, 30, 30), 2))
        p.drawEllipse(c, 6.0, 6.0)
        p.drawLine(QPointF(c.x() - 10, c.y()), QPointF(c.x() + 10, c.y()))
        p.drawLine(QPointF(c.x(), c.y() - 10), QPointF(c.x(), c.y() + 10))

    # миша
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._pan = (e.position().x(), e.position().y(), self.pan_x, self.pan_y)

    def mouseMoveEvent(self, e):
        if self._pan is not None:
            self.pan_x = self._pan[2] + e.position().x() - self._pan[0]
            self.pan_y = self._pan[3] + e.position().y() - self._pan[1]
            self.update()

    def mouseReleaseEvent(self, e):
        self._pan = None

    def wheelEvent(self, e):
        f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        self.zoom = max(0.5, min(30.0, self.zoom * f))
        self.update()
