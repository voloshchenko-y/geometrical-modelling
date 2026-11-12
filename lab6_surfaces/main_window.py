from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QGroupBox, QGridLayout,
    QDoubleSpinBox, QPushButton, QLabel, QScrollArea, QCheckBox, QComboBox,
)
from PySide6.QtCore import Qt, QTimer

from canvas import Canvas
from geometry3d import BETA_CHOICES
from scene import Scene, SCALE0
from surface import DEFAULTS

# параметри анімації
ANIM = {
    "A": (15.0, 45.0, 0.4, True),
    "B": (15.0, 45.0, 0.4, False),
    "C": (15.0, 60.0, 0.5, True),
}


def _spin(lo, hi, val, step=1.0, dec=2):
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(dec)
    s.setSingleStep(step)
    s.setValue(val)
    return s


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Лаб. робота №6 — Поверхні (Варіант 5: гіперболічний параболоїд, "
                            "контур з ЛР-3, ізометрія з ЛР-5)")
        self.resize(1500, 950)

        self.scene = Scene()
        self.canvas = Canvas(self.scene)
        self.dirs = {k: 1 for k in ANIM}
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

        central = QWidget()
        self.setCentralWidget(central)
        lay = QHBoxLayout(central)
        lay.addWidget(self._panel(), 0)
        lay.addWidget(self.canvas, 1)
        self._refresh()

    # панель
    def _panel(self):
        inner = QWidget()
        inner.setStyleSheet("QDoubleSpinBox, QPushButton, QComboBox { min-height: 24px; }")
        v = QVBoxLayout(inner)

        # поверхня
        g = QGroupBox("Поверхня: x = A·v·ch u,  y = B·v·sh u,  z = C·u²")
        f = QFormLayout(g)
        self.sb_A = _spin(1, 100, DEFAULTS["A"], 1.0)
        self.sb_B = _spin(1, 100, DEFAULTS["B"], 1.0)
        self.sb_C = _spin(1, 100, DEFAULTS["C"], 1.0)
        self.sb_u0 = _spin(-4, 0, DEFAULTS["u_min"], 0.1)
        self.sb_u1 = _spin(0, 4, DEFAULTS["u_max"], 0.1)
        self.sb_v0 = _spin(-4, 0, DEFAULTS["v_min"], 0.1)
        self.sb_v1 = _spin(0, 4, DEFAULTS["v_max"], 0.1)
        self.sb_mesh = _spin(0.03, 0.5, DEFAULTS["mesh"], 0.01)
        for sb in (self.sb_A, self.sb_B, self.sb_C, self.sb_u0, self.sb_u1, self.sb_v0, self.sb_v1,
                   self.sb_mesh):
            sb.valueChanged.connect(self._on_surface_changed)
        f.addRow("параметр A", self.sb_A)
        f.addRow("параметр B", self.sb_B)
        f.addRow("параметр C", self.sb_C)
        f.addRow("u від", self.sb_u0)
        f.addRow("u до", self.sb_u1)
        f.addRow("v від", self.sb_v0)
        f.addRow("v до", self.sb_v1)
        f.addRow("крок UV-сітки", self.sb_mesh)
        v.addWidget(g)

        # контур
        g = QGroupBox("Криволінійний контур (ЛР-3) в UV-сітці")
        f = QFormLayout(g)
        self.sb_cscale = _spin(0.1, 6.0, SCALE0, 0.1)
        self.sb_cscale.valueChanged.connect(self._on_cscale)
        self.sb_cdu = _spin(-3, 3, 0.2, 0.1)
        self.sb_cdv = _spin(-3, 3, 0.0, 0.1)
        self.sb_cang = _spin(-360, 360, 45.0, 5.0)
        b_ca = QPushButton("Застосувати до контуру")
        b_ca.clicked.connect(self._apply_contour)
        b_cr = QPushButton("Скинути контур")
        b_cr.clicked.connect(self._reset_contour)
        self.lbl_contour = QLabel()
        self.lbl_contour.setWordWrap(True)
        f.addRow("масштаб контуру", self.sb_cscale)
        f.addRow(QLabel("Зсув і оберт навколо себе (додаються):"))
        f.addRow("зсув ΔU", self.sb_cdu)
        f.addRow("зсув ΔV", self.sb_cdv)
        f.addRow("кут, °", self.sb_cang)
        f.addRow(b_ca)
        f.addRow(b_cr)
        f.addRow(self.lbl_contour)
        v.addWidget(g)

        # евклідові перетворення поверхні
        g = QGroupBox("Евклідові перетворення поверхні")
        f = QFormLayout(g)
        self.sb_tx = _spin(-1000, 1000, 40.0, 10.0)
        self.sb_ty = _spin(-1000, 1000, 0.0, 10.0)
        self.sb_tz = _spin(-1000, 1000, 0.0, 10.0)
        self.sb_rx = _spin(-360, 360, 0.0, 5.0)
        self.sb_ry = _spin(-360, 360, 45.0, 5.0)
        self.sb_rz = _spin(-360, 360, 0.0, 5.0)
        b_ap = QPushButton("Застосувати до поверхні")
        b_ap.clicked.connect(self._apply)
        b_rs = QPushButton("Скинути положення поверхні")
        b_rs.clicked.connect(self._reset_pose)
        self.lbl_pose = QLabel()
        self.lbl_pose.setWordWrap(True)
        f.addRow(QLabel("Зсув (додається до поточного):"))
        f.addRow("по X", self.sb_tx)
        f.addRow("по Y", self.sb_ty)
        f.addRow("по Z", self.sb_tz)
        f.addRow(QLabel("Оберт навколо власної осі через центр, °:"))
        f.addRow("навколо X", self.sb_rx)
        f.addRow("навколо Y", self.sb_ry)
        f.addRow("навколо Z", self.sb_rz)
        f.addRow(b_ap)
        f.addRow(b_rs)
        f.addRow(self.lbl_pose)
        v.addWidget(g)

        # анімація
        g = QGroupBox("Анімація параметрів поверхні")
        grid = QGridLayout(g)
        for col, t in enumerate(("", "мін", "макс", "крок")):
            grid.addWidget(QLabel(t), 0, col)
        self.anim_cb, self.anim_min, self.anim_max, self.anim_step = {}, {}, {}, {}
        for row, (name, (lo, hi, st, on)) in enumerate(ANIM.items(), start=1):
            cb = QCheckBox(name)
            cb.setChecked(on)
            self.anim_cb[name] = cb
            self.anim_min[name] = _spin(1, 100, lo, 1.0)
            self.anim_max[name] = _spin(1, 100, hi, 1.0)
            self.anim_step[name] = _spin(0.01, 10, st, 0.1)
            for sb in (self.anim_min[name], self.anim_max[name], self.anim_step[name]):
                sb.setButtonSymbols(QDoubleSpinBox.NoButtons)
            grid.addWidget(cb, row, 0)
            grid.addWidget(self.anim_min[name], row, 1)
            grid.addWidget(self.anim_max[name], row, 2)
            grid.addWidget(self.anim_step[name], row, 3)
        self.btn_anim = QPushButton("Старт / Стоп анімації")
        self.btn_anim.clicked.connect(self._toggle_anim)
        grid.addWidget(self.btn_anim, 4, 0, 1, 4)
        v.addWidget(g)

        # проекція
        g = QGroupBox("Проекціювання (ЛР-5): ізометрія на площину z = 0")
        f = QFormLayout(g)
        self.cmb_beta = QComboBox()
        for b in BETA_CHOICES:
            self.cmb_beta.addItem(f"β = {b:+.0f}°", b)
        self.cmb_alpha = QComboBox()
        self.cmb_alpha.addItem("α = +35,264°", +1)
        self.cmb_alpha.addItem("α = −35,264°", -1)
        self.cb_practical = QCheckBox("приведена ізометрія (масштаб осей 1,0)")
        self.cmb_beta.currentIndexChanged.connect(self._on_view_changed)
        self.cmb_alpha.currentIndexChanged.connect(self._on_view_changed)
        self.cb_practical.toggled.connect(self._on_view_changed)
        self.lbl_view = QLabel()
        self.lbl_view.setStyleSheet("font-family: monospace;")
        f.addRow("кут β (навколо Y)", self.cmb_beta)
        f.addRow("кут α (навколо X)", self.cmb_alpha)
        f.addRow(self.cb_practical)
        f.addRow(self.lbl_view)
        v.addWidget(g)

        # вигляд
        g = QGroupBox("Вигляд")
        f = QFormLayout(g)
        self.cb_axes = QCheckBox("осі координат")
        self.cb_mesh = QCheckBox("UV-сітка поверхні")
        self.cb_cont = QCheckBox("криволінійний контур")
        self.cb_piv = QCheckBox("центри: поверхні (червоний), контуру (синій)")
        for cb in (self.cb_axes, self.cb_mesh, self.cb_cont, self.cb_piv):
            cb.setChecked(True)
            cb.toggled.connect(self._on_show)
        b_view = QPushButton("Скинути масштаб і зсув полотна")
        b_view.clicked.connect(self.canvas.reset_view)
        b_all = QPushButton("Скинути все до значень за замовчуванням")
        b_all.clicked.connect(self._reset_all)
        for w in (self.cb_axes, self.cb_mesh, self.cb_cont, self.cb_piv, b_view, b_all):
            f.addRow(w)
        v.addWidget(g)
        v.addStretch(1)

        inner.setMinimumHeight(2050)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(inner)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sc.setFixedWidth(420)
        return sc

    # оновлення
    def _refresh(self):
        s = self.scene
        self.lbl_pose.setText(
            f"Положення: x = {s.pos[0]:.1f}, y = {s.pos[1]:.1f}, z = {s.pos[2]:.1f}\n"
            f"Кути: X = {s.ang[0]:.1f}°, Y = {s.ang[1]:.1f}°, Z = {s.ang[2]:.1f}°")
        pu, pv = s.contour_pivot_uv()
        self.lbl_contour.setText(f"Центр контуру в UV: u = {pu:.2f}, v = {pv:.2f}; "
                                 f"кут = {s.c_angle:.1f}°")
        info = s.view_info()
        m = s.view_matrix().m
        rows = "\n".join("  ".join(f"{m[i * 4 + j]:7.3f}" for j in range(4)) for i in range(4))
        fx, fy, fz = info["factors"]
        self.lbl_view.setText(
            f"α = {info['alpha']:.3f}°, β = {info['beta']:.0f}°\n"
            f"спотворення: Ux = {fx:.4f}, Uy = {fy:.4f}, Uz = {fz:.4f}\n"
            f"M =\n{rows}")
        self.canvas.update()

    def _sync_surface_spins(self):
        s = self.scene.surface
        for sb, val in ((self.sb_A, s.A), (self.sb_B, s.B), (self.sb_C, s.C), (self.sb_u0, s.u_min),
                        (self.sb_u1, s.u_max), (self.sb_v0, s.v_min), (self.sb_v1, s.v_max),
                        (self.sb_mesh, s.mesh)):
            sb.blockSignals(True)
            sb.setValue(val)
            sb.blockSignals(False)

    # поверхня
    def _on_surface_changed(self):
        s = self.scene.surface
        s.A, s.B, s.C = self.sb_A.value(), self.sb_B.value(), self.sb_C.value()
        s.u_min, s.u_max = self.sb_u0.value(), self.sb_u1.value()
        s.v_min, s.v_max = self.sb_v0.value(), self.sb_v1.value()
        s.mesh = self.sb_mesh.value()
        self._refresh()

    def _apply(self):
        self.scene.apply_offsets(
            (self.sb_tx.value(), self.sb_ty.value(), self.sb_tz.value()),
            (self.sb_rx.value(), self.sb_ry.value(), self.sb_rz.value()))
        self._refresh()

    def _reset_pose(self):
        self.scene.reset_pose()
        self._refresh()

    # контур
    def _on_cscale(self):
        self.scene.c_scale = self.sb_cscale.value()
        self._refresh()

    def _apply_contour(self):
        self.scene.apply_contour(self.sb_cdu.value(), self.sb_cdv.value(), self.sb_cang.value())
        self._refresh()

    def _reset_contour(self):
        self.scene.reset_contour()
        self.sb_cscale.blockSignals(True)
        self.sb_cscale.setValue(self.scene.c_scale)
        self.sb_cscale.blockSignals(False)
        self._refresh()

    # анімація
    def _toggle_anim(self):
        if self.timer.isActive():
            self.timer.stop()
            return
        s = self.scene.surface
        for name in ANIM:
            lo, hi = self.anim_min[name].value(), self.anim_max[name].value()
            setattr(s, name, min(max(getattr(s, name), lo), hi))
            self.dirs[name] = 1
        self.timer.start(30)

    def _tick(self):
        # кадр
        s = self.scene.surface
        for name in ANIM:
            if not self.anim_cb[name].isChecked():
                continue
            lo, hi = self.anim_min[name].value(), self.anim_max[name].value()
            val = getattr(s, name) + self.dirs[name] * self.anim_step[name].value()
            if val >= hi:
                val, self.dirs[name] = hi, -1
            elif val <= lo:
                val, self.dirs[name] = lo, 1
            setattr(s, name, val)
        self._sync_surface_spins()
        self._refresh()

    # проекція, вигляд
    def _on_view_changed(self):
        self.scene.beta = self.cmb_beta.currentData()
        self.scene.alpha_sign = self.cmb_alpha.currentData()
        self.scene.practical = self.cb_practical.isChecked()
        self._refresh()

    def _on_show(self):
        c = self.canvas
        c.show_axes = self.cb_axes.isChecked()
        c.show_mesh = self.cb_mesh.isChecked()
        c.show_contour = self.cb_cont.isChecked()
        c.show_pivot = self.cb_piv.isChecked()
        c.update()

    def _reset_all(self):
        self.timer.stop()
        self.scene.surface.reset()
        self.scene.reset_pose()
        self.scene.reset_contour()
        self.sb_cscale.blockSignals(True)
        self.sb_cscale.setValue(self.scene.c_scale)
        self.sb_cscale.blockSignals(False)
        self._sync_surface_spins()
        for w in (self.cmb_beta, self.cmb_alpha, self.cb_practical):
            w.blockSignals(True)
        self.cmb_beta.setCurrentIndex(0)
        self.cmb_alpha.setCurrentIndex(0)
        self.cb_practical.setChecked(False)
        for w in (self.cmb_beta, self.cmb_alpha, self.cb_practical):
            w.blockSignals(False)
        self._on_view_changed()
        self.canvas.reset_view()
