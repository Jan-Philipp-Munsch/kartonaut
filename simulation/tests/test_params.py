import json
import math

import pytest

from tvcsim.params import CAD_MASS_FILE, FUEL_PER_MOTOR_KG, VehicleParams


def test_cad_vehicle_from_file(tmp_path):
    """Achsentausch CAD (z laengs) -> Simulink (x laengs), m_dry = Masse - 28 g, l = Hebelarm."""
    data = {"configurations": {"liftoff": {
        "mass_kg": 0.981, "lever_arm_m": 0.3718, "cg_lateral_m": [0.00024, -0.00065],
        "inertia_kgm2": {"Ixx": 0.1096, "Iyy": 0.1097, "Izz": 0.00105}}}}
    p = tmp_path / "mass.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    v = VehicleParams.cad(path=p)
    assert math.isclose(v.Ix, 0.00105) and math.isclose(v.Iy, 0.1096) and math.isclose(v.Iz, 0.1097)
    assert math.isclose(v.l, 0.3718) and math.isclose(v.l_ctrl, 0.3718)
    assert math.isclose(v.m_dry, 0.981 - FUEL_PER_MOTOR_KG)
    assert math.isclose(v.mis_y, 0.00024) and math.isclose(v.mis_z, -0.00065)


@pytest.mark.skipif(not CAD_MASS_FILE.exists(), reason="cad/mass_properties.json nicht im Checkout")
def test_cad_vehicle_repo_file_plausible():
    v = VehicleParams.cad()
    assert 0.8 < v.m_dry < 1.1
    assert v.Iy > 10 * v.Ix            # schlanker Koerper: quer viel groesser als laengs
    assert 0.3 < v.l < 0.45
