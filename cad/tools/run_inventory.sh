#!/bin/bash
# Runs blender_inspect.py over the project's Blender files (local only, not in the repo).
# Output: JSON per file in $SCRATCH, PNG per file in docs/img/cad/blender_<name>.png
BLENDER="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
SRC="/d/Krams_aktuell_2026-08-16/Krams/Blender/Dateien"
REPO="/c/Users/Janmu/Gitlab/mission_space"
SCRATCH="${1:-$REPO/cad/export/inventory}"
mkdir -p "$SCRATCH" "$REPO/docs/img/cad"
FILES="model_rocket flight_computer flight_computer_obj TVC TVC_V2 Inner_gimbal Inner_gimbal_V2 dual_tvc inner_gimbal_dual_TVC outer_gimbal_dual_TVC LegConnectors rocket_nose flywheel flywheelV2 untitled test123"
for name in $FILES; do
  src="$SRC/$name.blend"
  [ "$name" = "rocket_nose" ] && src="$SRC/rocket nose.blend"
  echo "=== $name"
  "$BLENDER" -b "$src" --python "$REPO/cad/tools/blender_inspect.py" -- "$SCRATCH/$name.json" "$REPO/docs/img/cad/blender_$name.png" 2>&1 | grep -E "INSPECT_OK|Error|Traceback|Saved" | head -5
done
