import itertools
import math
import random

from body import StarPrism
from geometry3d import (Mat4, BETA_CHOICES, distortion_factors, isometry_angles,
                        isometry_matrix, trimetry_matrix)
from scene import Scene


def check(name, cond):
    print(("OK   " if cond else "FAIL ") + name)
    if not cond:
        raise SystemExit(1)


def close(a, b, eps=1e-9):
    return abs(a - b) < eps


def det3(m):
    a = [[m.m[i * 4 + j] for j in range(3)] for i in range(3)]
    return (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
            - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
            + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))


def angle_between(u, v):
    c = (u[0] * v[0] + u[1] * v[1]) / (math.hypot(*u) * math.hypot(*v))
    return math.degrees(math.acos(c))


def main():
    random.seed(3)

    # 1) (5.9)
    ok = True
    for _ in range(50):
        a, b = random.uniform(-90, 90), random.uniform(-180, 180)
        sa, ca = math.sin(math.radians(a)), math.cos(math.radians(a))
        sb, cb = math.sin(math.radians(b)), math.cos(math.radians(b))
        expected = [cb, sb * sa, 0, 0,
                    0, ca, 0, 0,
                    sb, -sa * cb, 0, 0,
                    0, 0, 0, 1]
        got = trimetry_matrix(a, b).m
        ok = ok and all(close(x, y) for x, y in zip(got, expected))
    check("Ry(b) * Rx(a) * Pz збігається з матрицею (5.9) методички на 50 випадкових кутах", ok)

    # 2) кути
    a0, b0 = isometry_angles()
    ux, uy, uz = distortion_factors(a0, b0)
    check(f"кути ізометрії: alpha = {a0:.4f}, beta = {b0:.4f}", close(a0, 35.26438968, 1e-6) and close(b0, 45.0))
    check(f"Ux = Uy = Uz = sqrt(2/3) = {math.sqrt(2 / 3):.6f} (є {ux:.6f}; {uy:.6f}; {uz:.6f})",
          close(ux, uy) and close(uy, uz) and close(ux, math.sqrt(2 / 3)))

    # 3) 120 градусів
    m = isometry_matrix(+1, -45.0)
    axes = [m.apply(*e)[:2] for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
    angs = [angle_between(axes[i], axes[j]) for i, j in ((0, 1), (1, 2), (0, 2))]
    check("проекції осей X, Y, Z утворюють кути 120 градусів: " + ", ".join(f"{x:.3f}" for x in angs),
          all(close(x, 120.0, 1e-6) for x in angs))

    # 4) 8 напрямів
    ok = True
    for sign, beta, practical in itertools.product((+1, -1), BETA_CHOICES, (False, True)):
        mm = isometry_matrix(sign, beta, practical)
        pr = [mm.apply(*e)[:2] for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
        lens = [math.hypot(*p) for p in pr]
        target = 1.0 if practical else math.sqrt(2 / 3)
        ok = ok and all(close(l, target, 1e-9) for l in lens)
        # 60 або 120
        ok = ok and all(close(abs(math.cos(math.radians(angle_between(pr[i], pr[j])))), 0.5, 1e-9)
                        for i, j in ((0, 1), (1, 2), (0, 2)))
    check("усі 8 напрямів погляду x теоретична/приведена: довжини проекцій осей однакові "
          "(sqrt(2/3) або 1.0), кути між осями 60/120", ok)

    # 5) z = 0
    ok = all(close(m.apply(random.uniform(-9, 9), random.uniform(-9, 9), random.uniform(-9, 9))[2], 0.0)
             for _ in range(100))
    check("після проекціювання координата z = 0", ok)

    # 6) оберти
    ok = True
    for rot in (Mat4.rotation_x(37), Mat4.rotation_y(-81), Mat4.rotation_z(123)):
        rt = rot.transposed()
        prod = rot.multiply(rt)
        ok = ok and all(close(prod.m[i], Mat4.identity().m[i]) for i in range(16)) and close(det3(rot), 1.0)
    check("матриці обертів ортогональні (R * R^T = E), det = 1", ok)

    sc = Scene()
    sc.ang = [30.0, 70.0, 110.0]
    sc.pos = [10.0, -4.0, 7.0]
    sc.body.scale = 1.7
    c = sc.pivot_local()
    cw = sc.model_matrix().apply(*c)
    exp = (c[0] + 10.0, c[1] - 4.0, c[2] + 7.0)
    check("центр обертання (точка всередині фігури) при оберті та масштабі лишається на місці: "
          f"({cw[0]:.3f}; {cw[1]:.3f}; {cw[2]:.3f})", all(close(a, b, 1e-9) for a, b in zip(cw, exp)))

    # 7) приклад з умови
    sc = Scene()
    v0 = sc.world_vertices()
    c0 = sc.body.center()
    sc.apply_offsets((100.0, 100.0, 0.0), (0.0, 90.0, 0.0))
    v1 = sc.world_vertices()
    ok = True
    for (x0, y0, z0), (x1, y1, z1) in zip(v0, v1):
        # оберт Y на 90
        dx, dz = x0 - c0[0], z0 - c0[2]
        ex, ez = c0[0] + dz + 100.0, c0[2] - dx
        ok = ok and close(x1, ex, 1e-9) and close(y1, y0 + 100.0, 1e-9) and close(z1, ez, 1e-9)
    check("зсув на 100 по X та Y і оберт навколо власної осі Y на 90: усі вершини збігаються з розрахунком", ok)

    # жорсткий рух
    sc = Scene()
    sc.ang = [41.0, 17.0, 63.0]
    cw = sc.model_matrix().apply(*sc.pivot_local())
    ok = all(close(math.dist(w, cw), math.dist(l, sc.pivot_local()), 1e-9)
             for w, l in zip(sc.world_vertices(), sc.body.vertices()))
    check("оберт — жорсткий рух: відстані до центра обертання зберігаються", ok)

    # 8) тіло
    b = StarPrism()
    check(f"зірчаста призма n = {b.n}: {len(b.vertices())} вершин, {len(b.edges())} ребер (6n)",
          len(b.vertices()) == 4 * b.n and len(b.edges()) == 6 * b.n)
    ok = True
    for n in range(3, 13):
        b.n = n
        ok = ok and len(b.edges()) == 6 * n and len(set(b.vertices())) == 4 * n
    check("кількість ребер = 6n для n = 3..12, вершини не збігаються", ok)
    b.n, b.height, b.width, b.depth = 5, 100.0, 80.0, 40.0
    xs = [v[0] for v in b.vertices()]
    ys = [v[1] for v in b.vertices()]
    zs = [v[2] for v in b.vertices()]
    check("зміна параметрів: висота 100, ширина <= 80, глибина <= 40 (габарити змінилися)",
          close(max(ys) - min(ys), 100.0) and (max(xs) - min(xs)) <= 80.0 + 1e-9 and (max(zs) - min(zs)) <= 40.0 + 1e-9)
    print("\nУсі перевірки пройдено.")


if __name__ == "__main__":
    main()
