import os

from contour import ContourUV
from geometry3d import Mat4, isometry_matrix, isometry_angles, distortion_factors
from surface import Surface

HERE = os.path.dirname(os.path.abspath(__file__))
AXIS_COLORS = (("X", (230, 40, 40)), ("Y", (40, 190, 40)), ("Z", (40, 60, 230)))
BASE_UV = (0.0, 0.8)  # початкове місце контуру
SCALE0 = 1.5


class Scene:
    def __init__(self, contour_path=None):
        self.surface = Surface()
        self.contour = ContourUV(contour_path or os.path.join(HERE, "duck_contour.json"))
        self.pos = [0.0, 0.0, 0.0]  # зсув поверхні
        self.ang = [0.0, 0.0, 0.0]  # кути поверхні, °
        self.reset_contour()
        self.alpha_sign = +1
        self.beta = -45.0
        self.practical = False

    # поверхня
    def reset_pose(self):
        self.pos = [0.0, 0.0, 0.0]
        self.ang = [0.0, 0.0, 0.0]

    def apply_offsets(self, dpos, dang):
        for i in range(3):
            self.pos[i] += dpos[i]
            self.ang[i] = (self.ang[i] + dang[i]) % 360.0

    def model_matrix(self):
        # T(-c) Rx Ry Rz T(c) T(pos)
        cx, cy, cz = self.surface.center()
        rot = (Mat4.rotation_x(self.ang[0])
               .multiply(Mat4.rotation_y(self.ang[1]))
               .multiply(Mat4.rotation_z(self.ang[2])))
        return (Mat4.translation(-cx, -cy, -cz)
                .multiply(rot)
                .multiply(Mat4.translation(cx, cy, cz))
                .multiply(Mat4.translation(*self.pos)))

    # контур
    def reset_contour(self):
        self.c_du = 0.0
        self.c_dv = 0.0
        self.c_angle = 0.0
        self.c_scale = SCALE0

    def apply_contour(self, du, dv, angle):
        self.c_du += du
        self.c_dv += dv
        self.c_angle = (self.c_angle + angle) % 360.0

    def contour_pivot_uv(self):
        return BASE_UV[0] + self.c_du, BASE_UV[1] + self.c_dv

    def contour_uv(self):
        return self.contour.place(self.contour_pivot_uv(), self.c_angle, self.c_scale)

    def contour_local(self):
        # на поверхні
        s = self.surface
        return [[s.point(u, v) for u, v in line] for line in self.contour_uv()]

    # проекція
    def view_matrix(self):
        return isometry_matrix(self.alpha_sign, self.beta, self.practical)

    def view_info(self):
        a, b = isometry_angles()
        u = distortion_factors(self.alpha_sign * a, self.beta)
        k = 1.0 / u[0] if self.practical else 1.0
        return {"alpha": self.alpha_sign * a, "beta": self.beta,
                "factors": tuple(f * k for f in u)}

    def _project(self, polylines):
        total = self.model_matrix().multiply(self.view_matrix())
        return [[total.apply(*p)[:2] for p in line] for line in polylines]

    def mesh_2d(self):
        return self._project(self.surface.lines())

    def contour_2d(self):
        return self._project(self.contour_local())

    def contour_world(self):
        mm = self.model_matrix()
        return [[mm.apply(*p) for p in line] for line in self.contour_local()]

    def axes_2d(self, length):
        vm = self.view_matrix()
        res = []
        for (name, col), end in zip(AXIS_COLORS, ((length, 0, 0), (0, length, 0), (0, 0, length))):
            x0, y0, _ = vm.apply(0, 0, 0)
            x1, y1, _ = vm.apply(*end)
            res.append((name, col, (x0, y0), (x1, y1)))
        return res

    def pivot_2d(self):
        # центр поверхні
        total = self.model_matrix().multiply(self.view_matrix())
        return total.apply(*self.surface.center())[:2]

    def contour_pivot_2d(self):
        u, v = self.contour_pivot_uv()
        total = self.model_matrix().multiply(self.view_matrix())
        return total.apply(*self.surface.point(u, v))[:2]
