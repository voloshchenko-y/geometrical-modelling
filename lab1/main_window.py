from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QGroupBox,
    QDoubleSpinBox, QPushButton, QTabWidget, QLabel, QScrollArea, QGridLayout,
    QCheckBox,
)
from PySide6.QtCore import Qt

from geometry import Mat3, PartParams, build_part_polygons, bounding_box
from canvas import Canvas


def _spinbox(minv, maxv, value, step=0.5, decimals=2):
    sb = QDoubleSpinBox()
    sb.setRange(minv, maxv)
    sb.setValue(value)
    sb.setSingleStep(step)
    sb.setDecimals(decimals)
    return sb


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "Лаб. робота №1 — Лінійні перетворення (Варіант 5)"
        )
        self.resize(1500, 900)

        self.params = PartParams()
        self.transform_stack = [Mat3.identity()]

        self.canvas = Canvas()
        self.canvas.point_picked.connect(self._on_point_picked)
        self._active_pivot_target = None  # (px_spin, py_spin) currently being picked

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        param_panel = self._build_param_panel()
        self._rebuild_geometry()

        layout.addWidget(param_panel, 0)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self._build_transform_panel(), 0)

    # Parameter panel (shape editing -> neighbors reconnect automatically
    # because the outline/holes are rebuilt from formulas each time)
    def _build_param_panel(self):
        box = QGroupBox("Параметри деталі (Варіант 5)")
        form = QFormLayout()

        p = self.params
        self.sb_width = _spinbox(10, 300, p.width)
        self.sb_total_height = _spinbox(10, 300, p.total_height)
        self.sb_tab_width = _spinbox(1, 300, p.tab_width)
        self.sb_tab_offset = _spinbox(0, 300, p.tab_offset)
        self.sb_tab_height = _spinbox(0.5, 100, p.tab_height)
        self.sb_big_d = _spinbox(1, 200, p.big_hole_d)
        self.sb_big_offset_y = _spinbox(0, 300, p.big_hole_offset_y)
        self.sb_small_d = _spinbox(1, 100, p.small_hole_d)
        self.sb_small_offset_x = _spinbox(0, 300, p.small_hole_offset_x)
        self.sb_small_offset_y = _spinbox(0, 300, p.small_hole_offset_y)

        rows = [
            ("Ширина (50)", self.sb_width),
            ("Повна висота (55)", self.sb_total_height),
            ("Ширина вирізу знизу (32)", self.sb_tab_width),
            ("Зсув вирізу зліва (9)", self.sb_tab_offset),
            ("Висота ніжок (6)", self.sb_tab_height),
            ("⌀ великого отвору (24)", self.sb_big_d),
            ("Зсув великого отвору по Y (22)", self.sb_big_offset_y),
            ("⌀ малих отворів (8)", self.sb_small_d),
            ("Зсув малих отворів по X (12)", self.sb_small_offset_x),
            ("Зсув малих отворів по Y (10)", self.sb_small_offset_y),
        ]
        for label, sb in rows:
            sb.valueChanged.connect(self._on_param_changed)
            form.addRow(label, sb)

        reset_btn = QPushButton("Скинути розміри")
        reset_btn.clicked.connect(self._reset_shape)
        form.addRow(reset_btn)

        box.setLayout(form)

        scroll = QScrollArea()
        scroll.setWidget(box)
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(270)
        return scroll

    def _on_param_changed(self, *_):
        p = self.params
        p.width = self.sb_width.value()
        p.total_height = self.sb_total_height.value()
        p.tab_width = self.sb_tab_width.value()
        p.tab_offset = self.sb_tab_offset.value()
        p.tab_height = self.sb_tab_height.value()
        p.big_hole_d = self.sb_big_d.value()
        p.big_hole_offset_y = self.sb_big_offset_y.value()
        p.small_hole_d = self.sb_small_d.value()
        p.small_hole_offset_x = self.sb_small_offset_x.value()
        p.small_hole_offset_y = self.sb_small_offset_y.value()
        self._rebuild_geometry()

    def _reset_shape(self):
        self.params = PartParams()
        p = self.params
        for sb, val in [
            (self.sb_width, p.width), (self.sb_total_height, p.total_height),
            (self.sb_tab_width, p.tab_width), (self.sb_tab_offset, p.tab_offset),
            (self.sb_tab_height, p.tab_height), (self.sb_big_d, p.big_hole_d),
            (self.sb_big_offset_y, p.big_hole_offset_y), (self.sb_small_d, p.small_hole_d),
            (self.sb_small_offset_x, p.small_hole_offset_x),
            (self.sb_small_offset_y, p.small_hole_offset_y),
        ]:
            sb.blockSignals(True)
            sb.setValue(val)
            sb.blockSignals(False)
        self._rebuild_geometry()

    def _rebuild_geometry(self):
        self.base_polygons = build_part_polygons(self.params)
        self.canvas.set_polygons(self.base_polygons)

    # Transform panel
    def _build_transform_panel(self):
        container = QWidget()
        container.setFixedWidth(330)
        v = QVBoxLayout(container)

        tabs = QTabWidget()
        tabs.addTab(self._build_euclidean_tab(), "Евклідові")
        tabs.addTab(self._build_affine_special_tab(), "Афінні (окр. вип.)")
        tabs.addTab(self._build_affine_general_tab(), "Афінні (загальні)")
        tabs.addTab(self._build_projective_tab(), "Проективні")
        v.addWidget(tabs)

        v.addWidget(self._build_matrix_readout())

        btn_row = QHBoxLayout()
        undo_btn = QPushButton("Скасувати останнє")
        undo_btn.clicked.connect(self._undo)
        reset_btn = QPushButton("Скинути перетворення")
        reset_btn.clicked.connect(self._reset_transform)
        btn_row.addWidget(undo_btn)
        btn_row.addWidget(reset_btn)
        v.addLayout(btn_row)

        v.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(345)
        return scroll

    def _pivot_row(self, form, default=(25.0, 25.0)):
        px = _spinbox(-500, 500, default[0])
        py = _spinbox(-500, 500, default[1])
        pick_btn = QPushButton("Обрати точку на сцені")
        pick_btn.setCheckable(True)
        pick_btn.toggled.connect(lambda on: self._set_pivot_picking(on, px, py))
        form.addRow("Точка X:", px)
        form.addRow("Точка Y:", py)
        form.addRow(pick_btn)
        return px, py

    def _set_pivot_picking(self, on, px, py):
        if on:
            self._active_pivot_target = (px, py)
            self.canvas.set_picking_pivot(True)
        else:
            if self._active_pivot_target == (px, py):
                self._active_pivot_target = None
            self.canvas.set_picking_pivot(False)

    def _on_point_picked(self, wx, wy):
        if self._active_pivot_target is not None:
            px, py = self._active_pivot_target
            px.setValue(wx)
            py.setValue(wy)
        self.canvas.set_pivot((wx, wy))

    # Euclidean: translation + rotation about arbitrary point
    def _build_euclidean_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)

        g1 = QGroupBox("Зсув (translation)")
        f1 = QFormLayout(g1)
        self.tr_dx = _spinbox(-500, 500, 10.0)
        self.tr_dy = _spinbox(-500, 500, 0.0)
        f1.addRow("dx:", self.tr_dx)
        f1.addRow("dy:", self.tr_dy)
        btn1 = QPushButton("Застосувати зсув")
        btn1.clicked.connect(self._apply_translate)
        f1.addRow(btn1)
        v.addWidget(g1)

        g2 = QGroupBox("Обертання навколо довільної точки")
        f2 = QFormLayout(g2)
        self.rot_angle = _spinbox(-360, 360, 30.0)
        self.rot_px, self.rot_py = self._pivot_row(f2)
        f2.addRow("Кут, °:", self.rot_angle)
        btn2 = QPushButton("Застосувати обертання")
        btn2.clicked.connect(self._apply_rotate)
        f2.addRow(btn2)
        v.addWidget(g2)

        v.addStretch(1)
        return w

    def _apply_translate(self):
        m = Mat3.translation(self.tr_dx.value(), self.tr_dy.value())
        self._compose(m)

    def _apply_rotate(self):
        m = Mat3.rotation(self.rot_angle.value(), self.rot_px.value(), self.rot_py.value())
        self._compose(m)

    # Affine special cases: point reflection + scaling
    def _build_affine_special_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)

        g1 = QGroupBox("Симетрія відносно точки")
        f1 = QFormLayout(g1)
        self.ref_px, self.ref_py = self._pivot_row(f1)
        btn1 = QPushButton("Застосувати симетрію")
        btn1.clicked.connect(self._apply_reflect)
        f1.addRow(btn1)
        v.addWidget(g1)

        g2 = QGroupBox("Масштабування")
        f2 = QFormLayout(g2)
        self.sc_sx = _spinbox(-10, 10, 1.5, step=0.1)
        self.sc_sy = _spinbox(-10, 10, 1.5, step=0.1)
        self.sc_px, self.sc_py = self._pivot_row(f2)
        f2.addRow("sx:", self.sc_sx)
        f2.addRow("sy:", self.sc_sy)
        btn2 = QPushButton("Застосувати масштабування")
        btn2.clicked.connect(self._apply_scale)
        f2.addRow(btn2)
        v.addWidget(g2)

        v.addStretch(1)
        return w

    def _apply_reflect(self):
        m = Mat3.point_reflection(self.ref_px.value(), self.ref_py.value())
        self._compose(m)

    def _apply_scale(self):
        m = Mat3.scaling(
            self.sc_sx.value(), self.sc_sy.value(), self.sc_px.value(), self.sc_py.value()
        )
        self._compose(m)

    # General affine: define a new coordinate system (origin + basis)
    def _build_affine_general_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        info = QLabel(
            "Задайте нову систему координат: куди переходять\n"
            "початок координат та орти i, j старої системи."
        )
        info.setWordWrap(True)
        v.addWidget(info)

        g = QGroupBox("Нова система координат")
        f = QFormLayout(g)
        self.af_ox = _spinbox(-500, 500, 0.0)
        self.af_oy = _spinbox(-500, 500, 0.0)
        self.af_ix = _spinbox(-10, 10, 1.0, step=0.1)
        self.af_iy = _spinbox(-10, 10, 0.3, step=0.1)
        self.af_jx = _spinbox(-10, 10, -0.2, step=0.1)
        self.af_jy = _spinbox(-10, 10, 1.2, step=0.1)
        f.addRow("Origin X:", self.af_ox)
        f.addRow("Origin Y:", self.af_oy)
        f.addRow("i' X:", self.af_ix)
        f.addRow("i' Y:", self.af_iy)
        f.addRow("j' X:", self.af_jx)
        f.addRow("j' Y:", self.af_jy)
        btn = QPushButton("Застосувати афінне перетворення")
        btn.clicked.connect(self._apply_affine)
        f.addRow(btn)
        v.addWidget(g)

        v.addStretch(1)
        return w

    def _apply_affine(self):
        m = Mat3.affine_from_basis(
            (self.af_ox.value(), self.af_oy.value()),
            (self.af_ix.value(), self.af_iy.value()),
            (self.af_jx.value(), self.af_jy.value()),
        )
        self._compose(m)

    # Projective: 4-point correspondence defines the new system
    def _build_projective_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        info = QLabel(
            "4 кутові точки поточного контуру переходять\n"
            "у задані нижче точки (проективна система координат)."
        )
        info.setWordWrap(True)
        v.addWidget(info)

        g = QGroupBox("Цільові точки (куди переходять кути bbox)")
        f = QFormLayout(g)
        self.pj_pts = []
        labels = ["Верх-ліво", "Верх-право", "Низ-право", "Низ-ліво"]
        for label in labels:
            ux = _spinbox(-500, 500, 0.0, step=1.0)
            uy = _spinbox(-500, 500, 0.0, step=1.0)
            f.addRow(f"{label} X:", ux)
            f.addRow(f"{label} Y:", uy)
            self.pj_pts.append((ux, uy))
        v.addWidget(g)

        fill_btn = QPushButton("Заповнити поточними кутами bbox")
        fill_btn.clicked.connect(self._fill_projective_defaults)
        v.addWidget(fill_btn)

        apply_btn = QPushButton("Застосувати проективне перетворення")
        apply_btn.clicked.connect(self._apply_projective)
        v.addWidget(apply_btn)

        v.addStretch(1)
        self._fill_projective_defaults()
        return w

    def _current_bbox_corners(self):
        outline = self.base_polygons[0]
        transformed = [self.transform_stack[-1].apply(x, y) for x, y in outline]
        xmin, ymin, xmax, ymax = bounding_box(transformed)
        return [(xmin, ymax), (xmax, ymax), (xmax, ymin), (xmin, ymin)]

    def _fill_projective_defaults(self):
        corners = self._current_bbox_corners()
        for (ux, uy), (cx, cy) in zip(self.pj_pts, corners):
            ux.setValue(cx)
            uy.setValue(cy)

    def _apply_projective(self):
        src = self._current_bbox_corners()
        dst = [(ux.value(), uy.value()) for ux, uy in self.pj_pts]
        try:
            m = Mat3.projective_from_points(src, dst)
        except ValueError:
            return
        self._compose(m)

    # Transform stack + readout
    def _build_matrix_readout(self):
        box = QGroupBox("Поточна сумарна матриця перетворення")
        grid = QGridLayout(box)
        self.matrix_labels = []
        for i in range(3):
            row = []
            for j in range(3):
                lbl = QLabel("0.00")
                lbl.setAlignment(Qt.AlignCenter)
                grid.addWidget(lbl, i, j)
                row.append(lbl)
            self.matrix_labels.append(row)
        self._refresh_matrix_readout()
        return box

    def _refresh_matrix_readout(self):
        m = self.transform_stack[-1].m
        for i in range(3):
            for j in range(3):
                self.matrix_labels[i][j].setText(f"{m[i*3+j]:.3f}")

    def _compose(self, m: Mat3):
        new_total = m.multiply(self.transform_stack[-1])
        self.transform_stack.append(new_total)
        self.canvas.set_transform(new_total)
        self._refresh_matrix_readout()

    def _undo(self):
        if len(self.transform_stack) > 1:
            self.transform_stack.pop()
            self.canvas.set_transform(self.transform_stack[-1])
            self._refresh_matrix_readout()

    def _reset_transform(self):
        self.transform_stack = [Mat3.identity()]
        self.canvas.set_transform(Mat3.identity())
        self._refresh_matrix_readout()
