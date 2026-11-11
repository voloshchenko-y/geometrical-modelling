import math

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PySide6.QtCore import Qt, QPointF, Signal

from bezier import Contour


class Canvas(QWidget):
    """Полотно: сітка, осі, криволінійний контур, характеристичні ламані,
    рухомі реперні точки (перетягуються мишею)."""

    contour_changed = Signal()
    segment_selected = Signal(int)
    point_picked = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(700, 600)
        self.scale = 34.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.contour = Contour()
        self.curves = []
        self.show_polygon = True
        self.selected = 0
        self.pivot = None
        self.picking_pivot = False
        self.editable = True
        self._drag_pt = None
        self._pan = None

    def set_contour(self, contour, curves):
        self.contour = contour
        self.curves = curves
        self.update()

    def set_picking_pivot(self, on):
        self.picking_pivot = on
        self.setCursor(Qt.CrossCursor if on else Qt.ArrowCursor)

    def world_to_screen(self, x, y):
        return (self.width() / 2.0 + self.pan_x + x * self.scale,
                self.height() / 2.0 + self.pan_y - y * self.scale)

    def screen_to_world(self, sx, sy):
        return ((sx - self.width() / 2.0 - self.pan_x) / self.scale,
                (self.height() / 2.0 + self.pan_y - sy) / self.scale)

    def _pt(self, p):
        return QPointF(*self.world_to_screen(p[0], p[1]))

    # ---- малювання ----
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(255, 255, 255))
        self._grid(p)
        self._curves(p)
        if self.show_polygon:
            self._polygons(p)
        self._points(p)
        if self.pivot is not None:
            sx, sy = self.world_to_screen(*self.pivot)
            p.setPen(QPen(QColor(210, 30, 30), 2))
            p.drawLine(QPointF(sx - 7, sy), QPointF(sx + 7, sy))
            p.drawLine(QPointF(sx, sy - 7), QPointF(sx, sy + 7))

    def _grid(self, p):
        x0, y0 = self.screen_to_world(0, self.height())
        x1, y1 = self.screen_to_world(self.width(), 0)
        p.setPen(QPen(QColor(228, 231, 235), 1))
        g = math.floor(x0)
        while g <= x1:
            p.drawLine(QPointF(*self.world_to_screen(g, y0)), QPointF(*self.world_to_screen(g, y1)))
            g += 1
        g = math.floor(y0)
        while g <= y1:
            p.drawLine(QPointF(*self.world_to_screen(x0, g)), QPointF(*self.world_to_screen(x1, g)))
            g += 1
        p.setPen(QPen(QColor(230, 60, 60), 2))
        p.drawLine(QPointF(*self.world_to_screen(x0, 0)), QPointF(*self.world_to_screen(x1, 0)))
        p.setPen(QPen(QColor(60, 200, 60), 2))
        p.drawLine(QPointF(*self.world_to_screen(0, y0)), QPointF(*self.world_to_screen(0, y1)))

    def _curves(self, p):
        for i, pts in enumerate(self.curves):
            if i == self.selected and self.show_polygon:
                p.setPen(QPen(QColor(20, 70, 200), 3))
            else:
                p.setPen(QPen(QColor(15, 15, 15), 2))
            prev = self._pt(pts[0])
            for q in pts[1:]:
                cur = self._pt(q)
                p.drawLine(prev, cur)
                prev = cur

    def _polygons(self, p):
        for i, s in enumerate(self.contour.pts):
            col = QColor(20, 70, 200) if i == self.selected else QColor(170, 170, 170)
            p.setPen(QPen(col, 1))
            for a, b in ((0, 1), (1, 2), (2, 3)):
                p.drawLine(self._pt(s[a]), self._pt(s[b]))

    def _points(self, p):
        if not self.show_polygon:
            return
        for i, s in enumerate(self.contour.pts):
            sel = i == self.selected
            for k, q in enumerate(s):
                if k in (0, 3):
                    p.setPen(QPen(QColor(0, 0, 0), 1))
                    p.setBrush(QBrush(QColor(0, 0, 0)))
                    r = 4.0 if sel else 3.0
                else:
                    p.setPen(QPen(QColor(0, 120, 0), 1))
                    p.setBrush(QBrush(QColor(40, 200, 40)))
                    r = 4.5 if sel else 3.0
                p.drawEllipse(self._pt(q), r, r)

    # ---- миша ----
    def _hit(self, sx, sy):
        best, bd = None, 10.0
        for i, s in enumerate(self.contour.pts):
            for k, q in enumerate(s):
                px, py = self.world_to_screen(q[0], q[1])
                d = math.hypot(px - sx, py - sy)
                # зеленим (k=1,2) віддаємо перевагу при однакових відстанях
                if d < bd or (d == bd and k in (1, 2)):
                    best, bd = (i, k), d
        return best

    def mousePressEvent(self, e):
        sx, sy = e.position().x(), e.position().y()
        if e.button() == Qt.LeftButton:
            if self.picking_pivot:
                self.point_picked.emit(*self.screen_to_world(sx, sy))
                return
            hit = self._hit(sx, sy) if (self.editable and self.show_polygon) else None
            if hit is not None:
                self._drag_pt = hit
                self.selected = hit[0]
                self.segment_selected.emit(hit[0])
                self.update()
            else:
                self._pan = (sx, sy, self.pan_x, self.pan_y)

    def mouseMoveEvent(self, e):
        sx, sy = e.position().x(), e.position().y()
        if self._drag_pt is not None:
            wx, wy = self.screen_to_world(sx, sy)
            i, k = self._drag_pt
            self.contour.move_point(i, k, wx, wy)
            self.contour_changed.emit()
        elif self._pan is not None:
            self.pan_x = self._pan[2] + sx - self._pan[0]
            self.pan_y = self._pan[3] + sy - self._pan[1]
            self.update()

    def mouseReleaseEvent(self, e):
        self._drag_pt = None
        self._pan = None

    def wheelEvent(self, e):
        f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        self.scale = max(4.0, min(150.0, self.scale * f))
        self.update()
