import math

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QGroupBox,
    QDoubleSpinBox, QPushButton, QLabel, QScrollArea, QCheckBox, QSlider,
)
from PySide6.QtCore import Qt, QTimer

from geometry import Mat3
from curve import Strophoid
from canvas import Canvas

# ---- набір параметрів за замовчуванням ----
DEFAULTS = dict(
    a=5.0,              # статичний параметр: вузол у (0,0), петля до x = a, асимптота x = -a
    alpha=-1.55,        # початок області визначення (трохи менше -pi/2)
    beta=1.55,          # кінець області визначення (трохи менше pi/2)
    step=0.01,          # крок керуючої змінної phi
    a_min=1.0,          # межі анімації параметра a
    a_max=8.0,
    a_step=0.05,        # приріст a на один кадр анімації
    phi0=math.pi / 6,   # початкова точка для дотичної
)
SAMPLE_EVERY = 10       # кожну 10-ту точку циклу зберігаємо в асоціативний контейнер


def _spin(minv, maxv, value, step=0.1, decimals=2):
    s = QDoubleSpinBox()
    s.setRange(minv, maxv)
    s.setDecimals(decimals)
    s.setSingleStep(step)
    s.setValue(value)
    return s


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Лаб. робота №2 — Побудова чудових кривих (Варіант 5: Строфоїда)")
        self.resize(1500, 900)

        self.curve = Strophoid(DEFAULTS["a"])
        self.total = Mat3.identity()          # накопичена матриця евклідових перетворень
        self.samples = {}                      # map<phi, (x, y)> — як у методичці
        self.keys = []
        self.idx = 0
        self.a_dir = 1                         # напрямок зміни a в анімації

        self.canvas = Canvas()
        self.canvas.point_picked.connect(self._on_pivot_picked)

        self.timer_a = QTimer(self)
        self.timer_a.timeout.connect(self._tick_a)
        self.timer_p = QTimer(self)
        self.timer_p.timeout.connect(self._tick_point)

        central = QWidget()
        self.setCentralWidget(central)
        lay = QHBoxLayout(central)
        lay.addWidget(self._build_panel(), 0)
        lay.addWidget(self.canvas, 1)

        self._rebuild()

    # ================= панель керування =================
    def _build_panel(self):
        inner = QWidget()
        inner.setStyleSheet("QDoubleSpinBox, QPushButton { min-height: 24px; }")
        v = QVBoxLayout(inner)

        # --- параметри кривої ---
        g = QGroupBox("Параметри кривої  r = a·cos2φ / cosφ")
        f = QFormLayout(g)
        self.sb_a = _spin(0.2, 20, DEFAULTS["a"], 0.1)
        self.sb_alpha = _spin(-1.57, 0, DEFAULTS["alpha"], 0.01, 3)
        self.sb_beta = _spin(0, 1.57, DEFAULTS["beta"], 0.01, 3)
        self.sb_step = _spin(0.001, 0.2, DEFAULTS["step"], 0.001, 3)
        for s in (self.sb_a, self.sb_alpha, self.sb_beta, self.sb_step):
            s.valueChanged.connect(self._on_params_changed)
        f.addRow("a (статичний параметр)", self.sb_a)
        f.addRow("α (початок φ, рад)", self.sb_alpha)
        f.addRow("β (кінець φ, рад)", self.sb_beta)
        f.addRow("крок φ", self.sb_step)
        v.addWidget(g)

        # --- анімація параметра a ---
        g = QGroupBox("Анімація (автозміна параметра a)")
        f = QFormLayout(g)
        self.sb_amin = _spin(0.2, 20, DEFAULTS["a_min"], 0.1)
        self.sb_amax = _spin(0.2, 20, DEFAULTS["a_max"], 0.1)
        self.sb_astep = _spin(0.01, 1, DEFAULTS["a_step"], 0.01)
        self.btn_anim = QPushButton("Старт / Стоп анімації a")
        self.btn_anim.clicked.connect(self._toggle_anim)
        f.addRow("a мін", self.sb_amin)
        f.addRow("a макс", self.sb_amax)
        f.addRow("приріст за кадр", self.sb_astep)
        f.addRow(self.btn_anim)
        v.addWidget(g)

        # --- точка кривої, дотична, нормаль, асимптота ---
        g = QGroupBox("Точка кривої, дотична, нормаль, асимптота")
        gl = QVBoxLayout(g)
        row = QHBoxLayout()
        self.btn_prev = QPushButton("<<")
        self.btn_next = QPushButton(">>")
        self.btn_prev.clicked.connect(lambda: self._move_point(-1))
        self.btn_next.clicked.connect(lambda: self._move_point(+1))
        row.addWidget(self.btn_prev)
        row.addWidget(QLabel("Точка кривої"))
        row.addWidget(self.btn_next)
        gl.addLayout(row)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.valueChanged.connect(self._on_slider)
        gl.addWidget(self.slider)
        self.btn_pt_anim = QPushButton("Старт / Стоп анімації точки")
        self.btn_pt_anim.clicked.connect(self._toggle_point_anim)
        gl.addWidget(self.btn_pt_anim)
        self.cb_tan = QCheckBox("Дотична")
        self.cb_nor = QCheckBox("Нормаль")
        self.cb_asy = QCheckBox("Асимптота")
        self.cb_tan.setChecked(True)
        for cb in (self.cb_tan, self.cb_nor, self.cb_asy):
            cb.toggled.connect(self._refresh_scene)
            gl.addWidget(cb)
        v.addWidget(g)

        # --- евклідові перетворення ---
        g = QGroupBox("Евклідові перетворення")
        f = QFormLayout(g)
        self.sb_dx = _spin(-100, 100, 3.0, 0.5)
        self.sb_dy = _spin(-100, 100, 2.0, 0.5)
        btn_shift = QPushButton("Зсув на (dx, dy)")
        btn_shift.clicked.connect(self._apply_shift)
        self.sb_px = _spin(-100, 100, 0.0, 0.5)
        self.sb_py = _spin(-100, 100, 0.0, 0.5)
        self.sb_ang = _spin(-360, 360, 30.0, 5.0)
        self.btn_pick = QPushButton("Вибрати центр оберту мишею")
        self.btn_pick.setCheckable(True)
        self.btn_pick.toggled.connect(self.canvas.set_picking_pivot)
        btn_rot = QPushButton("Оберт навколо точки (px, py)")
        btn_rot.clicked.connect(self._apply_rotation)
        btn_reset = QPushButton("Скинути перетворення")
        btn_reset.clicked.connect(self._reset_transform)
        for s in (self.sb_px, self.sb_py):
            s.valueChanged.connect(self._on_pivot_spin)
        f.addRow("dx", self.sb_dx)
        f.addRow("dy", self.sb_dy)
        f.addRow(btn_shift)
        f.addRow("px", self.sb_px)
        f.addRow("py", self.sb_py)
        f.addRow("кут, °", self.sb_ang)
        f.addRow(self.btn_pick)
        f.addRow(btn_rot)
        f.addRow(btn_reset)
        self.lbl_matrix = QLabel()
        self.lbl_matrix.setStyleSheet("font-family: monospace;")
        self.lbl_matrix.setMinimumHeight(60)
        f.addRow(self.lbl_matrix)
        v.addWidget(g)

        # --- результати розрахунків ---
        g = QGroupBox("Розрахунки")
        gl = QVBoxLayout(g)
        self.lbl_info = QLabel()
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setMinimumHeight(400)
        self.lbl_info.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.lbl_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        gl.addWidget(self.lbl_info)
        v.addWidget(g)

        btn_defaults = QPushButton("Скинути все до значень за замовчуванням")
        btn_defaults.clicked.connect(self._reset_all)
        v.addWidget(btn_defaults)
        v.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        scroll.setFixedWidth(400)
        inner.setMinimumHeight(1260)
        return scroll

    # ================= побудова =================
    def _on_params_changed(self):
        self.curve.a = self.sb_a.value()
        self._rebuild()

    def _rebuild(self):
        """Цикл побудови: обчислюємо точки кривої та зберігаємо кожну N-ту
        в асоціативному контейнері phi -> (x, y)."""
        alpha, beta, step = self.sb_alpha.value(), self.sb_beta.value(), self.sb_step.value()
        self.points = self.curve.build_points(alpha, beta, step)
        self.samples = {}
        for i, (phi, x, y) in enumerate(self.points):
            if i % SAMPLE_EVERY == 0:
                self.samples[phi] = (x, y)
        self.keys = sorted(self.samples.keys())

        # зберігаємо положення точки дотику при зміні параметрів
        if not hasattr(self, "_phi_cur"):
            self._phi_cur = DEFAULTS["phi0"]
        self.slider.blockSignals(True)
        self.slider.setRange(0, len(self.keys) - 1)
        self.idx = min(range(len(self.keys)), key=lambda i: abs(self.keys[i] - self._phi_cur))
        self.slider.setValue(self.idx)
        self.slider.blockSignals(False)
        self._refresh_scene()

    def _phi(self):
        return self.keys[self.idx]

    def _refresh_scene(self):
        phi = self._phi()
        self._phi_cur = phi
        a = self.curve.a
        pts = [(x, y) for (_, x, y) in self.points]
        tan = self.curve.tangent_segment(phi, 2.0 * a) if self.cb_tan.isChecked() else None
        nor = self.curve.normal_segment(phi, 2.0 * a) if self.cb_nor.isChecked() else None
        asy = self.curve.asymptote_segment(80.0 * a) if self.cb_asy.isChecked() else None
        cp = self.curve.point(phi)
        self.canvas.set_scene(pts, tan, nor, asy, cp, f"a = {a:.2f}")
        self.canvas.set_transform(self.total)
        self._refresh_info()

    def _refresh_info(self):
        c = self.curve
        phi = self._phi()
        x0, y0 = c.point(phi)
        xt, yt = self.total.apply(x0, y0)
        k = c.curvature(phi)
        d2 = c.second_derivative(phi)
        slope = c.slope(phi)
        infl = c.inflection_points(self.sb_alpha.value(), self.sb_beta.value(), 800)
        L_range = c.arc_length(self.sb_alpha.value(), self.sb_beta.value(), 4000)
        txt = (
            f"<b>Точка кривої</b>: φ = {phi:.3f} рад ({math.degrees(phi):.1f}°)<br>"
            f"(x, y) = ({x0:.3f}, {y0:.3f}); на сцені після перетворень: ({xt:.3f}, {yt:.3f})<br>"
            f"f′(φ) = dy/dx = {'∞ (вертикальна)' if slope is None else f'{slope:.4f}'}<br>"
            f"f″ = d²y/dx² = {'—' if d2 is None else f'{d2:.4f}'}<br>"
            f"<b>Дотична</b>: {c.tangent_equation(phi)}<br>"
            f"<b>Нормаль</b>: {c.normal_equation(phi)}<br>"
            f"<b>Асимптота</b>: x = {c.asymptote_x():.3f}<br>"
            f"<b>Кривина</b> k = {k:.4f}; радіус кривини R = {c.curvature_radius(phi):.4f}<br>"
            f"<b>Точки перегину</b>: {'немає (k не змінює знак)' if not infl else ', '.join(f'{p:.3f}' for p in infl)}<br>"
            f"<b>Довжина петлі</b> L = {c.loop_length():.4f} (≈ 2.4896·a)<br>"
            f"<b>Довжина дуги</b> на [α, β] = {L_range:.4f}<br>"
            f"<b>Площа петлі</b> S = {c.loop_area_numeric():.4f} (формула a²(2−π/2) = {c.loop_area_exact():.4f})<br>"
            f"<b>Площа між асимптотою і кривою</b> S = {c.area_between_numeric():.4f} "
            f"(формула a²(2+π/2) = {c.area_between_exact():.4f})"
        )
        self.lbl_info.setText(txt)
        m = self.total.m
        self.lbl_matrix.setText(
            "M =\n" + "\n".join("  ".join(f"{m[i*3+j]:8.3f}" for j in range(3)) for i in range(3))
        )

    # ================= точка кривої =================
    def _on_slider(self, v):
        self.idx = v
        self._refresh_scene()

    def _move_point(self, d):
        self.idx = max(0, min(len(self.keys) - 1, self.idx + d))
        self.slider.blockSignals(True)
        self.slider.setValue(self.idx)
        self.slider.blockSignals(False)
        self._refresh_scene()

    def _toggle_point_anim(self):
        if self.timer_p.isActive():
            self.timer_p.stop()
        else:
            self.timer_p.start(80)

    def _tick_point(self):
        self.idx = (self.idx + 1) % len(self.keys)
        self.slider.blockSignals(True)
        self.slider.setValue(self.idx)
        self.slider.blockSignals(False)
        self._refresh_scene()

    # ================= анімація параметра a =================
    def _toggle_anim(self):
        if self.timer_a.isActive():
            self.timer_a.stop()
        else:
            self.timer_a.start(30)

    def _tick_a(self):
        """Кадр анімації: змінюємо a на a_step, при досягненні межі міняємо
        напрямок; потім перераховуємо криву та перемальовуємо сцену."""
        a_min, a_max, st = self.sb_amin.value(), self.sb_amax.value(), self.sb_astep.value()
        a = self.curve.a + self.a_dir * st
        if a >= a_max:
            a, self.a_dir = a_max, -1
        elif a <= a_min:
            a, self.a_dir = a_min, +1
        self.sb_a.blockSignals(True)
        self.sb_a.setValue(a)
        self.sb_a.blockSignals(False)
        self.curve.a = a
        self._rebuild()

    # ================= евклідові перетворення =================
    def _compose(self, m):
        self.total = m.multiply(self.total)
        self._refresh_scene()

    def _apply_shift(self):
        self._compose(Mat3.translation(self.sb_dx.value(), self.sb_dy.value()))

    def _apply_rotation(self):
        self._compose(Mat3.rotation(self.sb_ang.value(), self.sb_px.value(), self.sb_py.value()))

    def _reset_transform(self):
        self.total = Mat3.identity()
        self._refresh_scene()

    def _on_pivot_picked(self, x, y):
        self.sb_px.setValue(round(x, 2))
        self.sb_py.setValue(round(y, 2))
        self.btn_pick.setChecked(False)

    def _on_pivot_spin(self):
        self.canvas.set_pivot((self.sb_px.value(), self.sb_py.value()))

    def _reset_all(self):
        self.timer_a.stop()
        self.timer_p.stop()
        for s, v in ((self.sb_a, DEFAULTS["a"]), (self.sb_alpha, DEFAULTS["alpha"]),
                     (self.sb_beta, DEFAULTS["beta"]), (self.sb_step, DEFAULTS["step"])):
            s.blockSignals(True)
            s.setValue(v)
            s.blockSignals(False)
        self.curve.a = DEFAULTS["a"]
        self._phi_cur = DEFAULTS["phi0"]
        self.total = Mat3.identity()
        self.canvas.set_pivot(None)
        self._rebuild()
