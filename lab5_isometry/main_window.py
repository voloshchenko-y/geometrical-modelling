from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QGroupBox,
    QDoubleSpinBox, QSpinBox, QPushButton, QLabel, QScrollArea, QCheckBox, QComboBox,
)
from PySide6.QtCore import QTimer

from body import DEFAULTS
from canvas import Canvas
from geometry3d import BETA_CHOICES
from scene import Scene

# параметри анімації
ANIM_PARAMS = {
    "Висота": ("height", 30.0, 120.0, 1.5),
    "Ширина": ("width", 30.0, 100.0, 1.0),
    "Глибина": ("depth", 30.0, 100.0, 1.0),
    "Масштаб": ("scale", 0.5, 2.0, 0.02),
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
        self.setWindowTitle("Лаб. робота №5 — Проекціювання (Варіант 5: ізометрія на площину z = 0, "
                            "зірчаста призма)")
        self.resize(1500, 950)

        self.scene = Scene()
        self.canvas = Canvas(self.scene)
        self.anim_dir = 1
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

        central = QWidget()
        self.setCentralWidget(central)
        lay = QHBoxLayout(central)
        lay.addWidget(self._panel(), 0)
        lay.addWidget(self.canvas, 1)
        self._on_anim_param()
        self._refresh()

    # панель
    def _panel(self):
        inner = QWidget()
        inner.setStyleSheet("QDoubleSpinBox, QSpinBox, QPushButton, QComboBox { min-height: 24px; }")
        v = QVBoxLayout(inner)

        # тіло
        g = QGroupBox("Параметри гранованого тіла (зірчаста призма)")
        f = QFormLayout(g)
        self.sb_h = _spin(5, 300, DEFAULTS["height"], 5.0)
        self.sb_w = _spin(5, 300, DEFAULTS["width"], 5.0)
        self.sb_d = _spin(5, 300, DEFAULTS["depth"], 5.0)
        self.sb_n = QSpinBox()
        self.sb_n.setRange(3, 12)
        self.sb_n.setValue(DEFAULTS["n"])
        self.sb_ratio = _spin(0.1, 0.95, DEFAULTS["ratio"], 0.05)
        self.sb_scale = _spin(0.2, 4.0, DEFAULTS["scale"], 0.1)
        for sb in (self.sb_h, self.sb_w, self.sb_d, self.sb_n, self.sb_ratio, self.sb_scale):
            sb.valueChanged.connect(self._on_body_changed)
        f.addRow("висота (вісь Y)", self.sb_h)
        f.addRow("ширина (вісь X)", self.sb_w)
        f.addRow("глибина (вісь Z)", self.sb_d)
        f.addRow("кількість променів", self.sb_n)
        f.addRow("відношення радіусів r/R", self.sb_ratio)
        f.addRow("масштаб", self.sb_scale)
        v.addWidget(g)

        # перетворення
        g = QGroupBox("Евклідові перетворення")
        f = QFormLayout(g)
        self.sb_tx = _spin(-1000, 1000, 100.0, 10.0)
        self.sb_ty = _spin(-1000, 1000, 100.0, 10.0)
        self.sb_tz = _spin(-1000, 1000, 0.0, 10.0)
        self.sb_rx = _spin(-360, 360, 0.0, 5.0)
        self.sb_ry = _spin(-360, 360, 90.0, 5.0)
        self.sb_rz = _spin(-360, 360, 0.0, 5.0)
        self.sb_px = _spin(-300, 300, 0.0, 5.0)
        self.sb_py = _spin(-300, 300, 0.0, 5.0)
        self.sb_pz = _spin(-300, 300, 0.0, 5.0)
        for sb in (self.sb_px, self.sb_py, self.sb_pz):
            sb.valueChanged.connect(self._on_pivot_changed)
        f.addRow(QLabel("Зсув фігури (додається до поточного):"))
        f.addRow("по X", self.sb_tx)
        f.addRow("по Y", self.sb_ty)
        f.addRow("по Z", self.sb_tz)
        f.addRow(QLabel("Оберт навколо власної осі, ° (додається):"))
        f.addRow("навколо X", self.sb_rx)
        f.addRow("навколо Y", self.sb_ry)
        f.addRow("навколо Z", self.sb_rz)
        f.addRow(QLabel("Центр обертання — точка всередині фігури;\nзміщення відносно центра тіла:"))
        f.addRow("Δx", self.sb_px)
        f.addRow("Δy", self.sb_py)
        f.addRow("Δz", self.sb_pz)
        b_apply = QPushButton("Застосувати")
        b_apply.clicked.connect(self._apply)
        b_reset = QPushButton("Скинути положення (Default)")
        b_reset.clicked.connect(self._reset_pose)
        f.addRow(b_apply)
        f.addRow(b_reset)
        self.lbl_pose = QLabel()
        self.lbl_pose.setWordWrap(True)
        f.addRow(self.lbl_pose)
        v.addWidget(g)

        # анімація
        g = QGroupBox("Анімація: зміна параметра тіла + зсув/оберт за кадр")
        f = QFormLayout(g)
        self.cmb_param = QComboBox()
        self.cmb_param.addItems(list(ANIM_PARAMS))
        self.cmb_param.currentIndexChanged.connect(self._on_anim_param)
        self.sb_amin = _spin(0.01, 1000, 30.0, 1.0)
        self.sb_amax = _spin(0.01, 1000, 120.0, 1.0)
        self.sb_astep = _spin(0.001, 100, 1.5, 0.5, 3)
        self.sb_adx = _spin(-100, 100, 1.0, 0.5)
        self.sb_ady = _spin(-100, 100, 0.0, 0.5)
        self.sb_adz = _spin(-100, 100, 0.0, 0.5)
        self.sb_aax = _spin(-90, 90, 0.0, 0.5)
        self.sb_aay = _spin(-90, 90, 2.0, 0.5)
        self.sb_aaz = _spin(-90, 90, 0.0, 0.5)
        self.btn_anim = QPushButton("Старт / Стоп анімації")
        self.btn_anim.clicked.connect(self._toggle_anim)
        f.addRow("параметр", self.cmb_param)
        f.addRow("мінімум", self.sb_amin)
        f.addRow("максимум", self.sb_amax)
        f.addRow("крок за кадр", self.sb_astep)
        f.addRow(QLabel("Зсув за кадр (туди й назад разом із параметром):"))
        f.addRow("Δx", self.sb_adx)
        f.addRow("Δy", self.sb_ady)
        f.addRow("Δz", self.sb_adz)
        f.addRow(QLabel("Оберт за кадр, ° (безперервний):"))
        f.addRow("навколо X", self.sb_aax)
        f.addRow("навколо Y", self.sb_aay)
        f.addRow("навколо Z", self.sb_aaz)
        f.addRow(self.btn_anim)
        v.addWidget(g)

        # проекція
        g = QGroupBox("Параметри проекціювання: ізометрія на площину z = 0")
        f = QFormLayout(g)
        self.cmb_beta = QComboBox()
        for b in BETA_CHOICES:
            self.cmb_beta.addItem(f"β = {b:+.0f}°", b)
        self.cmb_alpha = QComboBox()
        self.cmb_alpha.addItem("α = +35,264°", +1)
        self.cmb_alpha.addItem("α = −35,264°", -1)
        self.cb_practical = QCheckBox("приведена ізометрія (осі в масштабі 1,0)")
        self.cmb_beta.currentIndexChanged.connect(self._on_view_changed)
        self.cmb_alpha.currentIndexChanged.connect(self._on_view_changed)
        self.cb_practical.toggled.connect(self._on_view_changed)
        f.addRow("кут β (навколо Y)", self.cmb_beta)
        f.addRow("кут α (навколо X)", self.cmb_alpha)
        f.addRow(self.cb_practical)
        self.lbl_view = QLabel()
        self.lbl_view.setStyleSheet("font-family: monospace;")
        f.addRow(self.lbl_view)
        v.addWidget(g)

        # вигляд
        g = QGroupBox("Вигляд")
        f = QFormLayout(g)
        self.cb_axes = QCheckBox("осі координат")
        self.cb_axes.setChecked(True)
        self.cb_axes.toggled.connect(self._on_show)
        self.cb_pivot = QCheckBox("центр обертання")
        self.cb_pivot.setChecked(True)
        self.cb_pivot.toggled.connect(self._on_show)
        b_view = QPushButton("Скинути масштаб і зсув полотна")
        b_view.clicked.connect(self.canvas.reset_view)
        b_all = QPushButton("Скинути все до значень за замовчуванням")
        b_all.clicked.connect(self._reset_all)
        f.addRow(self.cb_axes)
        f.addRow(self.cb_pivot)
        f.addRow(b_view)
        f.addRow(b_all)
        v.addWidget(g)
        v.addStretch(1)

        inner.setMinimumHeight(1700)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(inner)
        sc.setFixedWidth(400)
        return sc

    # оновлення
    def _refresh(self):
        s = self.scene
        self.lbl_pose.setText(
            f"Положення: x = {s.pos[0]:.1f}, y = {s.pos[1]:.1f}, z = {s.pos[2]:.1f}\n"
            f"Кути: X = {s.ang[0]:.1f}°, Y = {s.ang[1]:.1f}°, Z = {s.ang[2]:.1f}°")
        info = s.view_info()
        m = s.view_matrix().m
        rows = "\n".join("  ".join(f"{m[i * 4 + j]:7.3f}" for j in range(4)) for i in range(4))
        fx, fy, fz = info["factors"]
        self.lbl_view.setText(
            f"α = {info['alpha']:.3f}°, β = {info['beta']:.0f}°\n"
            f"спотворення: Ux = {fx:.4f}, Uy = {fy:.4f}, Uz = {fz:.4f}\n"
            f"M =\n{rows}")
        self.canvas.update()

    def _sync_body_spins(self):
        b = self.scene.body
        for sb, val in ((self.sb_h, b.height), (self.sb_w, b.width), (self.sb_d, b.depth),
                        (self.sb_n, b.n), (self.sb_ratio, b.ratio), (self.sb_scale, b.scale)):
            sb.blockSignals(True)
            sb.setValue(val)
            sb.blockSignals(False)

    # тіло
    def _on_body_changed(self):
        b = self.scene.body
        b.height = self.sb_h.value()
        b.width = self.sb_w.value()
        b.depth = self.sb_d.value()
        b.n = self.sb_n.value()
        b.ratio = self.sb_ratio.value()
        b.scale = self.sb_scale.value()
        self._refresh()

    # перетворення
    def _apply(self):
        self.scene.apply_offsets(
            (self.sb_tx.value(), self.sb_ty.value(), self.sb_tz.value()),
            (self.sb_rx.value(), self.sb_ry.value(), self.sb_rz.value()))
        self._refresh()

    def _reset_pose(self):
        self.scene.reset_pose()
        self._refresh()

    def _on_pivot_changed(self):
        self.scene.pivot_offset = [self.sb_px.value(), self.sb_py.value(), self.sb_pz.value()]
        self._refresh()

    # анімація
    def _on_anim_param(self):
        _attr, lo, hi, st = ANIM_PARAMS[self.cmb_param.currentText()]
        for sb, val in ((self.sb_amin, lo), (self.sb_amax, hi), (self.sb_astep, st)):
            sb.setValue(val)

    def _toggle_anim(self):
        if self.timer.isActive():
            self.timer.stop()
            return
        attr = ANIM_PARAMS[self.cmb_param.currentText()][0]
        lo, hi = self.sb_amin.value(), self.sb_amax.value()
        setattr(self.scene.body, attr, min(max(getattr(self.scene.body, attr), lo), hi))
        self.anim_dir = 1
        self.timer.start(30)

    def _tick(self):
        # кадр
        attr = ANIM_PARAMS[self.cmb_param.currentText()][0]
        lo, hi, st = self.sb_amin.value(), self.sb_amax.value(), self.sb_astep.value()
        v = getattr(self.scene.body, attr) + self.anim_dir * st
        if v >= hi:
            v, self.anim_dir = hi, -1
        elif v <= lo:
            v, self.anim_dir = lo, 1
        setattr(self.scene.body, attr, v)
        d = self.anim_dir
        self.scene.apply_offsets(
            (self.sb_adx.value() * d, self.sb_ady.value() * d, self.sb_adz.value() * d),
            (self.sb_aax.value(), self.sb_aay.value(), self.sb_aaz.value()))
        self._sync_body_spins()
        self._refresh()

    # проекція
    def _on_view_changed(self):
        self.scene.beta = self.cmb_beta.currentData()
        self.scene.alpha_sign = self.cmb_alpha.currentData()
        self.scene.practical = self.cb_practical.isChecked()
        self._refresh()

    def _on_show(self):
        self.canvas.show_axes = self.cb_axes.isChecked()
        self.canvas.show_pivot = self.cb_pivot.isChecked()
        self.canvas.update()

    def _reset_all(self):
        self.timer.stop()
        self.scene.body.reset()
        self.scene.reset_pose()
        self.scene.pivot_offset = [0.0, 0.0, 0.0]
        for sb in (self.sb_px, self.sb_py, self.sb_pz):
            sb.blockSignals(True)
            sb.setValue(0.0)
            sb.blockSignals(False)
        self._sync_body_spins()
        for w in (self.cmb_beta, self.cmb_alpha, self.cb_practical):
            w.blockSignals(True)
        self.cmb_beta.setCurrentIndex(0)
        self.cmb_alpha.setCurrentIndex(0)
        self.cb_practical.setChecked(False)
        for w in (self.cmb_beta, self.cmb_alpha, self.cb_practical):
            w.blockSignals(False)
        self._on_view_changed()
        self.canvas.reset_view()
