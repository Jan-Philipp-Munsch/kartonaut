"""Kleine CadQuery-Helfer und die Teileliste, die alle Module füllen."""
import math
import cadquery as cq
from cadquery import Vector


class Parts(list):
    """Liste von (name, shape, color_key, group). `shape` ist ein cq.Workplane oder cq.Shape."""

    def add(self, name, shape, color, group):
        if isinstance(shape, cq.Workplane):
            shape = shape.val()
        self.append((name, shape, color, group))
        return shape


def tube(od, id_, z0, z1, x=0.0, y=0.0):
    """Rohr um z von z0 bis z1."""
    w = cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(od / 2)
    if id_ > 0:
        w = w.circle(id_ / 2)
    return w.extrude(z1 - z0)


def cyl(d, z0, z1, x=0.0, y=0.0):
    return tube(d, 0, z0, z1, x, y)


def cyl_between(d, p0, p1):
    """Zylinder von Punkt p0 nach p1."""
    v = Vector(*p1) - Vector(*p0)
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(d / 2, v.Length, Vector(*p0), v.normalized()))


def box(lx, ly, lz, cx=0.0, cy=0.0, cz=0.0):
    """Quader mit Mittelpunkt (cx, cy, cz)."""
    return cq.Workplane("XY").box(lx, ly, lz).translate((cx, cy, cz))


def box_from(x0, x1, y0, y1, z0, z1):
    return box(x1 - x0, y1 - y0, z1 - z0, (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)


def rot_z(shape, deg):
    return shape.rotate((0, 0, 0), (0, 0, 1), deg)


def rot_about(shape, point, axis, deg):
    p = Vector(*point)
    return shape.rotate(p.toTuple(), (p + Vector(*axis)).toTuple(), deg)


def radial_holes(shape, d, r_out, z, n=4, phi0=45.0, depth=None):
    """n radiale Bohrungen Ø d auf Höhe z durch eine Wand bei r_out."""
    depth = depth or r_out
    for i in range(n):
        phi = math.radians(phi0 + 360.0 * i / n)
        p0 = (r_out * 1.2 * math.cos(phi), r_out * 1.2 * math.sin(phi), z)
        p1 = ((r_out * 1.2 - depth * 1.4) * math.cos(phi), (r_out * 1.2 - depth * 1.4) * math.sin(phi), z)
        shape = shape.cut(cyl_between(d, p0, p1))
    return shape
