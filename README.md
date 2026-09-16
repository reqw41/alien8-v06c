# Alien 8 → Вектор-06Ц

Порт по рецепту, отработанному на Knight Lore: `~/projects/knightlore-v06c/docs/PORT_RECIPE.md`.
Обе игры — Ultimate 1984–85, движок Filmation, один автор дизассемблера (tcdev).

Материалы (образы игр, дизассемблер, стенды): `~/projects/alien8-research/`.
Темп трёх оригиналов по комнатам: ZX — `tools/zxpace_zx.lua`, MSX — `~/projects/alien8-research/msx/SPEED.md`, CPC — `~/projects/alien8-research/cpc/SPEED.md` (сводная таблица — в журнале, раздел «Темп MSX- и CPC-версий по комнатам»).
Готовый порт-образец со всеми инструментами: `~/projects/knightlore-v06c/`.

## Состояние (2026-09-16)
Этапы 1–4 закрыты, этап 5 начат. Журнал и все числа — в `docs/PORT_RECIPE.md`.

Последнее: **верхний регион кода ушёл с полосы HUD** (ветка `p2reflow`). Панель Alien 8
(ZX-строки 160..191) в столбцовой раскладке Вектора лежит в смещениях 0x20..0x3F **каждой**
из 32 страниц плоскости 2, поэтому верхний регион 0xD000–0xDFFF — не сплошные 4 КБ, а 17 окон
(32 Б, 15 по 224 Б и 192 Б). Новый раскладчик `a8_layout_upper` режет регион на 61 блок и
раскладывает их по окнам: **2545 Б в 13 окнах, свободно 1039, в полосе HUD ноль байт**.
Неподвижен один блок — цепочки `print_sprite` (156 Б, вход патчится младшим байтом `jp`,
значит одна страница); таблица `vec_rptab` (целая страница) выселена в хвост нижнего региона.
Темп — такт в такт с прежним. Гейт `tools/check_plane2.py` в `./build.sh vec`.
Подробности в журнале, раздел «Верхний регион с обходом HUD-полосы».

До того: **дыры вне картинки** (ветка `holes`) — 2043 Б мелких процедур уехали в строки
224..255/0..31 столбцов плоскости 1, куда не пишет ни рендер, ни очистка буфера (замер
`tools/holescan_vec.js`: шесть сценариев и все 128 комнат, ноль записей). Нижний регион:
свободно было 1608 Б, стало **3557** (+1949), темп не изменился (±0.3 % — разброс от
`seed_3`). Это закрывает дефицит под переезд переменных игры (1928 Б) из плоскости 2,
которая нужна под селектор белого HUD. Гейт — `tools/check_plane1.py` в `./build.sh vec`.
Подробности в журнале, раздел «Дыры вне картинки (Alien 8)».

До того: обе починки робомыши перенесены ПО МЕСТУ (сдвиги по `(ix+d)` — в транслятор,
Последнее: **вырезана атрибутная память ZX и обрезана печать по столбцу 31** — страницы
0xC0..0xC7 плоскости 2 (мусорное ОЗУ атрибутов + защитная зона спиллов) освобождены под
будущий цветной HUD. Код похудел на 650 байт, картинка байт в байт, гейт `spillcheck_vec.js`
держит зону мёртвой: 128 комнат × 300 итераций — ноль записей. Замер заодно показал, что
запаса до края нет ни одного столбца: 20 338 печатей из 377 740 дотягиваются до столбца 31
вплотную. Подробности — в журнале, раздел «Атрибуты ZX вырезаны, спиллы обрезаны».

Перед этим: обе починки робомыши перенесены ПО МЕСТУ (сдвиги по `(ix+d)` — в транслятор,
адрес таблицы направлений — в склейку, +24 байта против прежней пост-правки: теперь
сохраняется ещё и A, как у Z80), и сделан **обход ВСЕХ 128 комнат против оригинала ZX**:
три сценария × 128 комнат = 384 прогона, 383 зелёных по состоянию И по пикселям
(114 559 экранов побайтно). Единственная красная — комната 186 на прогулке, и там
виноват не порт, а кадровый латч ввода MAME (ЗАМЕР, LOCKSTEP.md §11 стенда).
Подробности в журнале, раздел «Обход всех 128 комнат против ZX».

| этап | состояние | гейт |
|---|---|---|
| 1. сборка дизассемблера tcdev | закрыт | `./build.sh zx` — 28515 байт $6288-$D1EA совпали с оригинальным снимком байт в байт |
| 2. журнал состояний оригинала | закрыт | `~/projects/alien8-research/zx-stand/` — три журнала по 600 итераций, каждый повторяется байт в байт в трёх прогонах |
| 3. рекомпиляция Z80 → i8080 | закрыт | `./build.sh lockstep` + `tools/lockstep_vec.js` — 600 из 600 итераций байт в байт на всех трёх сценариях |
| 4. склейка Вектора | закрыт | `./build.sh vec` + `tools/shot_vec.js` — меню и стартовая комната рисуются, снимок сходится с оригиналом ZX; `tools/render_gate.sh` — гейт картинки vs ревизия; **`tools/zxpix_vec.js` — гейт пикселей против ОРИГИНАЛА ZX: 12 прогонов по 599 итераций (6 сценариев, 7 комнат — включая ГИБЕЛЬ вне стартовой комнаты и комнату 137 с робомышью), 7188 экранов сошлись побайтно** |
| 5. звук, атрибуты, стековый вывод, HUD, цвет, темп | идёт | темп: 3.6 → **16.6 итер/с** в стартовой (заходы 3–4: game_delay снят, ограничитель темпа, нативные процедуры, стековый вывод, нативный разворот, догоняющий ISR вместо ожидания бюджета; комната 104 — 26.4, 48 — 6.2); звук MSX на AY (aycheck 0 расхождений); меню и три раскладки как у Городецкого; управление и запуск с джойстика (порт 0x0E); **атрибуты ZX вырезаны, спиллы печати обрезаны (страницы 0xC0..0xC7 плоскости 2 свободны)**; **верхний регион кода разложен мимо будущей полосы HUD** (0 байт в полосе, гейт `check_plane2`); HUD и цвет не начаты |

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

# ДЫРЫ ВНЕ КАРТИНКИ (журнал, раздел «Дыры вне картинки»). Строки 224..255 столбца c и 0..31
# столбца c+1 плоскости 1 лежат подряд (64 Б) и не пишутся никем — туда a8_pack_holes увозит
# мелкие процедуры нижнего региона (2043 Б в 82 процедуры, нижний регион +1949 Б).
node tools/holescan_vec.js build/alien8_vec.r0m build/alien8_vec.sld 200 \
  ~/projects/alien8-research/zx-stand/inputs_walk.txt      # ЗАМЕР/СТОРОЖ: какие строки пишутся;
                                                          # код 1 при записи в дыры (адрес + PC)
A8ROOM=137 node tools/holescan_vec.js ...                  # по комнате
A8HOLE_PLANE=8000 A8HOLE_GAME=1 node tools/holescan_vec.js ...   # судить плоскость 0, фаза игры
python3 tools/check_plane1.py build/alien8_vec.lst \
  --walk build/alien8_vec.asm                              # ГЕЙТ (в ./build.sh vec): в строках
                                                          # 32..223 буфера ноль байт кода;
                                                          # --walk: счёт длин против листинга
python3 tools/a8_regions.py build/alien8_vec.lst           # свободное место по регионам
# ВЕРХНИЙ РЕГИОН МИМО ПОЛОСЫ HUD (журнал, «Верхний регион с обходом HUD-полосы»). Панель
# займёт смещения 0x20..0x3F каждой страницы плоскости 2 — регион разложен по 17 окнам.
python3 tools/check_plane2.py build/alien8_vec.lst \
  --walk build/alien8_vec.asm                              # ГЕЙТ (в ./build.sh vec): в полосе
                                                          # HUD ноль байт кода и данных;
                                                          # --walk судит ЗАНЯТЫЕ адреса (DS!)
A8_HUD_DEBUG=1 ./build.sh vec                             # карта размещения: окна и блоки
A8_HUD_LAYOUT=off ./build.sh vec                          # без раскладчика (негативный контроль)
A8_HUD_LOW=1 ./build.sh vec                               # + окна страниц 0xC0..0xCF (после varmove;
                                                          # сейчас краснеет — там переменные)
python3 tools/a8_regions.py build/alien8_vec.lst --holes   # ... с разбивкой по 33 дырам
A8_HOLE_DEBUG=1 ./build.sh vec                            # что и куда уехало
A8_HOLE_BYTES=0 ./build.sh vec                            # упаковку выключить (разведение причин)
# ПЛОСКОСТЬ 2 ОБЯЗАНА БЫТЬ МЁРТВОЙ: в 0xC000-0xC7FF не должно попасть ни одной записи
# (атрибуты ZX вырезаны, вылет печати за столбец 31 обрезает ps_cw). «all» — все 128 комнат.
A8_IRQDROP=1 node tools/spillcheck_vec.js build/alien8_vec.r0m build/alien8_vec.sld 300 \
  ~/projects/alien8-research/zx-stand/inputs_alive.txt all
A8PSMAX=1 ... # запас до края: самый правый столбец, который печать заняла бы без клипа
A8PSSP=1  ... # инвариант чтения спрайта через SP; смотреть на сборке A8_PSCW=test
A8_PSCW=test ./build.sh vec   # край объявлен столбцом 30: клип срабатывает, ветка ps_fix живая
A8_PSCW=off  ./build.sh vec   # сборка без клипа (негативный контроль)

# ОБХОД ВСЕХ 128 КОМНАТ ПРОТИВ ZX (~85 с на 8 потоках). Для каждой комнаты из location_tbl
# снимается журнал ZX (zx_screen.lua, ZXSCR_ROOM) и прогоняется гейт пикселей (A8ROOM):
# сверяются И 1928 байт состояния, И пиксели. Итог — таблица «комната | грузится |
# состояние | пиксели | первое расхождение», код возврата 1 при любой красной комнате.
python3 tools/a8_rooms.py            # номера комнат: их 128, но НЕ 0..127, а 2..248 вразбивку
tools/roomsweep.sh                   # покой, 300 итераций, 4 потока
tools/roomsweep.sh inputs_alive.txt 300 8            # свой сценарий / итерации / потоки
tools/roomsweep.sh inputs_idle.txt 300 4 "39 48 137" # только эти комнаты
# ПЕРЕПИСЬ КЛАССОВ ОБЪЕКТОВ: какой обработчик upd_NN работает в какой комнате
tools/roomobjs.sh                    # -> build/roomobjs/CENSUS.txt
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
- `tools/` — транслятор, гейты, профилировщики (берутся из knightlore-v06c и правятся под Alien 8); `gatecheck.py` вносит в них порчу и проверяет, что гейт её ловит; `spillcheck_vec.js` сторожит плоскость 2; `roomsweep.sh` гоняет ВСЕ 128 комнат против ZX, `roomobjs.sh` переписывает классы объектов по комнатам
- `src/` — asm-исходник игры (сборка дизассемблера tcdev под sjasmplus)
- `spec/` — спецификации процедур на Python для метода «спец → дамп → asm» (пока пусто)
- `docs/` — журнал порта
- `build/` — сборки (в индекс не берутся)
