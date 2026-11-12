import math


class Mat3:
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
        # навколо точки
        t = math.radians(angle_deg)
        c, s = math.cos(t), math.sin(t)
        rot = Mat3([c, -s, 0, s, c, 0, 0, 0, 1])
        if cx == 0.0 and cy == 0.0:
            return rot
        return Mat3.translation(cx, cy).multiply(rot).multiply(Mat3.translation(-cx, -cy))

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
