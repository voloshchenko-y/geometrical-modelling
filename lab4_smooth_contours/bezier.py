import json
import math

from geometry import Mat3

JOINT_EPS = 1e-6  # точність
SMOOTH_TOL_DEG = 1.0  # допуск


def engineering_point(r, w, u):
    # формула 1.2
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
    n = max(2, int(round(1.0 / step)))
    return [engineering_point(r, w, i / n) for i in range(n + 1)]


def handle_index(k):
    return 1 if k == 0 else 2


class Contour:
    def __init__(self, pts=None, weights=None, joints=None, smooth=None):
        self.pts = pts or []
        self.w = weights or [[1.0] * 4 for _ in self.pts]
        self.joints = joints if joints is not None else self._find_joints()
        self.smooth = smooth if smooth is not None else [False] * len(self.joints)
        self._joint_of = {}
        for j, (e1, e2) in enumerate(self.joints):
            self._joint_of[e1] = j
            self._joint_of[e2] = j

    @staticmethod
    def load(path):
        with open(path, encoding="utf-8") as f:
            segs = json.load(f)
        c = Contour([[list(p) for p in s] for s in segs])
        c.auto_classify()
        return c

    def copy(self):
        return Contour([[list(p) for p in s] for s in self.pts], [list(w) for w in self.w],
                       list(self.joints), list(self.smooth))

    def __len__(self):
        return len(self.pts)

    # стики
    def _find_joints(self):
        ends = [(i, k) for i in range(len(self.pts)) for k in (0, 3)]
        partners = {e: [] for e in ends}
        for a in range(len(ends)):
            for b in range(a + 1, len(ends)):
                (i, k), (j, m) = ends[a], ends[b]
                if i == j:
                    continue
                p, q = self.pts[i][k], self.pts[j][m]
                if abs(p[0] - q[0]) < JOINT_EPS and abs(p[1] - q[1]) < JOINT_EPS:
                    partners[ends[a]].append(ends[b])
                    partners[ends[b]].append(ends[a])
        joints = []
        for e in ends:
            if len(partners[e]) == 1 and e < partners[e][0] and len(partners[partners[e][0]]) == 1:
                joints.append((e, partners[e][0]))
        return joints

    def joint_index(self, i, k):
        return self._joint_of.get((i, k))

    def smooth_count(self):
        return sum(1 for s in self.smooth if s)

    def break_count(self):
        return len(self.smooth) - self.smooth_count()

    def handle_vector(self, i, k):
        n = self.pts[i][k]
        h = self.pts[i][handle_index(k)]
        return h[0] - n[0], h[1] - n[1]

    def joint_angle(self, j):
        # кут
        (i1, k1), (i2, k2) = self.joints[j]
        ax, ay = self.handle_vector(i1, k1)
        bx, by = self.handle_vector(i2, k2)
        la, lb = math.hypot(ax, ay), math.hypot(bx, by)
        if la < 1e-12 or lb < 1e-12:
            return None
        c = (ax * bx + ay * by) / (la * lb)
        return math.degrees(math.acos(max(-1.0, min(1.0, c))))

    def joint_info(self, i, k):
        j = self.joint_index(i, k)
        if j is None:
            return None
        e1, e2 = self.joints[j]
        other = e2 if e1 == (i, k) else e1
        return {"joint": j, "partner": other[0], "smooth": self.smooth[j],
                "angle": self.joint_angle(j)}

    # гладкість
    def enforce_smooth(self, j, master):
        e1, e2 = self.joints[j]
        slave = e2 if master == e1 else e1
        mx, my = self.handle_vector(*master)
        lm = math.hypot(mx, my)
        if lm < 1e-12:
            return  # вироджена
        sx, sy = self.handle_vector(*slave)
        ls = math.hypot(sx, sy)
        node = self.pts[slave[0]][slave[1]]
        hp = self.pts[slave[0]][handle_index(slave[1])]
        hp[0] = node[0] - ls * mx / lm
        hp[1] = node[1] - ls * my / lm

    def align_joint(self, j):
        # вирівняти
        e1, e2 = self.joints[j]
        l1 = math.hypot(*self.handle_vector(*e1))
        l2 = math.hypot(*self.handle_vector(*e2))
        self.enforce_smooth(j, e1 if l1 >= l2 else e2)

    def auto_classify(self):
        # початкові типи
        for j in range(len(self.joints)):
            ang = self.joint_angle(j)
            self.smooth[j] = ang is not None and ang >= 180.0 - SMOOTH_TOL_DEG
            if self.smooth[j]:
                self.align_joint(j)

    def set_all(self, smooth):
        for j in range(len(self.joints)):
            self.smooth[j] = smooth
            if smooth:
                self.align_joint(j)

    def toggle_joint(self, j):
        self.smooth[j] = not self.smooth[j]
        if self.smooth[j]:
            self.align_joint(j)
        return self.smooth[j]

    def move_point(self, si, pi, x, y):
        if pi in (1, 2):
            self.pts[si][pi] = [x, y]
            k = 0 if pi == 1 else 3
            j = self.joint_index(si, k)
            if j is not None and self.smooth[j]:
                self.enforce_smooth(j, (si, k))
            return
        old = self.pts[si][pi]
        dx, dy = x - old[0], y - old[1]
        j = self.joint_index(si, pi)
        ends = list(self.joints[j]) if j is not None else [(si, pi)]
        for (i, k) in ends:
            self.pts[i][k] = [x, y]
            if j is not None and self.smooth[j]:
                h = self.pts[i][handle_index(k)]
                h[0] += dx
                h[1] += dy

    def transform(self, m: Mat3):
        for s in self.pts:
            for p in s:
                p[0], p[1] = m.apply(p[0], p[1])

    def all_curve_points(self, step):
        return [segment_points(self.pts[i], self.w[i], step) for i in range(len(self.pts))]


# фігури
def _shape_contour(point_at, tangent_at, n, curved):
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
    # кадр
    out = src.copy()
    for i, s in enumerate(out.pts):
        for k in range(4):
            s[k][0] = src.pts[i][k][0] + (dst.pts[i][k][0] - src.pts[i][k][0]) * t
            s[k][1] = src.pts[i][k][1] + (dst.pts[i][k][1] - src.pts[i][k][1]) * t
            out.w[i][k] = src.w[i][k] + (dst.w[i][k] - src.w[i][k]) * t
    return out
