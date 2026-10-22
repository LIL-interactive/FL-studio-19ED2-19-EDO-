import ast
import math
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import edo19  # noqa: E402


def ksp_trunc_div(a, b):
    """Целочисленное деление KSP (округление к нулю)."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


def ksp_simulate(note, a4_offset_mc, ref_key=69, mode=0):
    """Повторяет логику on note из KSP-скрипта."""
    target = ksp_trunc_div((note - ref_key) * 1200000, 19) + a4_offset_mc
    if mode == 0:
        if target >= 0:
            q = ksp_trunc_div(target + 50000, 100000)
        else:
            q = -ksp_trunc_div(50000 - target, 100000)
        key = min(127, max(0, 69 + q))
    else:
        key = note
    return key, target - (key - 69) * 100000


class TuningMath(unittest.TestCase):
    def test_reference_and_octave(self):
        for a4 in (440.0, 437.0):
            self.assertAlmostEqual(edo19.key_hz(69, a4), a4)
            self.assertAlmostEqual(edo19.key_hz(69 + 19, a4), 2 * a4)
            self.assertAlmostEqual(edo19.key_hz(69 - 19, a4), a4 / 2)

    def test_step_size(self):
        self.assertAlmostEqual(edo19.key_cents(70) - edo19.key_cents(69),
                               1200 / 19)

    def test_a437_offset(self):
        self.assertAlmostEqual(edo19.a4_offset_cents(437), -11.8443, places=3)

    def test_nearest_residual_bounded(self):
        for a4 in (440.0, 437.0):
            for k in range(128):
                m, res = edo19.nearest_12tet(k, a4)
                self.assertLessEqual(abs(res), 50.0)
                hz = 440 * 2 ** ((m - 69 + res / 100) / 12)
                self.assertAlmostEqual(hz, edo19.key_hz(k, a4), places=6)

    def test_note_names(self):
        self.assertEqual(edo19.note_name(69), "A4")
        self.assertEqual(edo19.note_name(55), "C4")
        self.assertEqual(edo19.note_name(74), "C5")
        self.assertEqual(edo19.note_name(56), "C#4")
        self.assertEqual(edo19.note_name(57), "Db4")


class Formats(unittest.TestCase):
    def test_scl(self):
        lines = [l for l in edo19.make_scl().splitlines()
                 if not l.startswith("!")]
        self.assertEqual(int(lines[1]), 19)
        pitches = lines[2:]
        self.assertEqual(len(pitches), 19)
        self.assertEqual(pitches[-1].strip(), "2/1")
        self.assertAlmostEqual(float(pitches[0]), 63.15789, places=4)

    def test_kbm(self):
        vals = [l for l in edo19.make_kbm(437.0).splitlines()
                if not l.startswith("!")]
        self.assertEqual(vals[:5], ["0", "0", "127", "69", "69"])
        self.assertAlmostEqual(float(vals[5]), 437.0)
        self.assertEqual(vals[6], "19")

    def test_tun(self):
        text = edo19.make_tun(437.0)
        exact = text.split("[Exact Tuning]")[1]
        m = re.search(r"note 69= ([\d.]+)", exact)
        base = float(re.search(r"basefreq= ([\d.]+)", exact).group(1))
        hz = base * 2 ** (float(m.group(1)) / 1200)
        self.assertAlmostEqual(hz, 437.0, places=4)

    def test_mts_syx(self):
        for a4 in (440.0, 437.0):
            syx = edo19.make_mts_syx(a4)
            self.assertEqual(len(syx), 408)
            self.assertEqual(syx[:5], bytes([0xF0, 0x7E, 0x7F, 0x08, 0x01]))
            self.assertEqual(syx[-1], 0xF7)
            self.assertTrue(all(b < 0x80 for b in syx[1:-1]))
            chk = 0
            for b in syx[1:-2]:
                chk ^= b
            self.assertEqual(syx[-2], chk & 0x7F)
            # нота 69 декодируется обратно в A
            off = 22 + 69 * 3
            xx, yy, zz = syx[off:off + 3]
            semis = xx + ((yy << 7) | zz) / 16384
            hz = 440 * 2 ** ((semis - 69) / 12)
            self.assertAlmostEqual(hz, a4, places=2)

    def test_csv(self):
        rows = edo19.make_csv(437.0).splitlines()
        self.assertEqual(len(rows), 129)
        self.assertTrue(rows[70].startswith("69;A5;A4;437.0000"))


class KontaktScript(unittest.TestCase):
    def test_ksp_math_matches_reference(self):
        for a4 in (440.0, 437.0, 415.0):
            off = edo19.millicents(edo19.a4_offset_cents(a4))
            for mode in (0, 1):
                for n in range(128):
                    key, tune_mc = ksp_simulate(n, off, mode=mode)
                    total_cents = (key - 69) * 100 + tune_mc / 1000
                    self.assertAlmostEqual(total_cents,
                                           edo19.key_cents(n, a4), delta=0.002)
                    if mode == 0:
                        self.assertLessEqual(abs(tune_mc), 50000)

    def test_ksp_structure(self):
        ksp = edo19.make_ksp(edo19.DEFAULT_A4_PRESETS, 440.0)
        self.assertEqual(ksp.count("on init"), 1)
        self.assertEqual(ksp.count("on note"), 1)
        self.assertEqual(ksp.count("end on"), 2)
        self.assertEqual(len(re.findall(r"^\s*if \(", ksp, re.M)),
                         len(re.findall(r"^\s*end if", ksp, re.M)))
        self.assertIn('"A4 = 437 Hz"', ksp)
        self.assertIn("-11844", ksp)

    def test_committed_ksp_up_to_date(self):
        path = os.path.join(ROOT, "kontakt", "19-EDO_Tuner.ksp.txt")
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(),
                             edo19.make_ksp(edo19.DEFAULT_A4_PRESETS, 440.0))


class FlScripts(unittest.TestCase):
    def _load(self, rel, module_name):
        """Исполняет скрипт FL с заглушкой модуля flvfx/flpianoroll."""
        import types
        stub = types.ModuleType(module_name)

        class Voice:
            def __init__(self, other=None):
                self.note = other.note if other else 60.0

        stub.Voice = Voice
        sys.modules[module_name] = stub
        ns = {}
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            src = f.read()
        ast.parse(src)
        exec(compile(src, rel, "exec"), ns)
        return ns

    def test_vfx_mapping(self):
        ns = self._load("fl_studio/VFX Script/19-EDO Retuner.py", "flvfx")
        for a4 in (440.0, 437.0):
            for n in (0, 50, 69, 88, 127):
                note = ns["edo_to_note"](n, a4, 69)
                hz = 440 * 2 ** ((note - 69) / 12)
                self.assertAlmostEqual(hz, edo19.key_hz(n, a4), places=6)

    def test_pianoroll_mapping(self):
        ns = self._load("fl_studio/Piano roll scripts/19-EDO Convert.pyscript",
                        "flpianoroll")
        for a4 in (440.0, 437.0):
            for n in range(128):
                key, ofs = ns["convert"](n, a4, 69)
                cents = (key - 69) * 100 + ofs * 10
                self.assertLessEqual(abs(cents - edo19.key_cents(n, a4)), 5.0001)


if __name__ == "__main__":
    unittest.main()
