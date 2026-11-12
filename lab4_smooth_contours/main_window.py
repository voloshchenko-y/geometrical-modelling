import os

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QGroupBox,
    QDoubleSpinBox, QSpinBox, QPushButton, QLabel, QScrollArea, QCheckBox,
    QComboBox, QSlider,
)
from PySide6.QtCore import Qt, QTimer

from geometry import Mat3
from bezier import Contour, morph, target_shape
from canvas import Canvas

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FILE = os.path.join(HERE, "duck_contour.json")

DEFAULTS = dict(step=0.05, anim_step=0.02, weight=1.0)


def _spin(lo, hi, val, step=0.1, dec=2):
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(dec)
    s.setSingleStep(step)
    s.setValue(val)
    return s


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Лаб. робота №4 — Побудова гладких криволінійних контурів "
                            "(Варіант 5: криві 3-го порядку в інженерному вигляді, контур 26)")
        self.resize(1500, 950)

        self.original = Contour.load(DEFAULT_FILE)
        self.contour = self.original.copy()
        self.base = None  # старт
        self.target = None
        self.t = 0.0
        self.t_dir = 1
        self.canvas = Canvas()
        self.canvas.contour_changed.connect(self._on_edited)
        self.canvas.segment_selected.connect(self._on_segment_selected)
        self.canvas.point_picked.connect(self._on_pivot_picked)
        self.canvas.joint_toggled.connect(self._on_joint_toggled)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

        central = QWidget()
        self.setCentralWidget(central)
        lay = QHBoxLayout(central)
        lay.addWidget(self._panel(), 0)
        lay.addWidget(self.canvas, 1)
        self._sync_weight_boxes()
        self._redraw()

    # панель
    def _panel(self):
        inner = QWidget()
        inner.setStyleSheet("QDoubleSpinBox, QSpinBox, QPushButton, QComboBox { min-height: 24px; }")
        v = QVBoxLayout(inner)

        g = QGroupBox("Гладкість 1-го порядку (Лаб. 4)")
        f = QFormLayout(g)
        self.lbl_hint = QLabel(
            "Подвійний клік по стиковій точці перемикає її:<br>"
            "<span style='color:#d21e1e'>●</span> вузлова точка — гладкість забезпечується: "
            "при русі крайньої реперної точки протилежна рухається сама;<br>"
            "<span style='color:#d21e1e'>■</span> точка зламу — гладкість не забезпечується.")
        self.lbl_hint.setWordWrap(True)
        self.lbl_counts = QLabel()
        self.lbl_joint = QLabel()
        self.lbl_joint.setWordWrap(True)
        self.lbl_event = QLabel("")
        self.lbl_event.setWordWrap(True)
        self.lbl_event.setStyleSheet("color: #8a1010;")
        b_all_s = QPushButton("Усі стики → вузлові точки")
        b_all_s.clicked.connect(lambda: self._set_all_joints(True))
        b_all_b = QPushButton("Усі стики → точки зламу")
        b_all_b.clicked.connect(lambda: self._set_all_joints(False))
        f.addRow(self.lbl_hint)
        f.addRow(self.lbl_counts)
        f.addRow(self.lbl_joint)
        f.addRow(self.lbl_event)
        f.addRow(b_all_s)
        f.addRow(b_all_b)
        v.addWidget(g)

        g = QGroupBox("Відображення")
        f = QFormLayout(g)
        self.cb_poly = QCheckBox("Показувати характеристичні багатокутники")
        self.cb_poly.setChecked(True)
        self.cb_poly.toggled.connect(self._on_poly_toggled)
        self.sb_step = _spin(0.005, 0.25, DEFAULTS["step"], 0.005, 3)
        self.sb_step.valueChanged.connect(self._redraw)
        f.addRow(self.cb_poly)
        f.addRow("крок параметра u", self.sb_step)
        v.addWidget(g)

        g = QGroupBox("Параметри вибраної дуги (ваги реперних точок)")
        f = QFormLayout(g)
        self.sb_seg = QSpinBox()
        self.sb_seg.setRange(1, len(self.contour))
        self.sb_seg.valueChanged.connect(self._on_seg_spin)
        self.sb_w = [_spin(0.05, 50.0, 1.0, 0.1) for _ in range(4)]
        for k, name in enumerate("ABCD"):
            self.sb_w[k].valueChanged.connect(self._on_weight_changed)
        f.addRow("дуга №", self.sb_seg)
        for k, name in enumerate("ABCD"):
            f.addRow(f"вага w{name}", self.sb_w[k])
        b1 = QPushButton("Скинути ваги цієї дуги (=1)")
        b1.clicked.connect(self._reset_seg_weights)
        b2 = QPushButton("Скинути ваги всіх дуг (=1)")
        b2.clicked.connect(self._reset_all_weights)
        f.addRow(b1)
        f.addRow(b2)
        self.lbl_info = QLabel()
        f.addRow(self.lbl_info)
        v.addWidget(g)

        g = QGroupBox("Анімація переходу в іншу фігуру")
        f = QFormLayout(g)
        self.cmb_target = QComboBox()
        self.cmb_target.addItems(["Трикутник", "Квадрат", "Коло"])
        self.sb_astep = _spin(0.002, 0.2, DEFAULTS["anim_step"], 0.002, 3)
        self.btn_anim = QPushButton("Старт / Стоп анімації")
        self.btn_anim.clicked.connect(self._toggle_anim)
        self.sl_t = QSlider(Qt.Horizontal)
        self.sl_t.setRange(0, 100)
        self.sl_t.valueChanged.connect(self._on_slider)
        self.lbl_t = QLabel("t = 0.00")
        f.addRow("кінцева фігура", self.cmb_target)
        f.addRow("крок t за кадр", self.sb_astep)
        f.addRow(self.btn_anim)
        f.addRow(self.sl_t)
        f.addRow(self.lbl_t)
        v.addWidget(g)

        g = QGroupBox("Евклідові перетворення")
        f = QFormLayout(g)
        self.sb_dx = _spin(-100, 100, 4.0, 0.5)
        self.sb_dy = _spin(-100, 100, -3.0, 0.5)
        bs = QPushButton("Зсув на (dx, dy)")
        bs.clicked.connect(self._shift)
        self.sb_px = _spin(-100, 100, 0.0, 0.5)
        self.sb_py = _spin(-100, 100, 0.0, 0.5)
        self.sb_ang = _spin(-360, 360, 45.0, 5.0)
        for s in (self.sb_px, self.sb_py):
            s.valueChanged.connect(self._on_pivot_spin)
        self.btn_pick = QPushButton("Вибрати центр оберту мишею")
        self.btn_pick.setCheckable(True)
        self.btn_pick.toggled.connect(self.canvas.set_picking_pivot)
        br = QPushButton("Оберт навколо точки (px, py)")
        br.clicked.connect(self._rotate)
        f.addRow("dx", self.sb_dx)
        f.addRow("dy", self.sb_dy)
        f.addRow(bs)
        f.addRow("px", self.sb_px)
        f.addRow("py", self.sb_py)
        f.addRow("кут, °", self.sb_ang)
        f.addRow(self.btn_pick)
        f.addRow(br)
        self.lbl_matrix = QLabel()
        self.lbl_matrix.setStyleSheet("font-family: monospace;")
        self.lbl_matrix.setMinimumHeight(60)
        f.addRow(self.lbl_matrix)
        v.addWidget(g)

        bo = QPushButton("Відновити початковий контур (качка)")
        bo.clicked.connect(self._reset_contour)
        v.addWidget(bo)
        v.addStretch(1)

        inner.setMinimumHeight(1330)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(inner)
        sc.setFixedWidth(400)
        return sc

    # оновлення
    def _redraw(self):
        curves = self.contour.all_curve_points(self.sb_step.value())
        self.canvas.set_contour(self.contour, curves)
        self._refresh_joint_info()

    def _on_edited(self):
        self._redraw()

    def _on_poly_toggled(self, on):
        self.canvas.show_polygon = on
        self.canvas.update()

    # гладкість
    def _refresh_joint_info(self):
        c = self.contour
        self.lbl_counts.setText(
            f"Стикових точок: {len(c.joints)}  (вузлових: {c.smooth_count()}, "
            f"точок зламу: {c.break_count()})")
        i = self.canvas.selected
        lines = [f"Вибрана дуга №{i + 1}:"]
        for k, name in ((0, "A"), (3, "D")):
            info = c.joint_info(i, k)
            if info is None:
                lines.append(f"  кінець {name}: вільний, стику немає")
                continue
            kind = "вузлова точка" if info["smooth"] else "точка зламу"
            ang = "—" if info["angle"] is None else f"{info['angle']:.1f}°"
            lines.append(f"  кінець {name}: стик з дугою №{info['partner'] + 1} — {kind}, "
                         f"кут між ручками {ang}")
        self.lbl_joint.setText("\n".join(lines))

    def _on_joint_toggled(self, j):
        (i1, _k1), (i2, _k2) = self.contour.joints[j]
        kind = ("вузлова точка: гладкість 1-го порядку увімкнено, ручки вирівняно"
                if self.contour.smooth[j] else "точка зламу: гладкість вимкнено")
        self.lbl_event.setText(f"Стик дуг №{i1 + 1} і №{i2 + 1} → {kind}.")
        self._sync_weight_boxes()
        self._redraw()

    def _set_all_joints(self, smooth):
        self.contour.set_all(smooth)
        self.lbl_event.setText("Усі стики → вузлові точки (ручки вирівняно)." if smooth
                               else "Усі стики → точки зламу.")
        self._redraw()

    # ваги
    def _sync_weight_boxes(self):
        i = self.canvas.selected
        for k in range(4):
            self.sb_w[k].blockSignals(True)
            self.sb_w[k].setValue(self.contour.w[i][k])
            self.sb_w[k].blockSignals(False)
        self.sb_seg.blockSignals(True)
        self.sb_seg.setValue(i + 1)
        self.sb_seg.blockSignals(False)
        r = self.contour.pts[i]
        self.lbl_info.setText(
            f"Дуг у контурі: {len(self.contour)}\n"
            f"A=({r[0][0]:.2f}; {r[0][1]:.2f})  B=({r[1][0]:.2f}; {r[1][1]:.2f})\n"
            f"C=({r[2][0]:.2f}; {r[2][1]:.2f})  D=({r[3][0]:.2f}; {r[3][1]:.2f})")
        self._refresh_joint_info()

    def _on_segment_selected(self, i):
        self._sync_weight_boxes()

    def _on_seg_spin(self, n):
        self.canvas.selected = n - 1
        self._sync_weight_boxes()
        self.canvas.update()

    def _on_weight_changed(self):
        i = self.canvas.selected
        for k in range(4):
            self.contour.w[i][k] = self.sb_w[k].value()
        self._redraw()

    def _reset_seg_weights(self):
        self.contour.w[self.canvas.selected] = [1.0] * 4
        self._sync_weight_boxes()
        self._redraw()

    def _reset_all_weights(self):
        self.contour.w = [[1.0] * 4 for _ in self.contour.pts]
        self._sync_weight_boxes()
        self._redraw()

    # анімація
    def _toggle_anim(self):
        if self.timer.isActive():
            self.timer.stop()
            return
        self.base = self.contour.copy()
        self.target = target_shape(self.cmb_target.currentText(), len(self.contour))
        self.t = 0.0
        self.t_dir = 1
        self.canvas.editable = False
        self.timer.start(30)

    def _apply_t(self):
        self.contour = morph(self.base, self.target, self.t)
        self.canvas.contour = self.contour
        self.lbl_t.setText(f"t = {self.t:.2f}")
        self.sl_t.blockSignals(True)
        self.sl_t.setValue(int(round(self.t * 100)))
        self.sl_t.blockSignals(False)
        self._redraw()

    def _tick(self):
        # кадр
        self.t += self.t_dir * self.sb_astep.value()
        if self.t >= 1.0:
            self.t, self.t_dir = 1.0, -1
        elif self.t <= 0.0:
            self.t, self.t_dir = 0.0, 1
        self._apply_t()

    def _on_slider(self, val):
        if self.base is None or self.timer.isActive():
            self.base = self.contour.copy() if self.base is None else self.base
            self.target = self.target or target_shape(self.cmb_target.currentText(), len(self.contour))
        if self.timer.isActive():
            return
        if self.base is None:
            return
        self.canvas.editable = (val == 0)
        self.t = val / 100.0
        self._apply_t()

    # перетворення
    def _apply_matrix(self, m):
        self.contour.transform(m)
        self.base = None
        self.lbl_matrix.setText("M =\n" + "\n".join(
            "  ".join(f"{m.m[i*3+j]:8.3f}" for j in range(3)) for i in range(3)))
        self._sync_weight_boxes()
        self._redraw()

    def _shift(self):
        self._apply_matrix(Mat3.translation(self.sb_dx.value(), self.sb_dy.value()))

    def _rotate(self):
        self._apply_matrix(Mat3.rotation(self.sb_ang.value(), self.sb_px.value(), self.sb_py.value()))

    def _on_pivot_picked(self, x, y):
        self.sb_px.setValue(round(x, 2))
        self.sb_py.setValue(round(y, 2))
        self.btn_pick.setChecked(False)

    def _on_pivot_spin(self):
        self.canvas.pivot = (self.sb_px.value(), self.sb_py.value())
        self.canvas.update()

    def _reset_contour(self):
        self.timer.stop()
        self.contour = self.original.copy()
        self.base = None
        self.target = None
        self.canvas.editable = True
        self.canvas.pivot = None
        self.canvas.focus = None
        self.lbl_event.setText("")
        self.sl_t.blockSignals(True)
        self.sl_t.setValue(0)
        self.sl_t.blockSignals(False)
        self.lbl_t.setText("t = 0.00")
        self._sync_weight_boxes()
        self._redraw()
