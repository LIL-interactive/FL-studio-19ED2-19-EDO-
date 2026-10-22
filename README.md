# FL Studio 19ED2 (19-EDO) Toolkit

Набор инструментов, который перестраивает проект FL Studio в микротональный строй
**19-EDO / 19ED2** (19 равных шагов на октаву), с эталоном **A = 440 Гц** или **A = 437 Гц**
(либо любым своим) — для родных инструментов FL, Kontakt и сторонних VST/VST3/CLAP.

Все части используют одну раскладку: **каждая клавиша = 1 шаг 19-EDO, клавиша 69 (A5 в FL) = A**,
поэтому разные инструменты в одном проекте звучат согласованно.

| Путь | Для чего |
|---|---|
| `fl_studio/VFX Script/19-EDO Retuner.py` | VFX Script: перестройка «на лету» родных инструментов FL (через Patcher) |
| `fl_studio/Piano roll scripts/19-EDO Convert.pyscript` | Piano roll: конвертация нот в 12-TET + fine pitch (запасной путь) |
| `kontakt/19-EDO_Tuner.ksp.txt`, `kontakt/19-EDO_Tuner_A437.ksp.txt` | KSP-скрипт для любой библиотеки Kontakt |
| `presets/A440/`, `presets/A437/` | `.scl`, `.kbm`, `.tun`, MTS `.syx`, CSV-таблица частот — для MTS-ESP Mini и плагинов со Scala |
| `tools/edo19.py` | Генератор всех файлов для любого A и опорной клавиши |
| `docs/INSTRUCTION_RU.md` | **Пошаговая инструкция** |
| `docs/RESEARCH_RU.md` | Обзор гайдов и существующих решений |
| `TUTORIALS/` | Гайды: сведение/мастеринг и стандарты LUFS; музыка для игр (гармония, мелодия, аранжировка) |

Быстрый старт — [docs/INSTRUCTION_RU.md](docs/INSTRUCTION_RU.md).

```bash
python3 tools/edo19.py --a4 437 --out presets/A437      # пересобрать файлы строя
python3 -m unittest discover -s tests -v                # тесты
```
