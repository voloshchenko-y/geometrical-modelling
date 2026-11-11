
import math

from geometry import simpson


class Strophoid:
    def __init__(self, a=5.0):
        self.a = a

    # ---------- рівняння кривої ----------
    def r(self, phi):
        """Полярний радіус r = a cos2phi / cos phi (формула (6) методички)."""
        return self.a * math.cos(2 * phi) / math.cos(phi)

    def point(self, phi):
        """Декартові координати точки за формулами (2), (4): x = r cos, y = r sin.
        Після скорочення: x = a cos2phi,  y = a cos2phi tg phi."""
        r = self.r(phi)
        return r * math.cos(phi), r * math.sin(phi)

    # ---------- похідні ----------
    def dr(self, phi):
        """r'(phi) = -a (2 + 1/cos^2 phi) sin phi."""
        return -self.a * (2.0 + 1.0 / math.cos(phi) ** 2) * math.sin(phi)

    def d1(self, phi):
        """(x'_phi, y'_phi) за формулою (11):
        x' = r' cos - r sin,  y' = r' sin + r cos."""
        r, dr = self.r(phi), self.dr(phi)
        c, s = math.cos(phi), math.sin(phi)
        return dr * c - r * s, dr * s + r * c

    def d2(self, phi):
        """(x''_phi, y''_phi). Спрощені аналітичні вирази:
        x'' = -4 a cos2phi,
        y'' = 2 a sin(phi) (-4 sin^4 + 8 sin^2 - 5) / cos^3(phi)."""
        a = self.a
        s, c = math.sin(phi), math.cos(phi)
        xpp = -4.0 * a * math.cos(2 * phi)
        ypp = 2.0 * a * s * (-4.0 * s ** 4 + 8.0 * s ** 2 - 5.0) / c ** 3
        return xpp, ypp

    def slope(self, phi):
        """f'(phi) = y'_phi / x'_phi — формула (12). None, якщо x'_phi = 0
        (вертикальна дотична)."""
        xp, yp = self.d1(phi)
        if abs(xp) < 1e-9:
            return None
        return yp / xp

    def second_derivative(self, phi):
        """d2y/dx2 = (y'' x' - y' x'') / (x')^3."""
        xp, yp = self.d1(phi)
        xpp, ypp = self.d2(phi)
        if abs(xp) < 1e-9:
            return None
        return (ypp * xp - yp * xpp) / xp ** 3

    # ---------- кривина ----------
    def curvature(self, phi):
        """k = (x' y'' - y' x'') / (x'^2 + y'^2)^(3/2)."""
        xp, yp = self.d1(phi)
        xpp, ypp = self.d2(phi)
        return (xp * ypp - yp * xpp) / (xp * xp + yp * yp) ** 1.5

    def curvature_radius(self, phi):
        k = self.curvature(phi)
        return float("inf") if abs(k) < 1e-12 else 1.0 / abs(k)

    # ---------- дотична, нормаль ----------
    def tangent_dir(self, phi):
        """Одиничний напрямний вектор дотичної (x', y')/|(x', y')|."""
        xp, yp = self.d1(phi)
        n = math.hypot(xp, yp)
        return xp / n, yp / n

    def normal_dir(self, phi):
        """Одиничний вектор нормалі: дотична, повернута на 90 градусів."""
        tx, ty = self.tangent_dir(phi)
        return -ty, tx

    def tangent_segment(self, phi, half_len):
        """Симетричний відносно точки дотику відрізок дотичної (як Рис. 16)."""
        x0, y0 = self.point(phi)
        tx, ty = self.tangent_dir(phi)
        return (x0 - half_len * tx, y0 - half_len * ty), (x0 + half_len * tx, y0 + half_len * ty)

    def normal_segment(self, phi, half_len):
        x0, y0 = self.point(phi)
        nx, ny = self.normal_dir(phi)
        return (x0 - half_len * nx, y0 - half_len * ny), (x0 + half_len * nx, y0 + half_len * ny)

    def tangent_equation(self, phi):
        """Текст рівняння дотичної (10): y = y0 + k (x - x0)."""
        x0, y0 = self.point(phi)
        k = self.slope(phi)
        if k is None:
            return f"x = {x0:.3f}"
        return f"y = {y0:.3f} + ({k:.3f})(x - {x0:.3f})"

    def normal_equation(self, phi):
        """Текст рівняння нормалі (15): y = y0 - (x - x0)/k."""
        x0, y0 = self.point(phi)
        k = self.slope(phi)
        if k is None:
            return f"y = {y0:.3f}"
        if abs(k) < 1e-9:
            return f"x = {x0:.3f}"
        return f"y = {y0:.3f} - (x - {x0:.3f}) / ({k:.3f})"

    # ---------- асимптота ----------
    def asymptote_x(self):
        """Вертикальна асимптота x = -a.
        Перевірка: при phi -> +-pi/2 маємо x = a cos2phi -> a cos(pi) = -a,
        тоді як |y| = a|cos2phi tg phi| -> inf."""
        return -self.a

    def asymptote_segment(self, half_len):
        x = self.asymptote_x()
        return (x, -half_len), (x, half_len)

    # ---------- довжина дуги, площі ----------
    def speed(self, phi):
        """sqrt(r^2 + r'^2) = a sqrt(1 + sin^2 2phi) / cos^2 phi — підінтегральна
        функція формули (20)."""
        return self.a * math.sqrt(1.0 + math.sin(2 * phi) ** 2) / math.cos(phi) ** 2

    def arc_length(self, phi1, phi2, n=4000):
        """Довжина дуги (20), інтеграл рахується методом Сімпсона."""
        return simpson(self.speed, phi1, phi2, n)

    def loop_length(self):
        return self.arc_length(-math.pi / 4, math.pi / 4)

    def loop_area_numeric(self):
        """S = 1/2 * integral r^2 dphi по петлі (-pi/4 .. pi/4)."""
        return 0.5 * simpson(lambda p: self.r(p) ** 2, -math.pi / 4, math.pi / 4)

    def loop_area_exact(self):
        return self.a ** 2 * (2.0 - math.pi / 2.0)

    def area_between_numeric(self):
        """Площа між асимптотою x=-a та двома нескінченними гілками кривої:
        S = 2 |int_{pi/4}^{pi/2} (x + a) y' dphi|, де (x + a) y' = 2a^2 (cos2phi - sin^2 2phi)
        (особливості cos phi у знаменнику скорочуються)."""
        f = lambda p: 2.0 * self.a ** 2 * (math.cos(2 * p) - math.sin(2 * p) ** 2)
        return 2.0 * abs(simpson(f, math.pi / 4, math.pi / 2))

    def area_between_exact(self):
        return self.a ** 2 * (2.0 + math.pi / 2.0)

    # ---------- точки перегину ----------
    def inflection_points(self, phi1, phi2, n=2000):
        """Пошук точок перегину: ознака — зміна знаку кривини k (еквівалентно
        зміні знаку f''). Повертає список phi, у яких знак k змінюється."""
        res = []
        prev = self.curvature(phi1)
        h = (phi2 - phi1) / n
        for i in range(1, n + 1):
            p = phi1 + i * h
            cur = self.curvature(p)
            if prev * cur < 0:
                lo, hi = p - h, p
                for _ in range(60):  # метод бісекції
                    mid = 0.5 * (lo + hi)
                    if self.curvature(lo) * self.curvature(mid) <= 0:
                        hi = mid
                    else:
                        lo = mid
                res.append(0.5 * (lo + hi))
            prev = cur
        return res

    # ---------- цикл побудови ----------
    def build_points(self, alpha, beta, step):
        """Цикл for(phi = alpha; phi <= beta; phi += step). Повертає список (phi, x, y).
        Крок накопичується через цілий лічильник, щоб не збиралась похибка."""
        pts = []
        n = int(round((beta - alpha) / step))
        for i in range(n + 1):
            phi = alpha + i * step
            x, y = self.point(phi)
            pts.append((phi, x, y))
        return pts
