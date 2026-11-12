import math
import random

from contour import K_UV, rotate_about
from geometry3d import Mat4, distortion_factors, isometry_angles
from scene import Scene


def check(name, cond):
    print(("OK   " if cond else "FAIL ") + name)
    if not cond:
        raise SystemExit(1)


def close(a, b, eps=1e-9):
    return abs(a - b) < eps


def close3(p, q, eps=1e-7):
    return all(close(a, b, eps) for a, b in zip(p, q))


def inverse_model(sc):
    # M^-1 = T(-pos) T(-c) Rz(-az) Ry(-ay) Rx(-ax) T(c)
    c = sc.surface.center()
    return (Mat4.translation(*(-p for p in sc.pos))
            .multiply(Mat4.translation(*(-x for x in c)))
            .multiply(Mat4.rotation_z(-sc.ang[2]))
            .multiply(Mat4.rotation_y(-sc.ang[1]))
            .multiply(Mat4.rotation_x(-sc.ang[0]))
            .multiply(Mat4.translation(*c)))


def bbox_center(lines):
    pts = [p for line in lines for p in line]
    us = [p[0] for p in pts]
    vs = [p[1] for p in pts]
    return (min(us) + max(us)) / 2.0, (min(vs) + max(vs)) / 2.0


def main():
    random.seed(5)
    sc = Scene()
    s = sc.surface

    # 1) рівняння (6.9)
    ok = True
    for _ in range(100):
        u, v = random.uniform(-1.5, 1.5), random.uniform(-2, 2)
        x, y, z = s.point(u, v)
        ok = ok and close(x, s.A * v * math.cosh(u)) and close(z, s.B * v * math.sinh(u)) and close(y, s.C * u * u)
        if abs(v) > 1e-3:
            ok = ok and close((x / (s.A * v)) ** 2 - (z / (s.B * v)) ** 2, 1.0, 1e-7)
    check("точки поверхні збігаються з (6.9): x = A v ch u, z = B v sh u, y = C u^2; ch^2 - sh^2 = 1", ok)

    # 2) UV-сітка
    g = s.grid()
    nu = round((s.u_max - s.u_min) / s.mesh)
    nv = round((s.v_max - s.v_min) / s.mesh)
    check(f"UV-сітка: {len(g)} x {len(g[0])} вузлів, ліній {len(s.lines())}",
          len(g) == nu + 1 and len(g[0]) == nv + 1 and len(s.lines()) == (nu + 1) + (nv + 1))
    check("кути області: сітка починається в (u_min, v_min) і закінчується в (u_max, v_max)",
          close3(g[0][0], s.point(s.u_min, s.v_min)) and close3(g[-1][-1], s.point(s.u_max, s.v_max)))
    a0 = s.point(0.5, 1.0)
    s.A *= 2.0
    a1 = s.point(0.5, 1.0)
    s.A /= 2.0
    check("параметр A змінює лише x (подвоєння A подвоює x)", close(a1[0], 2 * a0[0]) and close(a1[1], a0[1]) and close(a1[2], a0[2]))

    # 3) XY -> UV
    c = sc.contour
    check("XY -> UV за формулою (6.16): u = x*(pi/6)/10, v = y*(pi/6)/10",
          close(K_UV, math.pi / 60.0) and close(c.uv0[0][0][0], c.xy[0][0][0] * math.pi / 60.0))
    check(f"контур: {len(c.arcs)} дуг, кінці вибірки збігаються з точками A та D",
          len(c.arcs) == 32 and all(close(c.xy[i][0][0], c.arcs[i][0][0]) and close(c.xy[i][-1][1], c.arcs[i][3][1])
                                    for i in range(len(c.arcs))))

    # 4) контур в UV: положення, масштаб, оберт навколо себе
    base = bbox_center(c.place((0.3, 0.7), 0.0, 1.0))
    check("центр контуру після розміщення збігається з pivot: " + f"({base[0]:.3f}; {base[1]:.3f})",
          close3(base + (0,), (0.3, 0.7, 0)))
    for ang in (30, 90, 217):
        ok = True
        pl0 = c.place((0.3, 0.7), 0.0, 1.0)
        pl1 = c.place((0.3, 0.7), ang, 1.0)
        c0 = c.center0
        shift = (0.3 - c0[0], 0.7 - c0[1])
        ctr = (c0[0] + shift[0], c0[1] + shift[1])
        for l0, l1 in zip(pl0, pl1):
            for p0, p1 in zip(l0, l1):
                ok = ok and close(math.dist(p0, ctr), math.dist(p1, ctr), 1e-9)
                ok = ok and close3(rotate_about(p0, ctr, ang) + (0,), p1 + (0,), 1e-9)
        check(f"оберт контуру на {ang} градусів навколо себе зберігає відстані до pivot", ok)
    pl2 = c.place((0.3, 0.7), 0.0, 2.0)
    ctr = (0.3, 0.7)
    check("масштаб 2 подвоює відстані до pivot",
          close(math.dist(pl2[3][4], ctr), 2 * math.dist(pl0[3][4], ctr)))

    # 5) контур на поверхні та евклідові перетворення
    sc.apply_offsets((40, -10, 25), (30, 70, 110))
    sc.apply_contour(0.15, -0.1, 35)
    uvs = sc.contour_uv()
    local = sc.contour_local()
    ok = all(close3(local[i][j], s.point(*uvs[i][j])) for i in range(len(uvs)) for j in range(len(uvs[i])))
    check("точки контуру лежать на поверхні: r = r(u, v) для кожної точки", ok)
    inv = inverse_model(sc)
    world = sc.contour_world()
    ok = all(close3(inv.apply(*world[i][j]), local[i][j], 1e-6) for i in range(len(world)) for j in range(len(world[i])))
    check("після зсуву й оберту поверхні M^-1 повертає контур на поверхню (контур лишається на ній)", ok)
    mm = sc.model_matrix()
    p0 = local[2][3]
    q0 = s.point(0.2, 0.3)
    check("евклідове перетворення — жорсткий рух: відстань контур-поверхня зберігається",
          close(math.dist(p0, q0), math.dist(mm.apply(*p0), mm.apply(*q0)), 1e-7))
    cen = mm.apply(*s.center())
    exp = tuple(a + b for a, b in zip(s.center(), sc.pos))
    check("центр поверхні при оберті лишається на місці (зсувається лише на pos)", close3(cen, exp))

    # 6) pivot контуру
    sc2 = Scene()
    pv = sc2.contour_pivot_uv()
    sc2.apply_contour(0.0, 0.0, 80)
    check("оберт контуру навколо себе не зсуває його pivot в UV", close3(sc2.contour_pivot_uv() + (0,), pv + (0,)))
    sc2.apply_contour(0.3, -0.2, 0)
    check("зсув контуру в UV на (0,3; -0,2) переносить pivot",
          close3(sc2.contour_pivot_uv() + (0,), (pv[0] + 0.3, pv[1] - 0.2, 0)))

    # 7) зміна параметра змінює поверхню разом із контуром
    sc3 = Scene()
    w0 = sc3.contour_local()[1][2]
    sc3.surface.C *= 1.5
    w1 = sc3.contour_local()[1][2]
    check("зміна C (анімація) переносить і контур: y точки контуру змінюється в 1,5 рази",
          close(w1[1], 1.5 * w0[1]) and close(w1[0], w0[0]))

    # 8) проекція з ЛР-5
    a, b = isometry_angles()
    f = distortion_factors(a, -45.0)
    check(f"ізометрія з ЛР-5: Ux = Uy = Uz = {f[0]:.4f}",
          close(f[0], f[1]) and close(f[1], f[2]) and close(f[0], math.sqrt(2 / 3)))
    pts = [p for line in sc3.mesh_2d() for p in line]
    check("проекція поверхні в площині z = 0: " + f"{len(pts)} точок з координатами (x', y')", len(pts) > 100)
    print("\nУсі перевірки пройдено.")


if __name__ == "__main__":
    main()
