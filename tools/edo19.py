#!/usr/bin/env python3
"""19-EDO (19ED2) tuning toolkit generator.

Генерирует все файлы строя 19-EDO для FL Studio и плагинов:

  * Scala .scl  — сам строй (19 равных шагов на октаву 2/1);
  * Scala .kbm  — раскладка клавиш (линейная: каждая MIDI-клавиша = 1 шаг 19-EDO);
  * AnaMark .tun — таблица из 128 нот (для синтов, понимающих .tun);
  * MTS .syx    — MIDI Tuning Standard Bulk Dump (128 нот, SysEx);
  * .csv        — таблица «клавиша -> имя ноты 19-EDO -> Гц -> отклонение»;
  * Kontakt KSP — скрипт перестройки любого инструмента Kontakt.

Линейная раскладка: клавиша ``ref_key`` (по умолчанию 69, в FL Studio
она подписана как A5, в MIDI-стандарте — A4) звучит на частоте ``a4``,
каждая следующая клавиша выше на 1200/19 ≈ 63.158 цента.

Пример:
    python3 tools/edo19.py --a4 437 --out presets/A437
"""

from __future__ import annotations

import argparse
import math
import os
from typing import List, Sequence

EDO = 19
STEP_CENTS = 1200.0 / EDO
MIDI_A4 = 69
TET12_A4_HZ = 440.0
# Частота MIDI-ноты 0 в 12-TET при A4 = 440 Гц (база формата AnaMark .tun)
MIDI0_HZ = TET12_A4_HZ * 2 ** (-MIDI_A4 / 12)

# Имена 19 ступеней, начиная с C (диезы и бемоли в 19-EDO — разные ноты)
NOTE_NAMES_19 = [
    "C", "C#", "Db", "D", "D#", "Eb", "E", "E#/Fb", "F", "F#",
    "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B", "B#/Cb",
]
A_DEGREE = NOTE_NAMES_19.index("A")  # 14

# Пресеты эталона A4 для меню Kontakt-скрипта
DEFAULT_A4_PRESETS = [440.0, 437.0, 432.0, 442.0, 415.0]


# --------------------------------------------------------------------------
# Математика строя
# --------------------------------------------------------------------------

def a4_offset_cents(a4: float) -> float:
    """Смещение эталона A4 относительно 440 Гц в центах."""
    return 1200.0 * math.log2(a4 / TET12_A4_HZ)


def key_cents(key: int, a4: float = 440.0, ref_key: int = MIDI_A4) -> float:
    """Высота клавиши в центах относительно 12-TET MIDI 69 @ 440 Гц."""
    return (key - ref_key) * STEP_CENTS + a4_offset_cents(a4)


def key_hz(key: int, a4: float = 440.0, ref_key: int = MIDI_A4) -> float:
    return a4 * 2 ** ((key - ref_key) / EDO)


def nearest_12tet(key: int, a4: float = 440.0, ref_key: int = MIDI_A4):
    """Ближайшая 12-TET клавиша и остаток в центах (|остаток| <= 50)."""
    c = key_cents(key, a4, ref_key)
    semis = math.floor(c / 100.0 + 0.5)
    return MIDI_A4 + semis, c - semis * 100.0


def note_name(key: int, ref_key: int = MIDI_A4) -> str:
    """Имя ноты 19-EDO с номером октавы (C4..B#4 содержит A4)."""
    degree_from_c4 = (key - ref_key) + A_DEGREE
    octave = 4 + degree_from_c4 // EDO
    return f"{NOTE_NAMES_19[degree_from_c4 % EDO]}{octave}"


def fmt_hz(a4: float) -> str:
    return f"{a4:g}"


# --------------------------------------------------------------------------
# Файлы форматов
# --------------------------------------------------------------------------

def make_scl() -> str:
    lines = [
        "! 19-EDO.scl",
        "!",
        "19 equal divisions of the octave (19ED2 / 19-EDO / 19-TET)",
        f" {EDO}",
        "!",
    ]
    for i in range(1, EDO):
        lines.append(f" {i * STEP_CENTS:.5f}")
    lines.append(" 2/1")
    return "\n".join(lines) + "\n"


def make_kbm(a4: float, ref_key: int = MIDI_A4) -> str:
    lines = [
        f"! 19-EDO_A{fmt_hz(a4)}.kbm",
        "! Linear mapping: every MIDI key is one 19-EDO step.",
        f"! Key {ref_key} = A = {a4:.6f} Hz",
        "! Size of map (0 = linear, every key is the next scale degree):",
        "0",
        "! First MIDI note number to retune:",
        "0",
        "! Last MIDI note number to retune:",
        "127",
        "! Middle note where the first entry of the mapping is mapped to:",
        f"{ref_key}",
        "! Reference note for which frequency is given:",
        f"{ref_key}",
        "! Frequency to tune the above note to (floating point e.g. 440.0):",
        f"{a4:.6f}",
        "! Scale degree to consider as formal octave:",
        f"{EDO}",
        "! Mapping (none for a linear map)",
    ]
    return "\n".join(lines) + "\n"


def make_tun(a4: float, ref_key: int = MIDI_A4) -> str:
    name = f"19-EDO A={fmt_hz(a4)} Hz"
    out = [
        "; AnaMark tuning file (.tun)",
        f"; {name}, linear mapping, key {ref_key} = A",
        "[Scale Begin]",
        'Format= "AnaMark-TUN"',
        "FormatVersion= 200",
        'FormatSpecs= "http://www.mark-henning.de/eternity/tuningspecs.html"',
        "",
        "[Info]",
        f'Name= "{name}"',
        "",
        "[Tuning]",
    ]
    for k in range(128):
        out.append(f"note {k}= {round(key_cents(k, a4, ref_key) + MIDI_A4 * 100)}")
    out += ["", "[Exact Tuning]", f"basefreq= {MIDI0_HZ:.10f}"]
    for k in range(128):
        out.append(f"note {k}= {key_cents(k, a4, ref_key) + MIDI_A4 * 100:.6f}")
    out += ["", "[Scale End]", ""]
    return "\n".join(out)


def mts_bytes_for_cents(abs_cents: float) -> List[int]:
    """Кодирование частоты в 3 байта MTS (полутон + 14 бит доли полутона)."""
    semis = abs_cents / 100.0
    if semis <= 0:
        return [0, 0, 0]
    if semis >= 127 + 16383 / 16384:
        return [127, 127, 126]  # 0x7F7F7F зарезервировано как «без изменений»
    base = int(math.floor(semis))
    frac = int(round((semis - base) * 16384))
    if frac == 16384:
        base, frac = base + 1, 0
    return [base, (frac >> 7) & 0x7F, frac & 0x7F]


def make_mts_syx(a4: float, ref_key: int = MIDI_A4, program: int = 0,
                 device_id: int = 0x7F) -> bytes:
    """MIDI Tuning Standard: Bulk Tuning Dump (F0 7E dev 08 01 ...)."""
    name = f"19-EDO A{fmt_hz(a4)}"[:16].ljust(16)
    body = [0x7E, device_id & 0x7F, 0x08, 0x01, program & 0x7F]
    body += [ord(c) & 0x7F for c in name]
    for k in range(128):
        body += mts_bytes_for_cents(key_cents(k, a4, ref_key) + MIDI_A4 * 100)
    checksum = 0
    for b in body:
        checksum ^= b
    return bytes([0xF0] + body + [checksum & 0x7F, 0xF7])


def make_csv(a4: float, ref_key: int = MIDI_A4) -> str:
    rows = ["midi_key;fl_studio_label;edo19_note;freq_hz;cents_from_A440;"
            "nearest_12tet_key;fine_cents"]
    fl_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    for k in range(128):
        m, res = nearest_12tet(k, a4, ref_key)
        fl_label = f"{fl_names[k % 12]}{k // 12}"  # в FL Studio 60 = C5
        rows.append(f"{k};{fl_label};{note_name(k, ref_key)};"
                    f"{key_hz(k, a4, ref_key):.4f};"
                    f"{key_cents(k, a4, ref_key):.3f};{m};{res:+.3f}")
    return "\n".join(rows) + "\n"


def millicents(cents: float) -> int:
    return int(round(cents * 1000))


def make_ksp(a4_presets: Sequence[float], default_a4: float) -> str:
    """KSP-скрипт для Kontakt 5/6/7/8 (вставляется в слот Script Editor)."""
    presets = list(dict.fromkeys(list(a4_presets) + [default_a4]))
    default_idx = presets.index(default_a4)
    offsets = ", ".join(str(millicents(a4_offset_cents(f))) for f in presets)
    menu = "\n".join(
        f'    add_menu_item($A4, "A4 = {fmt_hz(f)} Hz", {i})'
        for i, f in enumerate(presets))
    return f"""{{ ===================================================================
  19-EDO (19ED2) Tuner for Kontakt
  Generated by tools/edo19.py  -- github: FL-studio-19ED2-19-EDO-

  Each MIDI key = one 19-EDO step (1200/19 = 63.158 cents).
  "Ref key" (default 69 = A4 MIDI / A5 in FL Studio) sounds at the
  A4 frequency chosen in the menu.

  Mode "Remap + fine tune": the note is moved to the nearest 12-TET key
  (so the closest sample is used, max +-50 cents of re-pitching).
  Mode "Tune in place": the original key is kept and re-pitched
  (use it for legato / keyswitch scripts that need original note numbers).

  Put this script into the LAST free script slot of the instrument,
  after the library's own scripts.
  The instrument itself must be tuned to A4 = 440 Hz (Kontakt default).
=================================================================== }}

on init
    set_script_title("19-EDO Tuner")
    message("")

    declare const $EDO := 19
    declare %a4_offset_mc[{len(presets)}] := ({offsets})

    declare ui_menu $A4
{menu}
    $A4 := {default_idx}

    declare ui_menu $Mode
    add_menu_item($Mode, "Remap + fine tune", 0)
    add_menu_item($Mode, "Tune in place", 1)

    declare ui_value_edit $RefKey (0, 127, 1)
    $RefKey := {MIDI_A4}

    declare ui_switch $Bypass

    make_persistent($A4)
    make_persistent($Mode)
    make_persistent($RefKey)
    make_persistent($Bypass)

    declare $target
    declare $q
    declare $key
    declare $new_id
end on

on note
    if ($Bypass = 0)
        {{ target pitch in millicents relative to MIDI 69 @ 440 Hz }}
        $target := (($EVENT_NOTE - $RefKey) * 1200000) / $EDO + %a4_offset_mc[$A4]

        if ($Mode = 0)
            {{ round to the nearest semitone (KSP integer division truncates) }}
            if ($target >= 0)
                $q := ($target + 50000) / 100000
            else
                $q := -((50000 - $target) / 100000)
            end if
            $key := 69 + $q
            if ($key < 0)
                $key := 0
            end if
            if ($key > 127)
                $key := 127
            end if
        else
            $key := $EVENT_NOTE
        end if

        if ($key = $EVENT_NOTE)
            change_tune($EVENT_ID, $target - ($EVENT_NOTE - 69) * 100000, 0)
        else
            ignore_event($EVENT_ID)
            $new_id := play_note($key, $EVENT_VELOCITY, 0, -1)
            change_tune($new_id, $target - ($key - 69) * 100000, 0)
        end if
    end if
end on
"""


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def write(path: str, data, binary: bool = False) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if binary:
        with open(path, "wb") as f:
            f.write(data)
    else:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(data)
    print(f"  {path}")


def generate(out_dir: str, a4: float, ref_key: int = MIDI_A4) -> None:
    tag = f"A{fmt_hz(a4)}"
    write(os.path.join(out_dir, "19-EDO.scl"), make_scl())
    write(os.path.join(out_dir, f"19-EDO_{tag}.kbm"), make_kbm(a4, ref_key))
    write(os.path.join(out_dir, f"19-EDO_{tag}.tun"), make_tun(a4, ref_key))
    write(os.path.join(out_dir, f"19-EDO_{tag}.syx"),
          make_mts_syx(a4, ref_key), binary=True)
    write(os.path.join(out_dir, f"19-EDO_{tag}_table.csv"), make_csv(a4, ref_key))


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="19-EDO tuning file generator")
    p.add_argument("--a4", type=float, default=440.0,
                   help="частота ноты A на опорной клавише, Гц (напр. 437)")
    p.add_argument("--ref-key", type=int, default=MIDI_A4,
                   help="MIDI-клавиша, звучащая как A (по умолчанию 69)")
    p.add_argument("--out", default=None, help="папка для файлов строя")
    p.add_argument("--ksp", default=None,
                   help="путь для KSP-скрипта Kontakt (необязательно)")
    args = p.parse_args(argv)

    if not 0 <= args.ref_key <= 127:
        p.error("--ref-key должен быть в диапазоне 0..127")
    if not 100.0 <= args.a4 <= 1000.0:
        p.error("--a4 должен быть в диапазоне 100..1000 Гц")

    out = args.out or os.path.join("presets", f"A{fmt_hz(args.a4)}")
    print(f"19-EDO, A = {args.a4} Hz на клавише {args.ref_key}:")
    generate(out, args.a4, args.ref_key)
    if args.ksp:
        write(args.ksp, make_ksp(DEFAULT_A4_PRESETS, args.a4))


if __name__ == "__main__":
    main()
