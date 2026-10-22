"""19-EDO (19ED2) Retuner — VFX Script для FL Studio (2024 / 21.2+).

Каждая клавиша = 1 шаг 19-EDO (1200/19 ≈ 63.158 цента).
Опорная клавиша (по умолчанию 69 — в FL Studio подписана A5, в MIDI A4)
звучит на выбранной частоте A (440 / 437 Гц или своя).

Использование: Patcher -> VFX Script (этот код) -> инструмент.
Подробно — docs/INSTRUCTION_RU.md.
"""

import math

import flvfx as vfx

EDO = 19
A4_CHOICES = [440.0, 437.0, 432.0, 442.0, 415.0]
A4_LABELS = ["440 Hz", "437 Hz", "432 Hz", "442 Hz", "415 Hz", "Custom (knob)"]


class EdoVoice(vfx.Voice):
    parentVoice = None


def read_settings():
    form = vfx.context.form
    choice = int(form.getInputValue("A4 reference"))
    if 0 <= choice < len(A4_CHOICES):
        a4 = A4_CHOICES[choice]
    else:
        a4 = float(form.getInputValue("Custom A4 (Hz)"))
    ref_key = int(form.getInputValue("Reference key (A)"))
    bypass = bool(form.getInputValue("Bypass"))
    return a4, ref_key, bypass


def edo_to_note(note, a4, ref_key):
    """Номер клавиши 19-EDO -> дробный MIDI-номер 12-TET (60.0 = C)."""
    return 69.0 + (note - ref_key) * 12.0 / EDO + 12.0 * math.log2(a4 / 440.0)


def apply_tuning(v, source_note):
    a4, ref_key, bypass = read_settings()
    v.note = source_note if bypass else edo_to_note(source_note, a4, ref_key)


def onTriggerVoice(incomingVoice):
    v = EdoVoice(incomingVoice)
    v.parentVoice = incomingVoice
    apply_tuning(v, incomingVoice.note)
    v.trigger()


def onTick():
    # Повторяем свойства родительской ноты, чтобы работали слайды/портаменто
    # (слайд идёт по шагам 19-EDO) и изменения настроек «на лету».
    for v in vfx.context.voices:
        if v.parentVoice is not None:
            v.copyFrom(v.parentVoice)
            apply_tuning(v, v.parentVoice.note)


def onReleaseVoice(incomingVoice):
    for v in vfx.context.voices:
        if v.parentVoice == incomingVoice:
            v.release()


def createDialog():
    form = vfx.ScriptDialog(
        "19-EDO Retuner",
        "Every key = one step of 19-EDO (63.158 cents).\n"
        "Reference key plays the note A at the chosen frequency.\n"
        "Route: Patcher -> VFX Script -> instrument.")
    form.addInputCombo("A4 reference", A4_LABELS, 0)
    form.addInputKnob("Custom A4 (Hz)", 437.0, 400.0, 480.0)
    form.addInputKnobInt("Reference key (A)", 69, 0, 127)
    form.addInputCheckbox("Bypass", 0)
    return form
