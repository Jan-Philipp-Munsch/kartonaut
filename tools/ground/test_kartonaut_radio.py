"""Tests des Laptop-Protokolls gegen die festen Bytefolgen der Firmware-Tests.

    python -m pytest -q tools/ground

firmware/test/data/radio_vectors.csv wird auch von firmware/test/test_native/test_radio_vectors.cpp
geprüft; die Eingaben hier sind dieselben (Schlüssel 00 01 .. 0f, Raketen-ID 1).
"""
import json
import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kartonaut_radio as kr  # noqa: E402

VECTORS = os.path.join(kr.REPO, "firmware", "test", "data", "radio_vectors.csv")
KEY = bytes(range(16))


def vectors():
    out = {}
    with open(VECTORS, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            name, hx = line.strip().split(",")
            out[name] = bytes.fromhex(hx)
    return out


V = vectors()


def built():
    """Dieselben Rahmen wie build() in test_radio_vectors.cpp, mit dem Python-Code gebaut."""
    return {
        "cmd_arm": kr.auth_cmd(kr.CMD_ARM, 7, 0x12345678, KEY, 1),
        "cmd_launch": kr.auth_cmd(kr.CMD_LAUNCH, 8, 0xCAFEBABE, KEY, 1),
        "cmd_heartbeat": kr.cmd(kr.CMD_HEARTBEAT, 9),
        "cmd_abort": kr.cmd(kr.CMD_ABORT, 10),
        "cmd_ping": kr.cmd(kr.CMD_PING, 11),
        "ack_ping": kr.encode(kr.ACK, struct.pack("<BBBBIBH", kr.CMD_PING, 11, kr.ACK_OK, 1, 0x12345678, 0x5F, 0)),
        "ack_arm": kr.encode(kr.ACK, struct.pack("<BBBBIBH", kr.CMD_ARM, 7, kr.ACK_OK, 9, 0xCAFEBABE, 0x7F, 0)),
        "ack_launch": kr.encode(kr.ACK, struct.pack("<BBBBIBH", kr.CMD_LAUNCH, 8, kr.ACK_OK, 10, 0, 0x7F, 5000)),
        "ack_safe": kr.encode(kr.ACK, bytes([kr.CMD_SAFE, 12, kr.ACK_REFUSED, 12])),
        "evt_ignition": kr.encode(kr.EVT, struct.pack("<IBBB", 1234, 10, 11, 19)),
        "ign": kr.encode(kr.IGN, struct.pack("<HHHHHHHHB", 10, 50, 130, 50, 7800, 6912, 3900, 80, 2)),
        "tlm_armed": kr.encode(kr.TLM, struct.pack("<BBHhhbbbbbBBB", 9, 0x0B, 4321, -12, 3, -4, 6, 45, 0, -1,
                                                   200, 160, 33)),
        "bridge_config": kr.encode(kr.BRIDGE_CONFIG),
        "bridge_ack": kr.encode(kr.BRIDGE_ACK, bytes([0]) + kr.e22_registers(kr.read_config_h(), True)),
    }


def test_crc_check_value():
    assert kr.crc16_ccitt(b"123456789") == 0x29B1


@pytest.mark.parametrize("name", sorted(built()))
def test_encode_matches_firmware_vectors(name):
    assert built()[name] == V[name], name


def test_all_vectors_covered():
    assert set(built()) == set(V)


def test_decode_vectors():
    p = kr.Parser()
    frames = p.feed(b"".join(V[n] for n in V))
    assert len(frames) == len(V) and p.bad == 0
    got = [kr.decode(t, pl) for t, pl in frames]
    names = list(V)
    by = dict(zip(names, got))
    assert by["ack_arm"]["nonce"] == 0xCAFEBABE and by["ack_arm"]["precond"] == kr.PRE_ALL
    assert by["ack_launch"]["countdown_ms"] == 5000 and kr.state_name(by["ack_launch"]["state"]) == "COUNTDOWN"
    assert by["ack_safe"] == {"cmd": kr.CMD_SAFE, "seq": 12, "result": kr.ACK_REFUSED, "state": 12}
    assert kr.state_name(by["evt_ignition"]["to"]) == "IGNITION"
    assert kr.reason_name(by["evt_ignition"]["reason"]) == "COUNTDOWN_END"
    ign = by["ign"]
    assert (ign["t_pulse_on_ms"], ign["t_cont_lost_ms"], ign["t_thrust_ms"]) == (10, 50, 130)
    assert ign["arm_min_mv"] == 6912 and ign["end_reason"] == 2
    assert "Durchgang weg 50 ms" in kr.ign_text(ign)
    tlm = by["tlm_armed"]
    assert kr.state_name(tlm["state"]) == "ARMED" and tlm["alt_m"] == pytest.approx(-1.2)
    assert tlm["vbat2_V"] == pytest.approx(8.0) and tlm["roll_deg"] == 90
    assert by["cmd_heartbeat"] == {"seq": 9}
    assert by["bridge_config"] == {}
    assert by["bridge_ack"]["result"] == 0 and "9,6 kbit/s" in kr.describe_e22(by["bridge_ack"]["regs"])


def test_mac_matches_and_rejects():
    mac = kr.compute_mac(KEY, kr.CMD_ARM, 7, 0x12345678, 1)
    assert V["cmd_arm"][5:13] == mac
    assert kr.compute_mac(KEY, kr.CMD_ARM, 7, 0x12345679, 1) != mac       # andere nonce
    assert kr.compute_mac(KEY, kr.CMD_LAUNCH, 7, 0x12345678, 1) != mac    # anderer Typ
    assert kr.compute_mac(bytes(16), kr.CMD_ARM, 7, 0x12345678, 1) != mac  # anderer Schlüssel


def test_parser_resync_rssi_and_corruption():
    bad = bytearray(V["cmd_abort"])
    bad[4] ^= 1
    p = kr.Parser(rssi_byte=True)
    frames = p.feed(b"\x00\xA5\x13" + bytes(bad) + V["tlm_armed"] + b"\xC4" + V["cmd_ping"])
    assert [t for t, _ in frames] == [kr.TLM, kr.CMD_PING]
    assert p.bad >= 1
    assert p.rssi_dbm == -60
    # stückweise wie am Stück
    q = kr.Parser()
    out = []
    for b in V["ign"]:
        out += q.feed(bytes([b]))
    assert len(out) == 1 and out[0][0] == kr.IGN


def test_missing_preconds_text():
    assert kr.missing_preconds(kr.PRE_ALL) == []
    miss = kr.missing_preconds(kr.PRE_ALL & ~0x02 & ~0x40)
    assert len(miss) == 2 and "Durchgang" in miss[0] and "Schlüssel" in miss[1]


def test_config_h_and_e22_registers():
    cfg = kr.read_config_h()
    assert cfg["ROCKET_ID"] == 1 and cfg["LAUNCH_CH"] == 0 and cfg["HEARTBEAT_TIMEOUT_MS"] == 1000
    assert cfg["RADIO_BAUD"] == 9600
    # gleiche Bytes wie e22_registers_from_config() in test_radio_vectors.cpp
    assert kr.e22_registers(cfg, False) == bytes([0x00, 0x00, 0x00, 0x64, 0x03, 0x17, 0x03, 0x00, 0x00])
    assert kr.e22_registers(cfg, True)[6] == 0x83


def test_load_key(tmp_path):
    good = tmp_path / "s.json"
    good.write_text(json.dumps({"key": KEY.hex()}))
    assert kr.load_key(str(good)) == KEY
    zero = tmp_path / "z.json"
    zero.write_text(json.dumps({"key": "00" * 16}))
    with pytest.raises(ValueError):
        kr.load_key(str(zero))
    short = tmp_path / "k.json"
    short.write_text(json.dumps({"key": "0102"}))
    with pytest.raises(ValueError):
        kr.load_key(str(short))


def test_example_secrets_is_template():
    with open(os.path.join(kr.HERE, "secrets.example.json"), encoding="utf-8") as f:
        assert bytes.fromhex(json.load(f)["key"]) == bytes(16)
