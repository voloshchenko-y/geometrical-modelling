import math

# за замовч.
DEFAULTS = dict(A=30.0, B=30.0, C=35.0, u_min=-1.0, u_max=1.0, v_min=-1.5, v_max=1.5, mesh=0.1)


class Surface:
    # гіперболічний параболоїд (6.9)
    def __init__(self):
        self.reset()

    def reset(self):
        for k, v in DEFAULTS.items():
            setattr(self, k, v)

    def point(self, u, v):
        # Y вгору
        x = self.A * v * math.cosh(u)
        z = self.B * v * math.sinh(u)
        y = self.C * u * u
        return x, y, z

    def _values(self, lo, hi):
        n = max(1, int(round((hi - lo) / self.mesh)))
        return [lo + (hi - lo) * i / n for i in range(n + 1)]

    def grid(self):
        us = self._values(self.u_min, self.u_max)
        vs = self._values(self.v_min, self.v_max)
        return [[self.point(u, v) for v in vs] for u in us]

    def lines(self):
        # лінії сітки
        g = self.grid()
        rows = [list(r) for r in g]
        cols = [[g[i][j] for i in range(len(g))] for j in range(len(g[0]))]
        return rows + cols

    def center(self):
        pts = [p for row in self.grid() for p in row]
        xs, ys, zs = zip(*pts)
        return ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0, (min(zs) + max(zs)) / 2.0)
