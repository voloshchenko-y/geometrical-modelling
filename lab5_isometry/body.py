import math

# за замовч.
DEFAULTS = dict(n=5, height=60.0, width=60.0, depth=60.0, ratio=0.45, scale=1.0)


class StarPrism:
    def __init__(self):
        self.n = DEFAULTS["n"]
        self.height = DEFAULTS["height"]
        self.width = DEFAULTS["width"]
        self.depth = DEFAULTS["depth"]
        self.ratio = DEFAULTS["ratio"]
        self.scale = DEFAULTS["scale"]

    def reset(self):
        for k, v in DEFAULTS.items():
            setattr(self, k, v)

    def footprint(self):
        # зірка XZ
        rx, rz = self.width / 2.0, self.depth / 2.0
        pts = []
        for i in range(2 * self.n):
            t = math.pi / 2.0 + i * math.pi / self.n
            k = 1.0 if i % 2 == 0 else self.ratio
            pts.append((k * rx * math.cos(t), k * rz * math.sin(t)))
        return pts

    def vertices(self):
        fp = self.footprint()
        bottom = [(x, 0.0, z) for x, z in fp]
        top = [(x, self.height, z) for x, z in fp]
        return bottom + top

    def edges(self):
        m = 2 * self.n
        e = []
        for i in range(m):
            j = (i + 1) % m
            e.append((i, j))  # низ
            e.append((m + i, m + j))  # верх
            e.append((i, m + i))  # бічне
        return e

    def center(self):
        # центр
        return 0.0, self.height / 2.0, 0.0
