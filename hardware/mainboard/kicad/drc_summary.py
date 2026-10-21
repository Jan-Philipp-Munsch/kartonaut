"""Short summary of out/drc.json (written by make.sh drc)."""
import json
from collections import Counter
from pathlib import Path

d = json.loads((Path(__file__).resolve().parent / "out" / "drc.json").read_text(encoding="utf-8"))
print("DRC:", dict(Counter(f"{v['type']} ({v['severity']})" for v in d["violations"])))
print("nicht verbunden:", len(d["unconnected_items"]), "| Paritaet Schaltplan:", len(d.get("schematic_parity", [])))
for u in d["unconnected_items"]:
    print("   ", " / ".join(i["description"][:70] for i in u["items"]))
for p in d.get("schematic_parity", [])[:10]:
    print("    Paritaet:", p["description"][:110])
