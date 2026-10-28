"""STL (binär oder ASCII) nach Wavefront OBJ umwandeln, ohne Zusatzbibliothek.

    python cad/tools/stl_to_obj.py cad/export/modular/*.stl              # OBJ neben die STL
    python cad/tools/stl_to_obj.py -o /tmp/obj cad/export/modular/*.stl  # in einen Ordner

Gleiche Punkte werden zusammengefasst (auf 1 µm gerundet), damit Slicer und CAD das Netz als geschlossen
erkennen. Einheiten bleiben Millimeter wie in den STL aus cad/modular.py.
"""
import argparse
import os
import struct
import sys


def read_stl(path):
    with open(path, "rb") as f:
        data = f.read()
    tris = []
    if data[:5].lower() == b"solid" and b"facet" in data[:400]:
        verts = []
        for line in data.decode("ascii", errors="ignore").splitlines():
            parts = line.split()
            if parts[:1] == ["vertex"]:
                verts.append(tuple(float(x) for x in parts[1:4]))
                if len(verts) == 3:
                    tris.append(tuple(verts))
                    verts = []
        return tris
    n = struct.unpack_from("<I", data, 80)[0]
    for i in range(n):
        off = 84 + i * 50
        v = struct.unpack_from("<12f", data, off)
        tris.append(((v[3], v[4], v[5]), (v[6], v[7], v[8]), (v[9], v[10], v[11])))
    return tris


def write_obj(tris, path, name):
    index = {}
    verts = []
    faces = []
    for tri in tris:
        ids = []
        for p in tri:
            key = tuple(round(c, 3) for c in p)
            if key not in index:
                index[key] = len(verts) + 1
                verts.append(key)
            ids.append(index[key])
        if len(set(ids)) == 3:
            faces.append(ids)
    with open(path, "w", encoding="ascii") as f:
        f.write(f"# {name}, aus cad/ (Kartonaut), Einheit mm\n")
        f.write(f"o {name}\n")
        for v in verts:
            f.write(f"v {v[0]:.3f} {v[1]:.3f} {v[2]:.3f}\n")
        for a, b, c in faces:
            f.write(f"f {a} {b} {c}\n")
    return len(verts), len(faces)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("stl", nargs="+")
    ap.add_argument("-o", "--out-dir", help="Zielordner (Standard: neben der STL)")
    args = ap.parse_args(argv)
    if args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)
    for src in args.stl:
        name = os.path.splitext(os.path.basename(src))[0]
        dst = os.path.join(args.out_dir or os.path.dirname(src), name + ".obj")
        nv, nf = write_obj(read_stl(src), dst, name)
        print(f"{dst}: {nv} Punkte, {nf} Dreiecke")
    return 0


if __name__ == "__main__":
    sys.exit(main())
