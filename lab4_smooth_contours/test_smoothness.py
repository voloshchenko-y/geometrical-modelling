import math
import os
import random

from bezier import Contour, engineering_point, handle_index
from geometry import Mat3

HERE = os.path.dirname(os.path.abspath(__file__))


def end_tangent(c, i, k, h=1e-6):
    u = h if k == 0 else 1.0 - h
    u0 = 0.0 if k == 0 else 1.0
    p0 = engineering_point(c.pts[i], c.w[i], u0)
    p1 = engineering_point(c.pts[i], c.w[i], u)
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    n = math.hypot(dx, dy)
    return dx / n, dy / n


def tangent_deviation(c, j):
    (i1, k1), (i2, k2) = c.joints[j]
    t1, t2 = end_tangent(c, i1, k1), end_tangent(c, i2, k2)
    return math.hypot(t1[0] + t2[0], t1[1] + t2[1])


def check(name, cond):
    print(("OK   " if cond else "FAIL ") + name)
    if not cond:
        raise SystemExit(1)


def main():
    c = Contour.load(os.path.join(HERE, "duck_contour.json"))
    check(f"стикових точок = 18 (є {len(c.joints)})", len(c.joints) == 18)
    check(f"вузлових = 15 (є {c.smooth_count()}), точок зламу = 3 (є {c.break_count()})",
          c.smooth_count() == 15 and c.break_count() == 3)
    check("початкові вузлові точки мають збіжні дотичні",
          all(tangent_deviation(c, j) < 1e-4 for j in range(len(c.joints)) if c.smooth[j]))

    # ваги
    random.seed(7)
    for w in c.w:
        for k in range(4):
            w[k] = random.uniform(0.3, 4.0)

    # 2) ручка
    j = next(j for j in range(len(c.joints)) if c.smooth[j])
    (i1, k1), (i2, k2) = c.joints[j]
    len_before = math.hypot(*c.handle_vector(i2, k2))
    for _ in range(200):
        hp = c.pts[i1][handle_index(k1)]
        c.move_point(i1, handle_index(k1), hp[0] + random.uniform(-3, 3), hp[1] + random.uniform(-3, 3))
        assert tangent_deviation(c, j) < 1e-4, tangent_deviation(c, j)
    len_after = math.hypot(*c.handle_vector(i2, k2))
    check("вузлова точка: після 200 випадкових зсувів ручки дотичні збігаються", True)
    check(f"довжина протилежної ручки збережена ({len_before:.6f} → {len_after:.6f})",
          abs(len_before - len_after) < 1e-9)
    check("кут між ручками = 180°", abs(c.joint_angle(j) - 180.0) < 1e-6)

    # 3) злам
    jb = next(j for j in range(len(c.joints)) if not c.smooth[j])
    (b1, bk1), (b2, bk2) = c.joints[jb]
    opp_before = list(c.pts[b2][handle_index(bk2)])
    hp = c.pts[b1][handle_index(bk1)]
    c.move_point(b1, handle_index(bk1), hp[0] + 2.5, hp[1] - 1.5)
    opp_after = c.pts[b2][handle_index(bk2)]
    check("точка зламу: протилежна реперна точка не змінила положення", opp_before == opp_after)
    check(f"точка зламу: кут між ручками ≠ 180° ({c.joint_angle(jb):.1f}°)", abs(c.joint_angle(jb) - 180.0) > 1.0)

    # 4) перемикання
    c.toggle_joint(jb)
    check("перемикання: точка зламу → вузлова, ручки вирівняно одразу",
          c.smooth[jb] and tangent_deviation(c, jb) < 1e-4 and abs(c.joint_angle(jb) - 180.0) < 1e-6)
    # назад
    c.toggle_joint(jb)
    hp = c.pts[b1][handle_index(bk1)]
    opp_before = list(c.pts[b2][handle_index(bk2)])
    c.move_point(b1, handle_index(bk1), hp[0] - 1.0, hp[1] + 3.0)
    check("вузлова → точка зламу: гладкість знову не забезпечується",
          (not c.smooth[jb]) and c.pts[b2][handle_index(bk2)] == opp_before)
    c.toggle_joint(jb)

    # 5) вузол
    (n1, nk1), (n2, nk2) = c.joints[j]
    node = c.pts[n1][nk1]
    for _ in range(100):
        node = c.pts[n1][nk1]
        c.move_point(n1, nk1, node[0] + random.uniform(-2, 2), node[1] + random.uniform(-2, 2))
        assert c.pts[n1][nk1] == c.pts[n2][nk2], "кінці розійшлися"
        assert tangent_deviation(c, j) < 1e-4
    check("рух вузлової точки: кінці дуг збігаються, гладкість збережена", True)

    # 6) оберт
    c.transform(Mat3.rotation(37.0, 3.0, -2.0))
    c.transform(Mat3.translation(4.0, -3.0))
    check("після оберту та зсуву всі вузлові точки лишаються гладкими",
          all(tangent_deviation(c, j) < 1e-4 for j in range(len(c.joints)) if c.smooth[j]))

    # копія
    d = c.copy()
    check("copy() зберігає типи стикових точок", d.smooth == c.smooth and d.joints == c.joints)
    print("\nУсі перевірки пройдено.")


if __name__ == "__main__":
    main()
