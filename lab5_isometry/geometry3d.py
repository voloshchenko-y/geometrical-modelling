import math


class Mat4:
    __slots__ = ("m",)

    def __init__(self, m=None):
        self.m = list(m) if m is not None else [1, 0, 0, 0,
                                                0, 1, 0, 0,
                                                0, 0, 1, 0,
                                                0, 0, 0, 1]

    @staticmethod
    def identity():
        return Mat4()

    @staticmethod
    def translation(dx, dy, dz):
        # зсув
        return Mat4([1, 0, 0, 0,
                     0, 1, 0, 0,
                     0, 0, 1, 0,
                     dx, dy, dz, 1])

    @staticmethod
    def scaling(sx, sy, sz):
        return Mat4([sx, 0, 0, 0,
                     0, sy, 0, 0,
                     0, 0, sz, 0,
                     0, 0, 0, 1])

    @staticmethod
    def rotation_x(angle_deg):
        # Y -> Z
        t = math.radians(angle_deg)
        c, s = math.cos(t), math.sin(t)
        return Mat4([1, 0, 0, 0,
                     0, c, s, 0,
                     0, -s, c, 0,
                     0, 0, 0, 1])

    @staticmethod
    def rotation_y(angle_deg):
        # Z -> X
        t = math.radians(angle_deg)
        c, s = math.cos(t), math.sin(t)
        return Mat4([c, 0, -s, 0,
                     0, 1, 0, 0,
                     s, 0, c, 0,
                     0, 0, 0, 1])

    @staticmethod
    def rotation_z(angle_deg):
        # X -> Y
        t = math.radians(angle_deg)
        c, s = math.cos(t), math.sin(t)
        return Mat4([c, s, 0, 0,
                     -s, c, 0, 0,
                     0, 0, 1, 0,
                     0, 0, 0, 1])

    @staticmethod
    def about_point(m, cx, cy, cz):
        # T(-c) m T(c)
        return (Mat4.translation(-cx, -cy, -cz)
                .multiply(m)
                .multiply(Mat4.translation(cx, cy, cz)))

    def multiply(self, other):
        a, b = self.m, other.m
        r = [0.0] * 16
        for i in range(4):
            for j in range(4):
                s = 0.0
                for k in range(4):
                    s += a[i * 4 + k] * b[k * 4 + j]
                r[i * 4 + j] = s
        return Mat4(r)

    def transposed(self):
        m = self.m
        return Mat4([m[j * 4 + i] for i in range(4) for j in range(4)])

    def apply(self, x, y, z):
        # ділимо на w
        m = self.m
        xp = x * m[0] + y * m[4] + z * m[8] + m[12]
        yp = x * m[1] + y * m[5] + z * m[9] + m[13]
        zp = x * m[2] + y * m[6] + z * m[10] + m[14]
        wp = x * m[3] + y * m[7] + z * m[11] + m[15]
        if abs(wp) < 1e-12:
            wp = 1e-12
        return xp / wp, yp / wp, zp / wp


# проекції
def projection_z0():
    # формула 5.7
    return Mat4([1, 0, 0, 0,
                 0, 1, 0, 0,
                 0, 0, 0, 0,
                 0, 0, 0, 1])


def trimetry_matrix(alpha_deg, beta_deg):
    # формула 5.9
    return (Mat4.rotation_y(beta_deg)
            .multiply(Mat4.rotation_x(alpha_deg))
            .multiply(projection_z0()))


def distortion_factors(alpha_deg, beta_deg):
    m = trimetry_matrix(alpha_deg, beta_deg)
    res = []
    for ex, ey, ez in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        x, y, _ = m.apply(ex, ey, ez)
        res.append(math.hypot(x, y))
    return tuple(res)


def isometry_angles():
    # формула 2.12
    alpha = math.degrees(math.asin(math.sqrt(1.0 / 3.0)))
    beta = math.degrees(math.asin(math.sqrt(1.0 / 2.0)))
    return alpha, beta


# 8 напрямів
BETA_CHOICES = (-45.0, 45.0, 135.0, -135.0)


def isometry_matrix(alpha_sign=+1, beta_deg=-45.0, practical=False):
    a0, b0 = isometry_angles()
    if round(abs(beta_deg) % 90.0, 6) != round(b0, 6):
        raise ValueError("для ізометрії beta має бути 45, 135, -45 або -135 градусів")
    m = trimetry_matrix(alpha_sign * a0, beta_deg)
    if practical:
        u = distortion_factors(a0, b0)[0]
        m = m.multiply(Mat4.scaling(1.0 / u, 1.0 / u, 1.0))
    return m
