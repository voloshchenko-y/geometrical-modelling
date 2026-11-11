import math

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QPolygonF
from PySide6.QtCore import Qt, QPointF, Signal

from geometry import Mat3


class Canvas(QWidget):
    point_picked = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(500, 500)
        self.setMouseTracking(True)

        self.scale = 6.0
        self.pan_x = -20.0
        self.pan_y = 0.0

        self.base_polygons = []
        self.transform = Mat3.identity()
        self.pivot = None

        self.picking_pivot = False

    # data
    def set_polygons(self, polygons):
        self.base_polygons = polygons
        self.update()

    def set_transform(self, m: Mat3):
        self.transform = m
        self.update()

    def set_pivot(self, pt):
        self.pivot = pt
        self.update()

    def set_picking_pivot(self, enabled: bool):
        self.picking_pivot = enabled
        self.setCursor(Qt.CrossCursor if enabled else Qt.ArrowCursor)

    # own world<->screen mapping (no QTransform)
    def world_to_screen(self, x, y):
        ox = self.width() / 2.0 + self.pan_x
        oy = self.height() / 2.0 + self.pan_y
        return ox + x * self.scale, oy - y * self.scale

    def screen_to_world(self, sx, sy):
        ox = self.width() / 2.0 + self.pan_x
        oy = self.height() / 2.0 + self.pan_y
        return (sx - ox) / self.scale, (oy - sy) / self.scale

    # painting
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(255, 255, 255))
        self._draw_grid(painter)
        self._draw_axes(painter)
        self._draw_part(painter)
        if self.pivot is not None:
            self._draw_pivot(painter)

    def _visible_world_bounds(self):
        x0, y0 = self.screen_to_world(0, self.height())
        x1, y1 = self.screen_to_world(self.width(), 0)
        return x0, y0, x1, y1

    def _draw_grid(self, painter):
        x0, y0, x1, y1 = self._visible_world_bounds()
        step = 5
        pen = QPen(QColor(225, 228, 232))
        pen.setWidth(1)
        painter.setPen(pen)

        start_x = int(math.floor(x0 / step) * step)
        end_x = int(math.ceil(x1 / step) * step)
        for gx in range(start_x, end_x + step, step):
            sx0, sy0 = self.world_to_screen(gx, y0)
            sx1, sy1 = self.world_to_screen(gx, y1)
            painter.drawLine(QPointF(sx0, sy0), QPointF(sx1, sy1))

        start_y = int(math.floor(y0 / step) * step)
        end_y = int(math.ceil(y1 / step) * step)
        for gy in range(start_y, end_y + step, step):
            sx0, sy0 = self.world_to_screen(x0, gy)
            sx1, sy1 = self.world_to_screen(x1, gy)
            painter.drawLine(QPointF(sx0, sy0), QPointF(sx1, sy1))

    def _draw_axes(self, painter):
        x0, y0, x1, y1 = self._visible_world_bounds()
        pen = QPen(QColor(60, 60, 60))
        pen.setWidth(2)
        painter.setPen(pen)

        ax0 = QPointF(*self.world_to_screen(x0, 0))
        ax1 = QPointF(*self.world_to_screen(x1, 0))
        painter.drawLine(ax0, ax1)
        self._arrowhead(painter, ax1, 0)

        ay0 = QPointF(*self.world_to_screen(0, y0))
        ay1 = QPointF(*self.world_to_screen(0, y1))
        painter.drawLine(ay0, ay1)
        self._arrowhead(painter, ay1, 90)

        painter.drawText(QPointF(ax1.x() - 14, ax1.y() - 6), "X")
        painter.drawText(QPointF(ay1.x() + 6, ay1.y() + 12), "Y")

    def _arrowhead(self, painter, tip: QPointF, angle_deg):
        size = 8
        a = math.radians(angle_deg + 150)
        b = math.radians(angle_deg - 150)
        p1 = QPointF(tip.x() + size * math.cos(a), tip.y() - size * math.sin(a))
        p2 = QPointF(tip.x() + size * math.cos(b), tip.y() - size * math.sin(b))
        painter.setBrush(QBrush(QColor(60, 60, 60)))
        painter.drawPolygon(QPolygonF([tip, p1, p2]))

    def _draw_part(self, painter):
        if not self.base_polygons:
            return
        path = QPainterPath()
        path.setFillRule(Qt.OddEvenFill)
        for poly in self.base_polygons:
            if not poly:
                continue
            screen_pts = []
            for (x, y) in poly:
                wx, wy = self.transform.apply(x, y)
                sx, sy = self.world_to_screen(wx, wy)
                screen_pts.append(QPointF(sx, sy))
            qpoly = QPolygonF(screen_pts)
            path.addPolygon(qpoly)
            path.closeSubpath()

        painter.setBrush(QBrush(QColor(178, 205, 235)))
        painter.setPen(QPen(QColor(15, 25, 40), 2))
        painter.drawPath(path)

    def _draw_pivot(self, painter):
        sx, sy = self.world_to_screen(*self.pivot)
        pen = QPen(QColor(210, 30, 30), 2)
        painter.setPen(pen)
        r = 6
        painter.drawLine(QPointF(sx - r, sy), QPointF(sx + r, sy))
        painter.drawLine(QPointF(sx, sy - r), QPointF(sx, sy + r))

    # ---- interaction ----
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            wx, wy = self.screen_to_world(event.position().x(), event.position().y())
            if self.picking_pivot:
                self.point_picked.emit(wx, wy)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale = max(0.5, min(60.0, self.scale * factor))
        self.update()

