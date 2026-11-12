import math

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PySide6.QtCore import Qt, QPointF, QRectF, Signal

from bezier import Contour, handle_index


class Canvas(QWidget):
    contour_changed = Signal()
    segment_selected = Signal(int)
    point_picked = Signal(float, float)
    joint_toggled = Signal(int)

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
        self.focus = None  # вибрана точка
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

    # малювання
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(255, 255, 255))
        self._grid(p)
        self._curves(p)
        if self.show_polygon:
            self._polygons(p)
        self._points(p)
        self._focus_rings(p)
        if self.show_polygon:
            self._legend(p)
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
        for j, (e1, _e2) in enumerate(self.contour.joints):
            c = self._pt(self.contour.pts[e1[0]][e1[1]])
            p.setPen(QPen(QColor(120, 0, 0), 1))
            p.setBrush(QBrush(QColor(225, 30, 30)))
            if self.contour.smooth[j]:
                p.drawEllipse(c, 5.5, 5.5)
            else:
                p.drawRect(QRectF(c.x() - 5.0, c.y() - 5.0, 10.0, 10.0))

    def _focus_rings(self, p):
        if self.focus is None or not self.show_polygon:
            return
        i, k = self.focus
        if i >= len(self.contour.pts):
            return
        s = self.contour.pts[i]
        green, red = [], []
        if k in (1, 2):
            end = 0 if k == 1 else 3
            green.append(s[k])
            red.append(s[end])
            j = self.contour.joint_index(i, end)
            if j is not None:
                e1, e2 = self.contour.joints[j]
                oi, ok = e2 if e1 == (i, end) else e1
                green.append(self.contour.pts[oi][handle_index(ok)])
        else:
            red.append(s[k])
        p.setBrush(Qt.NoBrush)
        for pts, col in ((green, QColor(0, 170, 60)), (red, QColor(220, 20, 20))):
            p.setPen(QPen(col, 2.5))
            for q in pts:
                p.drawEllipse(self._pt(q), 11.0, 11.0)

    def _legend(self, p):
        items = (("c", QColor(225, 30, 30), "вузлова точка (гладкість 1-го порядку)"),
                 ("s", QColor(225, 30, 30), "точка зламу (гладкість не забезпечується)"),
                 ("c", QColor(40, 200, 40), "реперна точка (ручка B або C)"),
                 ("c", QColor(0, 0, 0), "кінцева точка дуги"))
        p.setFont(QFont("Segoe UI", 9))
        w, h = 292.0, 18.0 * len(items) + 10.0
        p.setPen(QPen(QColor(200, 200, 200), 1))
        p.setBrush(QBrush(QColor(255, 255, 255, 230)))
        p.drawRect(QRectF(8.0, 8.0, w, h))
        for n, (shape, col, text) in enumerate(items):
            cy = 20.0 + 18.0 * n
            p.setPen(QPen(col.darker(160), 1))
            p.setBrush(QBrush(col))
            if shape == "s":
                p.drawRect(QRectF(15.0, cy - 5.0, 10.0, 10.0))
            else:
                p.drawEllipse(QPointF(20.0, cy), 5.0, 5.0)
            p.setPen(QPen(QColor(40, 40, 40), 1))
            p.drawText(QPointF(34.0, cy + 4.0), text)

    # миша
    def _hit(self, sx, sy):
        best, bd = None, 10.0
        for i, s in enumerate(self.contour.pts):
            for k, q in enumerate(s):
                px, py = self.world_to_screen(q[0], q[1])
                d = math.hypot(px - sx, py - sy)
                # пріоритет
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
                self.focus = hit
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

    def _hit_joint(self, sx, sy):
        best, bd = None, 10.0
        for j, (e1, _e2) in enumerate(self.contour.joints):
            q = self.contour.pts[e1[0]][e1[1]]
            px, py = self.world_to_screen(q[0], q[1])
            d = math.hypot(px - sx, py - sy)
            if d < bd:
                best, bd = j, d
        return best

    def mouseDoubleClickEvent(self, e):
        if e.button() != Qt.LeftButton or self.picking_pivot:
            return
        if not (self.editable and self.show_polygon):
            return
        j = self._hit_joint(e.position().x(), e.position().y())
        if j is None:
            return
        self._drag_pt = None
        self.contour.toggle_joint(j)
        i, k = self.contour.joints[j][0]
        self.focus = (i, k)
        self.selected = i
        self.segment_selected.emit(i)
        self.joint_toggled.emit(j)
        self.update()

    def mouseReleaseEvent(self, e):
        self._drag_pt = None
        self._pan = None

    def wheelEvent(self, e):
        f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        self.scale = max(4.0, min(150.0, self.scale * f))
        self.update()
