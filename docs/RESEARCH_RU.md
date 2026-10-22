# Исследование: микротональность в FL Studio и похожие решения

## Что умеет FL Studio сам по себе

| Механизм | Точность | Кого перестраивает | Вывод |
|---|---|---|---|
| Глобальный строй / Scala в FL | — | — | Нет. На форуме Image-Line до сих пор висят запросы на встроенную микротональность. |
| Piano roll → Note fine pitch (pitchofs) | шаг 10 центов (±120 = ±1 октава) | родные генераторы FL; сторонние плагины — только если поддерживают per-note pitch | Годится для черновика (ошибка до ±5 центов). Реализовано в 19-EDO Convert.pyscript. |
| VFX Script (FL Studio 2024+) | дробный номер ноты (voice.note — float, «fractional values allowed for microtuning») | всё, что подключено после него в Patcher и понимает дробную высоту ноты (родные генераторы FL) | Самый удобный «родной» способ. Реализовано в 19-EDO Retuner.py. |
| Sytrus .fnv | любая | только Sytrus | Узко, не масштабируется. |
| Pitch bend канала | любая | монофонично | Не годится для аккордов. |

## Индустриальные решения для сторонних плагинов

- Scala .scl + .kbm — стандарт де-факто. Нативно читают: Surge XT, Vital, Pianoteq,
  u-he (Diva, Zebra, Hive, Repro…), Arturia Pigments, Serum 2 и др.
- MTS-ESP (ODDSound) — протокол, где один «мастер» (бесплатный MTS-ESP Mini, либо
  MTS-ESP Suite, Entonal Studio, Infinitone DMT) перестраивает все совместимые плагины проекта
  сразу. Работает в любом хосте, включая FL Studio (это связь плагин-плагин, хосту поддержка не нужна).
  Список клиентов: https://oddsound.com/supportedplugins.php.
- AnaMark .tun и MIDI Tuning Standard (SysEx Bulk Dump) — старые, но широко
  поддерживаемые форматы (синты, железо).
- Kontakt — встроенный «Factory → Tuning → Microtuning» повторяет 12 нот в октаве,
  поэтому 19-EDO им не сделать. Рабочий путь — KSP-скрипт с change_tune()
  (точность 1 миллицент, 100000 = полутон). Похожие проекты: бесплатный скрипт
  Orange Tree Samples, «Polyphonic Microtuning in Kontakt with Max MSP» (lewiswolf).
- Pitch bend round-robin / MPE (Entonal Studio, MTS-ESP Suite в режиме MIDI) — для плагинов
  вообще без поддержки строя. В FL полноценного MPE-вывода для VST нет, поэтому это крайний вариант.

## Вывод — архитектура этого репозитория

Одного «переключателя строя на весь FL Studio» физически не существует: у FL нет глобального
строя, и каждый плагин строится по-своему. Поэтому инструмент — это набор из согласованных
частей с одной и той же математикой и раскладкой (клавиша 69 = A = 440/437 Гц, каждая клавиша
= 1 шаг 19-EDO), чтобы любой инструмент в проекте звучал одинаково:

1. tools/edo19.py — генератор всех файлов строя (.scl/.kbm/.tun/.syx/.csv) и KSP-скрипта.
2. fl_studio/VFX Script/19-EDO Retuner.py — для родных инструментов FL.
3. kontakt/19-EDO_Tuner*.ksp.txt — для любых библиотек Kontakt.
4. presets/ + MTS-ESP Mini — для всех остальных VST/VST3/CLAP.
5. fl_studio/Piano roll scripts/19-EDO Convert.pyscript — запасной путь через fine pitch.

## Источники

- FL Studio VFX Script manual — https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/VFX%20Script.htm
- FL Studio Piano roll scripting API — https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/pianoroll_scripting_api.htm
- Feature request: Built-in microtuning (Image-Line forum) — https://forum.image-line.com/viewtopic.php?p=1954540
- Wrapper «Send pitch bend range» (Image-Line KB) — https://support.image-line.com/action/knowledgebase?ans=810
- Sevish — микротональные плагины/DAW — https://sevish.com/?p=13
- VI-Control: modern approaches to microtonal tuning — https://vi-control.net/community/threads/modern-approaches-to-microtonal-tuning-and-plugin-solutions.163952/
- Kontakt 7 microtuning (NI community) — https://community.native-instruments.com/discussion/10087/kontakt-7-microtuning
- Orange Tree Samples free microtuning script — https://orangetreesamples.com/blog/free-pro-microtuning-script
- Polyphonic Microtuning in Kontakt with Max MSP — https://github.com/lewiswolf/Polyphonic-Microtuning-in-Kontakt-with-Max-MSP
- Scala .scl / .kbm формат — https://www.huygens-fokker.org/scala/scl_format.html, https://www.huygens-fokker.org/scala/help.htm#mappings
- AnaMark .tun спецификация — http://www.mark-henning.de/eternity/tuningspecs.html
