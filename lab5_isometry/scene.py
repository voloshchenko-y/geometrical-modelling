from body import StarPrism
from geometry3d import (Mat4, isometry_matrix, isometry_angles, distortion_factors)

AXIS_COLORS = (("X", (230, 40, 40)), ("Y", (40, 190, 40)), ("Z", (40, 60, 230)))


class Scene:
    def __init__(self):
        self.body = StarPrism()
        self.pos = [0.0, 0.0, 0.0]  # зсув
        self.ang = [0.0, 0.0, 0.0]  # кути, °
        self.pivot_offset = [0.0, 0.0, 0.0]  # центр обертання
        self.alpha_sign = +1  # знак alpha
        self.beta = -45.0  # кут beta
        self.practical = False  # приведена

    # положення
    def reset_pose(self):
        self.pos = [0.0, 0.0, 0.0]
        self.ang = [0.0, 0.0, 0.0]

    def apply_offsets(self, dpos, dang):
        for i in range(3):
            self.pos[i] += dpos[i]
            self.ang[i] = (self.ang[i] + dang[i]) % 360.0

    def pivot_local(self):
        cx, cy, cz = self.body.center()
        return (cx + self.pivot_offset[0], cy + self.pivot_offset[1], cz + self.pivot_offset[2])

    def model_matrix(self):
        # матриця тіла
        cx, cy, cz = self.pivot_local()
        s = self.body.scale
        rot = (Mat4.rotation_x(self.ang[0])
               .multiply(Mat4.rotation_y(self.ang[1]))
               .multiply(Mat4.rotation_z(self.ang[2])))
        return (Mat4.translation(-cx, -cy, -cz)
                .multiply(Mat4.scaling(s, s, s))
                .multiply(rot)
                .multiply(Mat4.translation(cx, cy, cz))
                .multiply(Mat4.translation(*self.pos)))

    # проекція
    def view_matrix(self):
        return isometry_matrix(self.alpha_sign, self.beta, self.practical)

    def view_info(self):
        a, b = isometry_angles()
        u = distortion_factors(self.alpha_sign * a, self.beta)
        k = 1.0 / u[0] if self.practical else 1.0
        return {"alpha": self.alpha_sign * a, "beta": self.beta,
                "factors": tuple(f * k for f in u)}

    def world_vertices(self):
        mm = self.model_matrix()
        return [mm.apply(*v) for v in self.body.vertices()]

    def projected_vertices(self):
        total = self.model_matrix().multiply(self.view_matrix())
        return [total.apply(*v)[:2] for v in self.body.vertices()]

    def edges_2d(self):
        pv = self.projected_vertices()
        return [(pv[i], pv[j]) for i, j in self.body.edges()]

    def axes_2d(self, length):
        vm = self.view_matrix()
        res = []
        for (name, col), end in zip(AXIS_COLORS, ((length, 0, 0), (0, length, 0), (0, 0, length))):
            x0, y0, _ = vm.apply(0, 0, 0)
            x1, y1, _ = vm.apply(*end)
            res.append((name, col, (x0, y0), (x1, y1)))
        return res

    def pivot_world(self):
        return self.model_matrix().apply(*self.pivot_local())

    def pivot_2d(self):
        return self.view_matrix().apply(*self.pivot_world())[:2]
