import math

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPolygonF, QFont
from PySide6.QtCore import Qt, QPointF, Signal

from geometry import Mat3


class Canvas(QWidget):
    """Полотно: сітка, осі, крива та прямі (дотична, нормаль, асимптота).
    Усі точки проходять через матрицю перетворень self.transform (Mat3)."""

    point_picked = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 600)

        self.scale = 25.0            # пікселів на одну одиницю
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._drag = None

        self.curve_pts = []          # [(x, y), ...] до перетворень
        self.tangent = None          # ((x1,y1),(x2,y2)) або None
        self.normal = None
        self.asymptote = None
        self.curve_point = None      # (x, y) точка кривої, у якій будуються прямі
        self.node_point = (0.0, 0.0)
        self.label = ""
        self.transform = Mat3.identity()
        self.pivot = None
        self.picking_pivot = False

    # ---- дані ----
    def set_scene(self, curve_pts, tangent, normal, asymptote, curve_point, label=""):
        self.curve_pts = curve_pts
        self.tangent = tangent
        self.normal = normal
        self.asymptote = asymptote
        self.curve_point = curve_point
        self.label = label
        self.update()

    def set_transform(self, m: Mat3):
        self.transform = m
        self.update()

    def set_pivot(self, pt):
        self.pivot = pt
        self.update()

    def set_picking_pivot(self, enabled):
        self.picking_pivot = enabled
        self.setCursor(Qt.CrossCursor if enabled else Qt.ArrowCursor)

    # ---- власне відображення світ <-> екран ----
    def world_to_screen(self, x, y):
        ox = self.width() / 2.0 + self.pan_x
        oy = self.height() / 2.0 + self.pan_y
        return ox + x * self.scale, oy - y * self.scale

    def screen_to_world(self, sx, sy):
        ox = self.width() / 2.0 + self.pan_x
        oy = self.height() / 2.0 + self.pan_y
        return (sx - ox) / self.scale, (oy - sy) / self.scale

    def _to_screen(self, x, y):
        wx, wy = self.transform.apply(x, y)
        sx, sy = self.world_to_screen(wx, wy)
        return QPointF(sx, sy)

    # ---- малювання ----
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(255, 255, 255))
        self._draw_grid(p)
        self._draw_axes(p)
        self._draw_asymptote(p)
        self._draw_curve(p)
        self._draw_line(p, self.tangent, QColor(30, 80, 200), 2)
        self._draw_line(p, self.normal, QColor(30, 80, 200), 2)
        self._draw_markers(p)
        if self.label:
            p.setPen(QColor(40, 40, 40))
            p.setFont(QFont("Sans", 11))
            p.drawText(12, 22, self.label)

    def _bounds(self):
        x0, y0 = self.screen_to_world(0, self.height())
        x1, y1 = self.screen_to_world(self.width(), 0)
        return x0, y0, x1, y1

    def _draw_grid(self, p):
        x0, y0, x1, y1 = self._bounds()
        step = 1 if self.scale >= 12 else 5
        p.setPen(QPen(QColor(225, 228, 232), 1))
        gx = math.floor(x0 / step) * step
        while gx <= x1:
            a = self.world_to_screen(gx, y0)
            b = self.world_to_screen(gx, y1)
            p.drawLine(QPointF(*a), QPointF(*b))
            gx += step
        gy = math.floor(y0 / step) * step
        while gy <= y1:
            a = self.world_to_screen(x0, gy)
            b = self.world_to_screen(x1, gy)
            p.drawLine(QPointF(*a), QPointF(*b))
            gy += step

    def _draw_axes(self, p):
        x0, y0, x1, y1 = self._bounds()
        p.setPen(QPen(QColor(230, 60, 60), 2))       # вісь X — червона
        p.drawLine(QPointF(*self.world_to_screen(x0, 0)), QPointF(*self.world_to_screen(x1, 0)))
        p.setPen(QPen(QColor(60, 200, 60), 2))       # вісь Y — зелена
        p.drawLine(QPointF(*self.world_to_screen(0, y0)), QPointF(*self.world_to_screen(0, y1)))
        p.setPen(QColor(90, 90, 90))
        step = 1 if self.scale >= 12 else 5
        p.setFont(QFont("Sans", 8))
        k = math.ceil(x0 / step) * step
        while k <= x1:
            if k != 0 and (k % (2 * step) == 0 or self.scale >= 25):
                sx, sy = self.world_to_screen(k, 0)
                p.drawText(QPointF(sx - 6, sy + 14), f"{k:g}")
            k += step
        k = math.ceil(y0 / step) * step
        while k <= y1:
            if k != 0 and (k % (2 * step) == 0 or self.scale >= 25):
                sx, sy = self.world_to_screen(0, k)
                p.drawText(QPointF(sx + 5, sy + 4), f"{k:g}")
            k += step

    def _draw_curve(self, p):
        if len(self.curve_pts) < 2:
            return
        p.setPen(QPen(QColor(15, 15, 15), 2))
        prev = self._to_screen(*self.curve_pts[0])
        for (x, y) in self.curve_pts[1:]:
            cur = self._to_screen(x, y)
            # відкидаємо відрізки, що цілком далеко поза вікном (нескінченні гілки)
            if abs(cur.x()) < 1e5 and abs(cur.y()) < 1e5 and abs(prev.x()) < 1e5 and abs(prev.y()) < 1e5:
                p.drawLine(prev, cur)
            prev = cur

    def _draw_asymptote(self, p):
        if self.asymptote is None:
            return
        self._draw_line(p, self.asymptote, QColor(0, 150, 150), 2, dashed=True)

    def _draw_line(self, p, seg, color, width, dashed=False):
        if seg is None:
            return
        pen = QPen(color, width)
        if dashed:
            pen.setStyle(Qt.DashLine)
        p.setPen(pen)
        a = self._to_screen(*seg[0])
        b = self._to_screen(*seg[1])
        p.drawLine(a, b)

    def _draw_markers(self, p):
        p.setPen(QPen(QColor(0, 0, 0), 1))
        p.setBrush(QBrush(QColor(0, 0, 0)))
        n = self._to_screen(*self.node_point)
        p.drawEllipse(n, 3.5, 3.5)
        if self.curve_point is not None:
            p.setBrush(QBrush(QColor(20, 190, 20)))
            p.drawEllipse(self._to_screen(*self.curve_point), 5, 5)
        if self.pivot is not None:
            sx, sy = self.world_to_screen(*self.pivot)
            p.setPen(QPen(QColor(210, 30, 30), 2))
            r = 7
            p.drawLine(QPointF(sx - r, sy), QPointF(sx + r, sy))
            p.drawLine(QPointF(sx, sy - r), QPointF(sx, sy + r))

    # ---- взаємодія ----
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self.picking_pivot:
                wx, wy = self.screen_to_world(e.position().x(), e.position().y())
                self.point_picked.emit(wx, wy)
            else:
                self._drag = (e.position().x(), e.position().y(), self.pan_x, self.pan_y)

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            x, y, px, py = self._drag
            self.pan_x = px + e.position().x() - x
            self.pan_y = py + e.position().y() - y
            self.update()

    def mouseReleaseEvent(self, e):
        self._drag = None

    def wheelEvent(self, e):
        f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        self.scale = max(2.0, min(200.0, self.scale * f))
        self.update()
