"""Криві третього порядку, задані в інженерному вигляді (раціональні кубічні),
та контур із таких дуг.

r(u) = ( rA wA (1-u)^3 + 3 rB wB u (1-u)^2 + 3 rC wC u^2 (1-u) + rD wD u^3 )
       / ( wA (1-u)^3 + 3 wB u (1-u)^2 + 3 wC u^2 (1-u) + wD u^3 ),   0 <= u <= 1
Якщо всі ваги дорівнюють 1 — це звичайна крива Безьє третього порядку.
"""
import json
import math

from geometry import Mat3


def engineering_point(r, w, u):
    """Точка кривої третього порядку в інженерному вигляді (формула 1.2).
    r — список з 4 реперних точок [(x, y)]*4, w — 4 ваги."""
    v = 1.0 - u
    b0 = w[0] * v ** 3
    b1 = 3.0 * w[1] * u * v ** 2
    b2 = 3.0 * w[2] * u ** 2 * v
    b3 = w[3] * u ** 3
    den = b0 + b1 + b2 + b3
    x = (r[0][0] * b0 + r[1][0] * b1 + r[2][0] * b2 + r[3][0] * b3) / den
    y = (r[0][1] * b0 + r[1][1] * b1 + r[2][1] * b2 + r[3][1] * b3) / den
    return x, y


def segment_points(r, w, step):
    """Цикл по параметру u від 0 до 1 з кроком step -> список точок дуги."""
    n = max(2, int(round(1.0 / step)))
    return [engineering_point(r, w, i / n) for i in range(n + 1)]


class Contour:
    """Криволінійний контур = послідовність дуг (кожна — 4 реперні точки A,B,C,D
    та 4 ваги)."""

    def __init__(self, pts=None, weights=None):
        self.pts = pts or []          # [[ [x,y]*4 ], ...]
        self.w = weights or [[1.0] * 4 for _ in self.pts]

    @staticmethod
    def load(path):
        with open(path, encoding="utf-8") as f:
            segs = json.load(f)
        return Contour([[list(p) for p in s] for s in segs])

    def copy(self):
        return Contour([[list(p) for p in s] for s in self.pts], [list(w) for w in self.w])

    def __len__(self):
        return len(self.pts)

    def move_point(self, si, pi, x, y):
        """Переміщення реперної точки. Кінцеві точки дуг (A, D) зшиті з сусідніми
        дугами: якщо в іншої дуги кінець збігається — він рухається разом."""
        old = list(self.pts[si][pi])
        if pi in (0, 3):
            for s in self.pts:
                for k in (0, 3):
                    if abs(s[k][0] - old[0]) < 1e-6 and abs(s[k][1] - old[1]) < 1e-6:
                        s[k][0], s[k][1] = x, y
        else:
            self.pts[si][pi] = [x, y]

    def transform(self, m: Mat3):
        """Евклідове перетворення: кожну реперну точку множимо на матрицю."""
        for s in self.pts:
            for p in s:
                p[0], p[1] = m.apply(p[0], p[1])

    def all_curve_points(self, step):
        return [segment_points(self.pts[i], self.w[i], step) for i in range(len(self.pts))]


# ---------- цільові фігури для анімації переходу ----------
def _shape_contour(point_at, tangent_at, n, curved):
    """Будує контур із n дуг, що йдуть по замкненій лінії point_at(s), s in [0,1)."""
    pts = []
    for i in range(n):
        s0, s1 = i / n, (i + 1) / n
        a, d = point_at(s0), point_at(s1)
        if curved:
            h = (4.0 / 3.0) * math.tan(math.pi * 2.0 / n / 4.0) * curved
            t0, t1 = tangent_at(s0), tangent_at(s1)
            b = [a[0] + h * t0[0], a[1] + h * t0[1]]
            c = [d[0] - h * t1[0], d[1] - h * t1[1]]
        else:
            b = [a[0] + (d[0] - a[0]) / 3.0, a[1] + (d[1] - a[1]) / 3.0]
            c = [a[0] + 2.0 * (d[0] - a[0]) / 3.0, a[1] + 2.0 * (d[1] - a[1]) / 3.0]
        pts.append([list(a), b, c, list(d)])
    return Contour(pts)


def _polygon_point(vertices):
    def f(s):
        k = len(vertices)
        x = (s % 1.0) * k
        i = int(x) % k
        t = x - int(x)
        p, q = vertices[i], vertices[(i + 1) % k]
        return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
    return f


def target_shape(name, n):
    """Кінцеві координати реперних точок: інша фігура з тією ж кількістю дуг."""
    if name == "Трикутник":
        v = [(-11.0, -8.0), (11.0, -8.0), (0.0, 9.0)]
        return _shape_contour(_polygon_point(v), None, n, 0)
    if name == "Квадрат":
        v = [(-9.0, -9.0), (9.0, -9.0), (9.0, 9.0), (-9.0, 9.0)]
        return _shape_contour(_polygon_point(v), None, n, 0)
    R = 9.0
    pos = lambda s: (R * math.cos(2 * math.pi * s), R * math.sin(2 * math.pi * s))
    tan = lambda s: (-math.sin(2 * math.pi * s), math.cos(2 * math.pi * s))
    return _shape_contour(pos, tan, n, R)


def morph(src: Contour, dst: Contour, t):
    """Кадр анімації: кожна реперна точка йде по своїй прямій від початкових
    координат до кінцевих: r = r0 + (r1 - r0) * t; ваги так само."""
    out = src.copy()
    for i, s in enumerate(out.pts):
        for k in range(4):
            s[k][0] = src.pts[i][k][0] + (dst.pts[i][k][0] - src.pts[i][k][0]) * t
            s[k][1] = src.pts[i][k][1] + (dst.pts[i][k][1] - src.pts[i][k][1]) * t
            out.w[i][k] = src.w[i][k] + (dst.w[i][k] - src.w[i][k]) * t
    return out
