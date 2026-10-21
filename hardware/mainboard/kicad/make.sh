#!/usr/bin/env bash
# Whole chain for mainboard rev B, from circuit.py to checked board and pictures (Git Bash on Windows).
#
#   ./make.sh          everything
#   ./make.sh sch      library, schematic, ERC, netlist check
#   ./make.sh pcb      board: place, route (Freerouting), zones, DRC
#   ./make.sh drc      DRC only
#   ./make.sh img      renders and layer plots
#
# kicad-cli is called from bash on purpose: started from the Microsoft-Store Python it does not find
# the global library tables (the Store app container hides them), so ERC and renders would be wrong.
set -euo pipefail
cd "$(dirname "$0")"
P="$LOCALAPPDATA/Programs"
CLI="$P/KiCad/10.0/bin/kicad-cli.exe"
KPY="$P/KiCad/10.0/bin/python.exe"
JAVA=$(ls "$P"/freerouting/jdk-25*/bin/java.exe | head -1)
JAR="$P/freerouting/freerouting-2.5.0.jar"
mkdir -p out img

sch() {
  python build_lib.py
  python gen_schematic.py
  "$CLI" sch erc --format report --exit-code-violations -o out/erc.rpt mainboard.kicad_sch
  "$CLI" sch export pdf -o out/mainboard_schematic.pdf mainboard.kicad_sch
  python check_design.py
}

route() {
  # 1. Freerouting on the placed board (deterministic: the same input gives the same result)
  "$KPY" gen_pcb.py dsn ""
  rm -f out/mainboard.ses
  "$JAVA" -jar "$JAR" --gui.enabled=false -de out/mainboard.dsn -do out/mainboard.ses     --router.autorouter.max_passes=100 > out/freerouting.log 2>&1 || true
  grep -E "Auto-routing stage completed" out/freerouting.log | sed 's/.*final score/  Freerouting: score/' | cut -c1-70 || true
  "$KPY" gen_pcb.py ses ""
  # 2. two finishing passes: existing wiring exported as fixed, only the open connections are routed
  #    and merged into the board (a plain second pass would rip everything up and end worse)
  for pass in 1 2; do
    "$KPY" gen_pcb.py dsn _fix
    sed -i 's/(type route))/(type fix))/' out/mainboard_fix.dsn
    rm -f out/mainboard_fix.ses
    "$JAVA" -jar "$JAR" --gui.enabled=false -de out/mainboard_fix.dsn -do out/mainboard_fix.ses       --router.autorouter.max_passes=100 > "out/freerouting_fix$pass.log" 2>&1 || true
    [ -f out/mainboard_fix.ses ] && "$KPY" gen_pcb.py merge _fix
  done
  # 3. close track ends left just short of their pad, collision-checked
  "$CLI" pcb drc --format json -o out/drc.json mainboard.kicad_pcb > /dev/null
  "$KPY" gen_pcb.py patch
}

drc() {
  "$CLI" pcb drc --format json --severity-all --schematic-parity -o out/drc.json mainboard.kicad_pcb > /dev/null
  "$CLI" pcb drc --format report --severity-all --schematic-parity -o out/drc.rpt mainboard.kicad_pcb > /dev/null
  python drc_summary.py
}

pcb() {
  "$KPY" gen_pcb.py place
  route                # a second Freerouting pass on a routed board starts over and ends worse
  drc
}

img() {
  # 3D renders (ray-traced) and one PDF per layer, cut and labelled by render.py
  "$CLI" pcb render --quality high --floor --background opaque --width 3200 --height 1700 --side top \
    --rotate 0,0,90 -o img/render_top.png mainboard.kicad_pcb
  "$CLI" pcb render --quality high --floor --background opaque --width 3200 --height 1700 --side bottom \
    --rotate 0,0,-90 -o img/render_bottom.png mainboard.kicad_pcb
  "$CLI" pcb render --quality high --floor --background opaque --width 2400 --height 1600 --side top \
    --perspective --zoom 1.6 --rotate -55,0,35 -o img/render_iso.png mainboard.kicad_pcb
  for l in "F_Cu:F.Cu,F.SilkS,Edge.Cuts" "In1_Cu:In1.Cu,Edge.Cuts" "In2_Cu:In2.Cu,Edge.Cuts" \
           "B_Cu:B.Cu,Edge.Cuts" "Bestueckung:F.SilkS,F.Fab,Edge.Cuts"; do
    "$CLI" pcb export pdf --layers "${l#*:}" --mode-single --drill-shape-opt 2 -o "img/_${l%%:*}.pdf" mainboard.kicad_pcb > /dev/null
  done
  python render.py
  rm -f img/_*.pdf
}

case "${1:-all}" in
  sch) sch ;;
  pcb) pcb ;;
  drc) drc ;;
  img) img ;;
  all) sch; pcb; img ;;
esac
