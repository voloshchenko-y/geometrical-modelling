import math


def solve_linear_system(a_rows, b_col):
    n = len(a_rows)
    m = [list(a_rows[i]) + [b_col[i]] for i in range(n)]

    for col in range(n):
        pivot_row = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot_row][col]) < 1e-12:
            raise ValueError("Degenerate point configuration (singular system)")
        m[col], m[pivot_row] = m[pivot_row], m[col]

        pivot = m[col][col]
        m[col] = [v / pivot for v in m[col]]

        for r in range(n):
            if r == col:
                continue
            factor = m[r][col]
            if factor != 0.0:
                m[r] = [m[r][k] - factor * m[col][k] for k in range(n + 1)]

    return [m[i][n] for i in range(n)]


class Mat3:
    """Row-major 3x3 matrix for 2D homogeneous transforms."""

    __slots__ = ("m",)

    def __init__(self, m=None):
        self.m = list(m) if m is not None else [1, 0, 0, 0, 1, 0, 0, 0, 1]

    @staticmethod
    def identity():
        return Mat3()

    @staticmethod
    def translation(dx, dy):
        return Mat3([1, 0, dx, 0, 1, dy, 0, 0, 1])

    @staticmethod
    def rotation(angle_deg, cx=0.0, cy=0.0):
        t = math.radians(angle_deg)
        c, s = math.cos(t), math.sin(t)
        rot = Mat3([c, -s, 0, s, c, 0, 0, 0, 1])
        if cx == 0.0 and cy == 0.0:
            return rot
        return Mat3.translation(cx, cy).multiply(rot).multiply(Mat3.translation(-cx, -cy))

    @staticmethod
    def scaling(sx, sy, cx=0.0, cy=0.0):
        scale = Mat3([sx, 0, 0, 0, sy, 0, 0, 0, 1])
        if cx == 0.0 and cy == 0.0:
            return scale
        return Mat3.translation(cx, cy).multiply(scale).multiply(Mat3.translation(-cx, -cy))

    @staticmethod
    def point_reflection(cx, cy):
        """Central symmetry about an arbitrary point: special case of
        affine scaling with sx = sy = -1."""
        return Mat3.scaling(-1.0, -1.0, cx, cy)

    @staticmethod
    def affine_from_basis(origin, i_vec, j_vec):
        """General affine transform defined by picking a new coordinate
        system: where the old origin/i-axis/j-axis land in world space."""
        ox, oy = origin
        ix, iy = i_vec
        jx, jy = j_vec
        return Mat3([ix, jx, ox, iy, jy, oy, 0, 0, 1])

    @staticmethod
    def projective_from_points(src4, dst4):
        """Homography mapping src4[i] -> dst4[i] for 4 point pairs.
        Solves the 8x8 linear system for h11..h32 (h33 fixed to 1) by
        hand via solve_linear_system."""
        if len(src4) != 4 or len(dst4) != 4:
            raise ValueError("projective_from_points needs exactly 4 point pairs")

        a_rows = []
        b_col = []
        for (x, y), (u, v) in zip(src4, dst4):
            a_rows.append([x, y, 1, 0, 0, 0, -x * u, -y * u])
            b_col.append(u)
            a_rows.append([0, 0, 0, x, y, 1, -x * v, -y * v])
            b_col.append(v)

        h = solve_linear_system(a_rows, b_col)
        h11, h12, h13, h21, h22, h23, h31, h32 = h
        return Mat3([h11, h12, h13, h21, h22, h23, h31, h32, 1.0])

    def multiply(self, other):
        a, b = self.m, other.m
        r = [0.0] * 9
        for i in range(3):
            for j in range(3):
                s = 0.0
                for k in range(3):
                    s += a[i * 3 + k] * b[k * 3 + j]
                r[i * 3 + j] = s
        return Mat3(r)

    def apply(self, x, y):
        m = self.m
        xp = m[0] * x + m[1] * y + m[2]
        yp = m[3] * x + m[4] * y + m[5]
        wp = m[6] * x + m[7] * y + m[8]
        if abs(wp) < 1e-9:
            wp = 1e-9 if wp >= 0 else -1e-9
        return xp / wp, yp / wp


class PartParams:
    """Editable parameters for variant 5's plate. Editing any of these
    regenerates the outline/holes from formulas, so neighboring edges stay
    joined automatically."""

    def __init__(self):
        self.width = 50.0
        self.total_height = 55.0
        self.tab_width = 32.0
        self.tab_offset = 9.0
        self.tab_height = 6.0
        self.big_hole_d = 24.0
        self.big_hole_offset_y = 22.0
        self.small_hole_d = 8.0
        self.small_hole_offset_x = 12.0
        self.small_hole_offset_y = 10.0

    def body_height(self):
        return self.total_height - self.tab_height


def _circle_points(cx, cy, r, segments=64):
    pts = []
    for i in range(segments):
        t = 2 * math.pi * i / segments
        pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return pts


def build_outline(p: PartParams):
    """Body rectangle (0,0)-(width, body_height) sitting on two legs at the
    bottom-left and bottom-right corners, with a rectangular notch cut out
    of the bottom edge between them, as one closed contour."""
    w = p.width
    bh = p.body_height()
    n0 = p.tab_offset
    n1 = p.tab_offset + p.tab_width
    leg_bottom = -p.tab_height

    return [
        (0.0, leg_bottom),
        (0.0, bh),
        (w, bh),
        (w, leg_bottom),
        (n1, leg_bottom),
        (n1, 0.0),
        (n0, 0.0),
        (n0, leg_bottom),
    ]


def build_part_polygons(p: PartParams):
    """Returns list of closed polygons: [outline, big_hole, small_hole_l,
    small_hole_r], all in model/base coordinates."""
    bh = p.body_height()
    cx = p.width / 2.0

    outline = build_outline(p)
    big_hole = _circle_points(cx, p.big_hole_offset_y, p.big_hole_d / 2.0)
    hole_l = _circle_points(
        p.small_hole_offset_x, bh - p.small_hole_offset_y, p.small_hole_d / 2.0
    )
    hole_r = _circle_points(
        p.width - p.small_hole_offset_x, bh - p.small_hole_offset_y, p.small_hole_d / 2.0
    )

    return [outline, big_hole, hole_l, hole_r]


def bounding_box(polygon):
    xs = [x for x, _ in polygon]
    ys = [y for _, y in polygon]
    return min(xs), min(ys), max(xs), max(ys)
