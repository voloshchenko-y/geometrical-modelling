import json
import math

K_UV = math.pi / 6.0 / 10.0  # формула 6.16


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


def load_arcs(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sample_arcs(arcs, n=16):
    w = [1.0, 1.0, 1.0, 1.0]
    return [[engineering_point(a, w, i / n) for i in range(n + 1)] for a in arcs]


def rotate_about(p, c, angle_deg):
    # оберт навколо c
    t = math.radians(angle_deg)
    cs, sn = math.cos(t), math.sin(t)
    dx, dy = p[0] - c[0], p[1] - c[1]
    return c[0] + dx * cs - dy * sn, c[1] + dx * sn + dy * cs


class ContourUV:
    def __init__(self, path):
        self.arcs = load_arcs(path)
        self.xy = sample_arcs(self.arcs)
        # XY -> UV (6.16)
        self.uv0 = [[(x * K_UV, y * K_UV) for x, y in line] for line in self.xy]
        pts = [p for line in self.uv0 for p in line]
        us = [p[0] for p in pts]
        vs = [p[1] for p in pts]
        self.center0 = ((min(us) + max(us)) / 2.0, (min(vs) + max(vs)) / 2.0)

    def place(self, pivot, angle_deg, scale):
        # масштаб, оберт, pivot
        res = []
        c0 = self.center0
        for line in self.uv0:
            out = []
            for u, v in line:
                p = (c0[0] + (u - c0[0]) * scale, c0[1] + (v - c0[1]) * scale)
                p = rotate_about(p, c0, angle_deg)
                out.append((p[0] - c0[0] + pivot[0], p[1] - c0[1] + pivot[1]))
            res.append(out)
        return res
