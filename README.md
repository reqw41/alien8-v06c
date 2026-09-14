# Alien 8 → Вектор-06Ц

Порт по рецепту, отработанному на Knight Lore: `~/projects/knightlore-v06c/docs/PORT_RECIPE.md`.
Обе игры — Ultimate 1984–85, движок Filmation, один автор дизассемблера (tcdev).

Материалы (образы игр, дизассемблер, стенды): `~/projects/alien8-research/`.
Темп трёх оригиналов по комнатам: ZX — `tools/zxpace_zx.lua`, MSX — `~/projects/alien8-research/msx/SPEED.md`, CPC — `~/projects/alien8-research/cpc/SPEED.md` (сводная таблица — в журнале, раздел «Темп MSX- и CPC-версий по комнатам»).
Готовый порт-образец со всеми инструментами: `~/projects/knightlore-v06c/`.

## Состояние (2026-09-14)
Этапы 1–4 закрыты, этап 5 начат. Журнал и все числа — в `docs/PORT_RECIPE.md`.

| этап | состояние | гейт |
|---|---|---|
| 1. сборка дизассемблера tcdev | закрыт | `./build.sh zx` — 28515 байт $6288-$D1EA совпали с оригинальным снимком байт в байт |
| 2. журнал состояний оригинала | закрыт | `~/projects/alien8-research/zx-stand/` — три журнала по 600 итераций, каждый повторяется байт в байт в трёх прогонах |
| 3. рекомпиляция Z80 → i8080 | закрыт | `./build.sh lockstep` + `tools/lockstep_vec.js` — 600 из 600 итераций байт в байт на всех трёх сценариях |
| 4. склейка Вектора | закрыт | `./build.sh vec` + `tools/shot_vec.js` — меню и стартовая комната рисуются, снимок сходится с оригиналом ZX; `tools/render_gate.sh` — гейт картинки |
| 5. звук, атрибуты, стековый вывод, HUD, цвет, темп | идёт | темп: 3.6 → **16.6 итер/с** в стартовой (заходы 3–4: game_delay снят, ограничитель темпа, нативные процедуры, стековый вывод, нативный разворот, догоняющий ISR вместо ожидания бюджета; комната 104 — 26.4, 48 — 6.2); звук MSX на AY (aycheck 0 расхождений); меню и три раскладки как у Городецкого; атрибуты, HUD и цвет не начаты |

```bash
./build.sh zx          # ZX-версия из листинга tcdev + гейт «байт в байт»
./build.sh lockstep    # i8080, логика 1:1, вывод заглушен + три гейта
./build.sh vec         # Вектор-06Ц: ч/б, нативный столбцовый буфер
node tools/lockstep_vec.js build/alien8_8080.r0m build/alien8_8080.sld 600 \
  ~/projects/alien8-research/zx-stand/inputs_idle.txt \
  ~/projects/alien8-research/zx-stand/zx_idle600.bin

node tools/shot_vec.js build/alien8_vec.r0m 900 spec/keys_start.txt build/shot.pgm
python3 tools/pgm2png.py build/shot.pgm /tmp/shot.png     # посмотреть картинку
tools/render_gate.sh HEAD 120 104,39,56,88,48             # гейт картинки vs ревизия (+ по комнатам)
python3 tools/gatecheck.py                                # САМОПРОВЕРКА: каждый гейт обязан
                                                          # поймать свою порчу (по коду возврата)
node tools/profile_vec.js build/alien8_vec.r0m build/alien8_vec.sld 150
node tools/inputcheck_vec.js build/alien8_vec.r0m build/alien8_vec.sld   # раскладки, меню, пауза
node tools/kbcheck_vec.js build/alien8_vec.r0m build/alien8_vec.sld      # матрица Вектора -> ряды ZX

# ЗВУК (драйвер MSX-версии на AY): журнал записей AY и поканальная сверка с моделью MSX
node tools/tunecheck_vec.js build/alien8_vec.r0m build/alien8_vec.sld    # темп всех шести мелодий
A8TUNETRACE=build/ay.txt node tools/tunecheck_vec.js build/alien8_vec.r0m build/alien8_vec.sld
python3 tools/aycheck.py build/ay.txt                                    # мелодии поканально
node tools/aytrace_vec.js build/alien8_vec.r0m build/alien8_vec.sld 300 \
  ~/projects/alien8-research/zx-stand/inputs_alive.txt > build/ay_game.txt
python3 tools/aycheck.py build/ay_game.txt                               # эффекты в игре
A8SFX=1:0:31:0:0 node tools/aytrace_vec.js ... > build/ay_e1.txt         # эффект, которого нет в сценарии
```

## Управление

В меню строка выбранного режима подсвечена полосой; режим запоминается между
играми. `1`, `2`, `3` — выбрать режим, `0` — начать игру, **ВК — пауза**
(в любом режиме; повторное нажатие снимает).

| режим | влево | вправо | вперёд | прыжок | взять/бросить |
|---|---|---|---|---|---|
| **1 KEYBOARD** (клавиши оригинала) | `Z` `C` `M` `B` | `X` `V` `N` | `A` `D` `F` `G` `S` `H` `J` `K` `L` | `Q` `W` `E` `R` `T` `P` `O` `I` `U` `Y` | `0`..`9` |
| **2 CURSOR** | ← | → | ↑ | пробел | ↓ |
| **3 DIRECTIONAL CONTROL** | стрелки = стороны света | | | пробел | `0`..`7` |

## Каталоги
- `tools/` — транслятор, гейты, профилировщики (берутся из knightlore-v06c и правятся под Alien 8); `gatecheck.py` вносит в них порчу и проверяет, что гейт её ловит
- `src/` — asm-исходник игры (сборка дизассемблера tcdev под sjasmplus)
- `spec/` — спецификации процедур на Python для метода «спец → дамп → asm» (пока пусто)
- `docs/` — журнал порта
- `build/` — сборки (в индекс не берутся)
