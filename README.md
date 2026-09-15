# Alien 8 → Вектор-06Ц

Порт по рецепту, отработанному на Knight Lore: `~/projects/knightlore-v06c/docs/PORT_RECIPE.md`.
Обе игры — Ultimate 1984–85, движок Filmation, один автор дизассемблера (tcdev).

Материалы (образы игр, дизассемблер, стенды): `~/projects/alien8-research/`.
Темп трёх оригиналов по комнатам: ZX — `tools/zxpace_zx.lua`, MSX — `~/projects/alien8-research/msx/SPEED.md`, CPC — `~/projects/alien8-research/cpc/SPEED.md` (сводная таблица — в журнале, раздел «Темп MSX- и CPC-версий по комнатам»).
Готовый порт-образец со всеми инструментами: `~/projects/knightlore-v06c/`.

## Состояние (2026-09-15)
Этапы 1–4 закрыты, этап 5 начат. Журнал и все числа — в `docs/PORT_RECIPE.md`.

Последнее: жалоба владельца «враг забился в угол, на экране мусор» разобрана — два дефекта
рекомпиляции в поведении робомыши (таблица направлений адресовалась смещением от ДЛИНЫ ТЕЛА
процедуры на Z80; транслятор молча ронял шесть `sla`/`srl` по `(ix+d)` в комментарий
`; UNHANDLED`). Оба чинятся в `tools/a8_native_logic.py`, +55 байт, 0 тактов. Ловятся
только в комнате с робомышью — отсюда новые сценарии стенда и две новые порчи
самопроверки; подробности в журнале, раздел «Дефект владельца 2026-09-15».

| этап | состояние | гейт |
|---|---|---|
| 1. сборка дизассемблера tcdev | закрыт | `./build.sh zx` — 28515 байт $6288-$D1EA совпали с оригинальным снимком байт в байт |
| 2. журнал состояний оригинала | закрыт | `~/projects/alien8-research/zx-stand/` — три журнала по 600 итераций, каждый повторяется байт в байт в трёх прогонах |
| 3. рекомпиляция Z80 → i8080 | закрыт | `./build.sh lockstep` + `tools/lockstep_vec.js` — 600 из 600 итераций байт в байт на всех трёх сценариях |
| 4. склейка Вектора | закрыт | `./build.sh vec` + `tools/shot_vec.js` — меню и стартовая комната рисуются, снимок сходится с оригиналом ZX; `tools/render_gate.sh` — гейт картинки vs ревизия; **`tools/zxpix_vec.js` — гейт пикселей против ОРИГИНАЛА ZX: 9 прогонов по 599 итераций (4 сценария + 5 комнат), 5391 экран сошёлся побайтно** |
| 5. звук, атрибуты, стековый вывод, HUD, цвет, темп | идёт | темп: 3.6 → **16.6 итер/с** в стартовой (заходы 3–4: game_delay снят, ограничитель темпа, нативные процедуры, стековый вывод, нативный разворот, догоняющий ISR вместо ожидания бюджета; комната 104 — 26.4, 48 — 6.2); звук MSX на AY (aycheck 0 расхождений); меню и три раскладки как у Городецкого; управление и запуск с джойстика (порт 0x0E); **цвет комнаты меняется там же, где атрибуты на ZX — на чёрном экране до `update_screen` (`tools/palseq_vec.js`)**; атрибуты и HUD не начаты |
| 4. склейка Вектора | закрыт | `./build.sh vec` + `tools/shot_vec.js` — меню и стартовая комната рисуются, снимок сходится с оригиналом ZX; `tools/render_gate.sh` — гейт картинки vs ревизия; **`tools/zxpix_vec.js` — гейт пикселей против ОРИГИНАЛА ZX: 12 прогонов по 599 итераций (6 сценариев, 7 комнат — включая ГИБЕЛЬ вне стартовой комнаты и комнату 137 с робомышью), 7188 экранов сошлись побайтно** |
| 5. звук, атрибуты, стековый вывод, HUD, цвет, темп | идёт | темп: 3.6 → **16.6 итер/с** в стартовой (заходы 3–4: game_delay снят, ограничитель темпа, нативные процедуры, стековый вывод, нативный разворот, догоняющий ISR вместо ожидания бюджета; комната 104 — 26.4, 48 — 6.2); звук MSX на AY (aycheck 0 расхождений); меню и три раскладки как у Городецкого; управление и запуск с джойстика (порт 0x0E); атрибуты, HUD и цвет не начаты |

```bash
./build.sh zx          # ZX-версия из листинга tcdev + гейт «байт в байт»
./build.sh lockstep    # i8080, логика 1:1, вывод заглушен + три гейта
./build.sh vec         # Вектор-06Ц: ч/б, нативный столбцовый буфер
node tools/lockstep_vec.js build/alien8_8080.r0m build/alien8_8080.sld 600 \
  ~/projects/alien8-research/zx-stand/inputs_idle.txt \
  ~/projects/alien8-research/zx-stand/zx_idle600.bin
# сценарии стенда ZX: inputs_idle / inputs_alive / inputs_safe (стартовая комната),
# inputs_walk (четыре комнаты), inputs_death (ГИБЕЛЬ в соседней комнате),
# inputs_death137 (комната 137 + гибель, снимать с A8ROOM=137 / ZXSCR_ROOM=137)

node tools/shot_vec.js build/alien8_vec.r0m 900 spec/keys_start.txt build/shot.pgm
python3 tools/pgm2png.py build/shot.pgm /tmp/shot.png     # посмотреть картинку
tools/render_gate.sh HEAD 120 104,39,56,88,48             # гейт картинки vs ревизия (+ по комнатам)

# ГЕЙТ ПИКСЕЛЕЙ ПРОТИВ ОРИГИНАЛА ZX (единственный, чей судья — не прежняя ревизия, а сам ZX):
# плоскость 0 против дампа видеопамяти ZX на той же границе итерации; дампы снимает
# zx-stand/zx_screen.lua (LOCKSTEP.md §10), комната задаётся A8ROOM/ZXSCR_ROOM
A8_IRQDROP=1 node tools/zxpix_vec.js build/alien8_vec.r0m build/alien8_vec.sld 600 \
  ~/projects/alien8-research/zx-stand/inputs_walk.txt \
  ~/projects/alien8-research/zx-stand/zx_screen_walk.bin
A8PNG=300 node tools/zxpix_vec.js ...   # картинка «ZX | Вектор | XOR» -> build/zxpix_*.png
# ПАЛИТРА ПРОТИВ СТИРАНИЯ ЭКРАНА: цвет комнаты обязан меняться только на ЧЁРНОМ экране
# (нарушение = запись палитры в момент, когда плоскость 0 не пуста). A8PALTRACE=1 — трасса
# по кадрам вокруг каждой смены комнаты и гибели
A8_IRQDROP=1 node tools/palseq_vec.js build/alien8_vec.r0m build/alien8_vec.sld 250
A8ROOM=137 A8_IRQDROP=1 node tools/zxpix_vec.js build/alien8_vec.r0m build/alien8_vec.sld 600 \
  ~/projects/alien8-research/zx-stand/inputs_death137.txt \
  ~/projects/alien8-research/zx-stand/zx_screen_death137.bin   # комната владельца: робомышь + гибель
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
| **джойстик** (порт 0x0E, всегда) | LEFT | RIGHT | UP | FIRE1 | FIRE2 |

**Джойстик работает всегда и параллельно с клавиатурой**, сводясь к битам выбранного режима:
в режиме 3 DIRECTIONAL стик — стороны света (включая DOWN), в поворотных 1 и 2 «вниз» не
заведено (его нет и у клавиатуры). В меню **кнопка = «0 START GAME»** (она же пропускает
мелодии), а направления листают режим по кругу: LEFT/UP назад, RIGHT/DOWN вперёд. Пауза
остаётся на ВК.

## MiSTer (живое железо)
Образ 64 КБ с загрузчиком в байте 0 кладётся как `.c00` (грузится по 0x0000; `.rom` лёг бы по 0x0100),
запуск через `Alien8.mgl` по FIFO (`load_core`), скриншот с железа — `screenshot` в тот же FIFO:
```bash
sshpass -p 1 scp -o PreferredAuthentications=password -o PubkeyAuthentication=no \
  build/alien8_vec.r0m "root@192.168.1.124:/media/fat/games/VECTOR06/Alien 8.c00"
sshpass -p 1 ssh root@192.168.1.124 '(echo "load_core /media/fat/Alien8.mgl" > /dev/MiSTer_cmd) & sleep 12; \
  (echo screenshot > /dev/MiSTer_cmd) & sleep 4; ls -t /media/fat/screenshots/VECTOR06/ | head -1'
```

## Каталоги
- `tools/` — транслятор, гейты, профилировщики (берутся из knightlore-v06c и правятся под Alien 8); `gatecheck.py` вносит в них порчу и проверяет, что гейт её ловит
- `src/` — asm-исходник игры (сборка дизассемблера tcdev под sjasmplus)
- `spec/` — спецификации процедур на Python для метода «спец → дамп → asm» (пока пусто)
- `docs/` — журнал порта
- `build/` — сборки (в индекс не берутся)
