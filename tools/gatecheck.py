#!/usr/bin/env python3
"""САМОПРОВЕРКА ГЕЙТОВ Alien 8: в каждый гейт вносится порча, которую он ОБЯЗАН поймать.

Гейт, который никогда не краснел, ничего не доказывает: он может сравнивать сборку саму с
собой (так уже было с `render_gate.sh`), проверять не тот код, что идёт в игру (так уже было
с локстепом до `A8_IX_HOT`), или краснеть только ТЕКСТОМ, выходя с нулём (так было с
`lockstep_vec.js`). Здесь по одной порче на гейт — в `tools/` (а не в `src/`), потому что
именно там живёт вся склейка и весь нативный код.

  python3 tools/gatecheck.py [имя_порчи ...]      (без аргументов — все)

Вердикт выносится по КОДУ ВОЗВРАТА гейта, а не по его тексту. Порча вносится в рабочее дерево
и ОТКАТЫВАЕТСЯ `git checkout --` в любом случае (в том числе по Ctrl+C); после отката обе цели
пересобираются, иначе в `build/` остаётся испорченный образ и следующий ручной прогон краснеет
на ровном месте. Перед запуском рабочее дерево должно быть чистым.

Две ловушки самой мутационной проверки (обе давали ложное «гейт слеп», §22 рецепта KL):
* порча обязана ДОХОДИТЬ ДО ПРОВЕРЯЕМОГО СВОЙСТВА. У Alien 8 на этом обожглись: флаг DRAW
  (`or 0x10` в нативном `set_draw_objs_overlapped`) до журнала не доходит — на цели lockstep
  вывод заглушен, а сам флаг к моменту снятия состояния уже не отличается. Порча логики взята
  в копии полей +24..+27 -> +28..+31 (`update_sprite_loop`): эти байты лежат в таблице объектов,
  то есть прямо в записи журнала;
* порча обязана ПОПАДАТЬ В СОБИРАЕМЫЙ КОД. Порча вывода живёт в `tools/a8_vec.py`, который
  собирает только цель `vec`: образ `alien8_8080.r0m` с ней совпадает байт в байт с чистым
  (проверено md5), поэтому спрашивать с локстепа тут нечего — он её физически не видит;
* и третья, найденная на порче звука: **кэш `tools/__pycache__`**. У mtime в `.pyc`
  разрешение в секунду, и если откат предыдущей порчи и запись следующей попали в одну
  секунду, Python брал старый `.pyc` и собирал ЧИСТЫЙ код — гейт «пропускал» порчу,
  которой в образе не было. Кэш теперь сносится и перед прогоном, и после отката.
"""
import os
import re
import shutil
import signal
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAND = os.path.join(os.environ.get('A8_RESEARCH', os.path.expanduser('~/projects/alien8-research')),
                     'zx-stand')
# сценарий локстепа -> (файл ввода, журнал ZX). Соответствие — по LOCKSTEP.md стенда.
SCEN = [('покой', 'inputs_idle.txt', 'zx_idle600.bin'),
        ('ходьба', 'inputs_alive.txt', 'zx_states600.bin'),
        ('осторожный', 'inputs_safe.txt', 'zx_safe600.bin')]
# гейт пикселей против ZX: тот же сценарий, но журнал — дамп ЭКРАНА (zx_screen.lua стенда).
# Четвёртое поле — номер комнаты (A8ROOM на стенде Вектора = ZXSCR_ROOM у lua), None = стартовая.
PIXSCEN = [('покой', 'inputs_idle.txt', 'zx_screen_idle.bin', None),
           ('ходьба', 'inputs_alive.txt', 'zx_screen_alive.bin', None),
           ('осторожный', 'inputs_safe.txt', 'zx_screen_safe.bin', None),
           ('прогулка', 'inputs_walk.txt', 'zx_screen_walk.bin', None),   # четыре комнаты
           ('комната 48', 'inputs_idle.txt', 'zx_screen_r48.bin', '48'),  # тяжёлая комната
           # 2026-09-15: гибель ВНЕ стартовой комнаты (прежние сценарии гибли только в ней)
           # и комната 137 — первая в гейтах с РОБОМЫШЬЮ (upd_5E_5F). Именно на ней нашлись
           # два дефекта рекомпиляции (журнал, «Робомышь стояла на месте»): гейт сверяет не
           # только пиксели, но и 1928 байт состояния, и красным стало именно состояние.
           ('гибель в соседней', 'inputs_death.txt', 'zx_screen_death.bin', None),
           ('комната 137', 'inputs_idle.txt', 'zx_screen_r137.bin', '137'),
           ('137 + гибель', 'inputs_death137.txt', 'zx_screen_death137.bin', '137')]

# гейт границы занятых записей: сценарий -> (ввод, комната, итераций)
# гейт белого HUD: экран -> (окружение hudshot_vec.js, ключи hudcolor.py).
# _iters — сколько ИТЕРАЦИЙ крутить после входа в комнату (для экранов по кадрам не нужно).
HUDSCEN = [('комната 19 (старт)', {'_iters': '40'}, []),
           ('комната 137', {'_iters': '40', 'A8ROOM': '137'}, []),
           ('меню', {'_iters': '0', 'A8HS_FRAMES': '260'}, ['--nomask']),
           ('GAME OVER', {'_iters': '40', 'A8HS_JP': 'game_over@400'}, ['--nomask'])]

# ГЕЙТ ПЕРЕХОДОВ (плёнка): НАСТОЯЩАЯ дорога гибели в комнате 137 — сценарий стенда ZX плюс
# A8HS_DIE (положить последнюю жизнь на 20-й итерации), дальше своим ходом: GAME OVER ->
# рейтинг -> клавиша -> RE-PROGRAMMING (сборка робота) -> меню -> новая игра. Прыжков на метки
# нет. build/keys_go.txt пишется гейтом: отпустить всё на 700-м кадре (сценарий оставляет
# клавишу нажатой, и loc_B7AE ждал бы отпускания вечно) и дальше жать «0».
HUDFILM = dict(dirn='build/gate_film', keys='build/keys_go.txt',
               env={'A8ROOM': '137', 'A8HS_DIE': '20', 'A8HS_MAXF': '2600',
                    'A8HS_FILMFR': '300,2600,20'}, inputs='inputs_death137.txt', iters='400')

NOBJSCEN = [('покой', 'inputs_idle.txt', None, '60'),
            ('прогулка', 'inputs_walk.txt', None, '600'),
            ('гибель в соседней', 'inputs_death.txt', None, '600'),
            ('137 + гибель', 'inputs_death137.txt', '137', '600')]

# сценарии гейта aycheck: (метка, итераций, файл ввода стенда или None, окружение[, --need])
# --need=GL/GO/PZ: долгий путь без слива (смена комнаты / GAME OVER / пауза) обязан встретиться
# со звучащим на входе счётчиком — и счётчики обязаны замолчать (aycheck.py, «долгие пути»)
AYSCEN = [('ходьба', '600', 'inputs_alive.txt', {}, 'GL'),                 # эффекты 3,4,5,7; 2 смены комнаты
          ('пауза', '40', 'inputs_alive.txt', {"A8PAUSE": "1"}, 'PZ'),      # ВК сразу за звучащим сливом
          ('GAME OVER', '600', 'inputs_death.txt', {"A8LIVES": "0", "A8STOPTUNE": "1"}, 'GO'),
          ('шум', '60', None, {"A8SFX": "1:0:31:0:0"}),                    # эффект 1, отложенная нота
          ('шум 180 тиков', '40', None, {"A8SFX": "1:0:180:0:0"}),         # 56 тиков на итерацию; на
                                                                           #  3-м сливе c = 12: громкость 6 = порог
          ('чирп', '40', None, {"A8SFX": "2:0:15:0:0"}),
          ('эффект 8', '40', None, {"A8SFX": "8:0:7:0:0"}),
          ('список 9', '40', None, {"A8SFX": "9:1:40:e9b"}),
          ('лесенка', '40', None, {"A8LADDER": "15"})]

MUTS = [
    dict(name="render", gate="render_gate",
         why="окно update_screen на строку ниже (приёмник ld l,32 -> 33): чистый ВЫВОД, логика не меняется",
         file="tools/a8_vec.py",
         old="us_dst:\t\t\tld\t\th, 0\t\t\t\t; патч: страница экрана\n"
             "\t\t\t\tld\t\tl, 32\t\t\t\t; HL = приёмник\n",
         new="us_dst:\t\t\tld\t\th, 0\t\t\t\t; патч: страница экрана\n"
             "\t\t\t\tld\t\tl, 33\t\t\t\t; HL = приёмник\n"),
    dict(name="zxwipe", gate="zxpix",
         why="окно стирания старого положения объекта (wipe_next_object) на строку короче — "
             "ровно тот класс дефекта, на который жалуется владелец («спрайты не стираются»). "
             "ЧИСТЫЙ ВЫВОД: 1928 байт состояния при этом совпадают с ZX байт в байт, и красным "
             "гейт делает именно пиксельная сверка (render_gate эту порчу тоже ловит — она "
             "видна с третьей итерации; здесь она доказывает, что пиксельный путь НЕ вакуумный)",
         file="tools/a8_native_logic.py",
         old="\t\tsub c\n\t\tld l, a\t\t\t\t; высота окна\n",
         new="\t\tsub c\n\t\tdec a\n\t\tld l, a\t\t\t\t; высота окна\n"),
    dict(name="zxkey", gate="zxpix",
         why="раскладка 1: клавиша Z («поворот влево») уехала на соседний бит матрицы. "
             "RENDER_GATE ЭТУ ПОРЧУ НЕ ЛОВИТ (проверено руками: три сценария «СОВПАДЕНИЕ», код 0) — "
             "его окно 40 итераций, а Z в сценариях нажимается на 60-й; ЛОКСТЕП тоже слеп — путь "
             "a8_vec_input есть только у цели vec, у цели lockstep стоит оригинальный keyboard: "
             "по рядам ZX. Гейт против ZX краснеет на итерации 62",
         file="tools/a8_z80_to_8080.py",
         old="        DB low (vec_kbmat+7), 0x04, 0x01   ; Z             -> влево\n",
         new="        DB low (vec_kbmat+7), 0x08, 0x01   ; ПОРЧА: Z уехала на соседний бит\n"),
    dict(name="logic", gate="lockstep",
         why="update_sprite_loop кладёт в «старую» копию +31 (pixel Y) значение поля +26 (pixel X)",
         file="tools/a8_native_logic.py",
         old="\t\tld a, (hl)\n\t\tld (de), a\n\t\tld l, c\t\t\t\t; graphic_no",
         new="\t\tdec hl\n\t\tld a, (hl)\n\t\tld (de), a\n\t\tld l, c\t\t\t\t; graphic_no"),
    dict(name="nobj", gate="nobjcheck",
         why="граница занятости таблицы объектов (a8_nobj) на единицу НИЖЕ последнего живого",
         file="tools/a8_native_logic.py",
         old="        ld (a8_nobj), a\n",
         new="        dec a\n        ld (a8_nobj), a\n"),
    dict(name="i8080", gate="check_i8080",
         why="`bit n,r` остаётся Z80-only (CB-префикс на i8080 — чужая инструкция)",
         file="tools/a8_z80_to_8080.py",
         old="def _bit(n, reg):\n",
         new="def _bit(n, reg):\n"
             "    if os.environ.get('A8_GATECHECK_I8080'):\n"
             "        return ['bit %s, %s' % (n, reg)]\n"),
    dict(name="ixflags", gate="check_ixflags",
         why="в upd_103 снято сохранение переноса вокруг хелперов (ix+d) — «лишняя жизнь» не выдаётся",
         file="tools/a8_z80_to_8080.py",
         old="    assert n == 1, 'print_sprite: порядок ld sp / (ix+25)'\n    return src\n",
         new="    assert n == 1, 'print_sprite: порядок ld sp / (ix+25)'\n"
             "    if os.environ.get('A8_GATECHECK_IXFLAGS'):\n"
             "        src = src.replace('        push af   ; A8: хелпер (ix+d) портит перенос,"
             " а ответ процедуры — в нём\\n', '', 1)\n"
             "        src = src.replace('        dec (ix+5)   ; plyr bottom depth\\n        pop af\\n',"
             " '        dec (ix+5)   ; plyr bottom depth\\n', 1)\n"
             "    return src\n"),
    dict(name="djnz", gate="check_djnz",
         why="в sub_AD66 снят пересчёт Z после djnz — GAME OVER на первой итерации главного цикла",
         file="tools/a8_z80_to_8080.py",
         old="    assert n == 1, 'print_sprite: порядок ld sp / (ix+25)'\n    return src\n",
         new="    assert n == 1, 'print_sprite: порядок ld sp / (ix+25)'\n"
             "    if os.environ.get('A8_GATECHECK_DJNZ'):\n"
             "        src = src.replace('        and a   ; A8: djnz на i8080 портит Z —"
             " пересчитать по накопленному OR\\n', '', 1)\n"
             "    return src\n"),
    dict(name="input", gate="inputcheck",
         why="в раскладках 2 и 3 «стрелка вверх» переехала с бита 0x20 ряда 0 на мёртвый 0x02: "
             "ни локстеп, ни гейт картинки этих раскладок не касаются",
         file="tools/a8_z80_to_8080.py",
         old="        DB low (vec_kbmat+0), 0x20, 0x04   ; стрелка вверх\n",
         new="        DB low (vec_kbmat+0), 0x02, 0x04   ; стрелка вверх\n"),
    dict(name="pause", gate="inputcheck",
         why="пауза потеряла защиту оригинала «и ни одной другой клавиши того же ряда»: "
             "ВК лежит в ряду 0 ВМЕСТЕ СО СТРЕЛКАМИ, и ходьба ставила бы ложную паузу",
         file="tools/a8_z80_to_8080.py",
         old="        and 0xF4        ; ВК (0x04) + стрелки (0x10 0x20 0x40 0x80)\n        cp 4\n",
         new="        and 0x04        ; ПОРЧА: только ВК, стрелки не мешают\n        cp 4\n"),
    dict(name="joyfire", gate="inputcheck",
         why="FIRE2 в раскладке 3 сведена на бит 4 вместо 5: «взять» стало «вниз». Разница видна "
             "ТОЛЬКО в directional (в поворотных этот бит и есть «взять»), и ни локстеп, ни гейт "
             "картинки джойстика не касаются вовсе",
         file="tools/a8_z80_to_8080.py",
         old="        DB 0x80, 0x20   ; FIRE2 -> взять/бросить  (как цифры 0..7)\n",
         new="        DB 0x80, 0x10   ; ПОРЧА: FIRE2 на бит 4\n"),
    dict(name="joyzx", gate="inputcheck",
         why="кнопка джойстика больше не прижимает клавишу '0' в рядах ZX (`and 0xFE` -> `and 0xFF`): "
             "игра с джойстика не запускается и мелодии кнопкой не пропускаются, а раскладки, "
             "ввод в игре и ряды покоя при этом целы",
         file="tools/a8_vec.py",
         old="vj_fire:\t\tld\t\thl, vec_zxrows+4\t; FIRE -> клавиша '0' (ряд ZX 4, бит 0)\n"
             "\t\t\t\tld\t\ta, (hl)\n\t\t\t\tand\t\t0xFE\n",
         new="vj_fire:\t\tld\t\thl, vec_zxrows+4\t; FIRE -> клавиша '0' (ряд ZX 4, бит 0)\n"
             "\t\t\t\tld\t\ta, (hl)\n\t\t\t\tand\t\t0xFF\t\t\t\t; ПОРЧА: кнопка в ряды ZX не попадает\n"),
    dict(name="kbmap", gate="kbcheck",
         why="отображение «клавиша Вектора -> ряд ZX»: Z уехала с 0x04 на 0x08 ряда 7. Гейт "
             "картинки и локстеп кладут ряды ZX в память сами и этот путь не видят",
         file="tools/a8_vec.py",
         old="vec_kbmat+7,0x04,", new="vec_kbmat+7,0x08,"),
    dict(name="flip", gate="flipcheck",
         why="быстрый путь разворота смотрит только на бит V (`and 0xC0` -> `and 0x80`): "
             "запрос одного лишь H-разворота проходит мимо",
         file="tools/a8_native_flip.py",
         old="        and 0xC0\n        ret z   ; быстрый путь: ориентация уже нужная\n",
         new="        and 0x80\n        ret z   ; быстрый путь: ориентация уже нужная\n"),
    dict(name="palseq", gate="palseq",
         why="палитра комнаты встаёт ДО стирания экрана (colour_something + vec_palwait перенесены "
             "перед vec_wipe0): старая комната успевает вспыхнуть цветом новой — ровно то, на что "
             "жалуется владелец. ПРОВЕРЕНО РУКАМИ: ни гейт пикселей против ZX (599 итераций "
             "прогулки «пиксель в пиксель»), ни render_gate (семь сценариев «СОВПАДЕНИЕ»), ни "
             "локстеп (крючков Вектора у цели lockstep нет вовсе) этой порчи не видят — палитра "
             "не пиксель, а на границе итерации и картинка, и цвет одни и те же",
         file="tools/a8_vec.py",
         old='               "        call vec_wipe0   ; Вектор: экран в ноль ДО смены палитры\\n"\n'
             '               "        call colour_something   ; fill_attr -> палитра новой комнаты\\n"\n'
             '               "        call vec_palwait   ; палитра встаёт на ЧЁРНОМ экране, до update_screen\\n"\n',
         new='               "        call colour_something   ; ПОРЧА: палитра до стирания\\n"\n'
             '               "        call vec_palwait\\n"\n'
             '               "        call vec_wipe0\\n"\n'),
    dict(name="tune", gate="tunecheck",
         why="плеер мелодий msx_tv_note считает длину ноты на кадр меньше (`sub 1` -> `sub 2`: "
             "res = длина-2): каждая нота короче, делители по кадрам расходятся с блобом "
             "(старая порча cp 7 -> cp 8 в msx_fetch ушла вместе с real-time плеером MSX)",
         file="tools/a8_sound_ay.py",
         old="\t\t\t\tsub\t\t1\t\t\t\t\t\t; кадр взятия ноты уже потрачен",
         new="\t\t\t\tsub\t\t2\t\t\t\t\t\t; ПОРЧА: кадр взятия ноты уже потрачен"),
    dict(name="mousetbl", gate="zxpix",
         why="снята починка адреса таблицы направлений робомыши: обратно `sub_B0E7+0x21` — "
             "смещение, верное только для длины тела НА Z80. Это и был дефект владельца "
             "(«враг забился в угол»): мышь читала три байта из хвоста собственного кода и "
             "получала нулевое направление. КРАСНЕЕТ ТОЛЬКО НА КОМНАТЕ 137 — в стартовой "
             "комнате и в комнатах 39/48/56/88/104 робомыши нет вовсе, и все прежние "
             "сценарии гейта эту порчу пропускают",
         file="tools/a8_vec.py",
         old="                          ('0xB108', 'a8_mouse_dirs', 1)):   # направления робомыши, см. выше\n",
         new="                          ('0xB108', 'sub_B0E7+0x21', 1)):   # ПОРЧА: снова смещение длины тела Z80\n"),
    dict(name="ixshift", gate="zxpix",
         why="сдвиг по (ix+d) снова ничего не сдвигает — ровно то, что делал транслятор, роняя "
             "`sla`/`srl` в комментарий `; UNHANDLED`: мышь ходит половинным шагом. Сторож "
             "«ни одной строки UNHANDLED» при этом обойдён — порча подменяет ТЕЛО сдвига "
             "(_shift_cell), а не выключает разбор формы",
         file="tools/a8_z80_to_8080.py",
         old='    return ["ld a,(hl)"] + _shift_body(op) + ["ld (hl),a", "ld a,(il_a)", "ld hl,(il_tmp2)"]',
         new='    return ["ld a,(hl)"] + [] + ["ld (hl),a", "ld a,(il_a)", "ld hl,(il_tmp2)"]   # ПОРЧА: ячейка (ix+d) не сдвигается'),
    dict(name="plane1", gate="check_plane1",
         why="дыры вне картинки сдвинуты со строки 224 на 200: под код отданы строки ВНУТРИ "
             "картинки (200..223 каждого столбца буфера). Ассемблер такое пропускает — байты "
             "ложатся, ASSERT'ы дыр целы, — а на первом же кадре рендер их затрёт и нарисует "
             "мусором. Ловит только check_plane1: он судит по ЛИСТИНГУ, где лежит код",
         file="tools/a8_z80_to_8080.py",
         old="    h += [(base + c * 256 + 224, 64) for c in range(pages - 1)]\n"
             "    h.append((base + (pages - 1) * 256 + 224, 32))\n",
         new="    h += [(base + c * 256 + 200, 64) for c in range(pages - 1)]\n"
             "    h.append((base + (pages - 1) * 256 + 200, 32))\n"),
    dict(name="plane2", gate="check_plane2",
         why="дыры раскладчика длиннее на 16 байт: окно кончается не на 0x20 следующей страницы, "
             "а на 0x30, и код ложится в смещения 0x20..0x2F — В КАРТИНКУ плоскости 2, в самую "
             "полосу панели. Ассемблер такое пропускает молча (ASSERT'ы дыр целы, ORG законны), "
             "картинка плоскости 0 и темп не меняются вовсе — а маска HUD легла бы поверх кода, "
             "и код побелил бы точки поля. Ловит только check_plane2: он судит по ЛИСТИНГУ, "
             "где лежит код",
         file="tools/a8_z80_to_8080.py",
         old="        a, b = (p << 8) + 0xE0, min(((p + 1) << 8) + 0x20, hi)\n",
         new="        a, b = (p << 8) + 0xE0, min(((p + 1) << 8) + 0x30, hi)   # ПОРЧА: дыра в картинку\n"),
    dict(name="spill", gate="spill",
         why="очистка буфера идёт на столбец дальше края (clear_scrn_buffer: `ld b, 32` -> 33): "
             "192 записи за плоскость 1, в страницу 0xC000. ЭТО ВИДИТ ТОЛЬКО spillcheck: картинка "
             "не меняется вовсе (лишний столбец за краем буфера никто не блитит), и гейт пикселей "
             "против ZX на той же сборке остаётся ЗЕЛЁНЫМ — проверено",
         file="tools/a8_vec.py",
         old='               "        ld hl, vidbuf+32\\n        ld b, 32\\n"',
         new='               "        ld hl, vidbuf+32\\n        ld b, 33\\n"   # ПОРЧА: столбец за краем'),
    dict(name="psfix", gate="spill",
         why="ps_cw не двигает SP за непрочитанный хвост строки (снят `ld (ps_fix+1), a`): "
             "обрезанная печать разъезжается по строкам. В ИГРЕ КЛИП НЕ СРАБАТЫВАЕТ НИ РАЗУ "
             "(замер: 128 комнат, 377 740 печатей, самый правый столбец ровно 31), поэтому "
             "порча ловится только на сборке A8_PSCW=test, где край объявлен столбцом 30 — "
             "на обычной сборке она ПРОХОДИТ мимо всех гейтов, и это тоже проверено",
         file="tools/a8_vec.py",
         old="        ld (ps_fix+1), a\n",
         new="        ; ПОРЧА: SP за непрочитанный хвост не двигаем\n"),
    dict(name="varalign", gate="asmcheck",
         why="база переменных сдвинута на 32 (кратна 32, но НЕ 256). Сборка обязана упасть по "
             "ASSERT'у: upd_42/43 берут случайность из младшего байта указателя записи "
             "(push ix/pop bc/ld a,c/rrca/and 0x10), и сдвиг базы переворачивает поворот у всех "
             "объектов с нечётным номером. ЗАМЕРЕНО, что без ASSERT'а это стоит 5 красных комнат "
             "из 128 (48, 60, 79, 97, 247), а ШЕСТЬ гейтовых сценариев zxpix по 600 итераций "
             "остаются ЗЕЛЁНЫМИ — то есть ловит это только ассемблер или обход всех комнат",
         file="tools/a8_vec.py",
         old="A8_VARS    = ((A8_PLANE0 - A8_VARSLEN) // 256) * 256        # 0x7800",
         new="A8_VARS    = ((A8_PLANE0 - A8_VARSLEN) // 256) * 256 + 32   # ПОРЧА: кратно 32, не 256"),
    dict(name="plane2first", gate="regions",
         why="ПЕРВАЯ дыра плоскости 2 объявлена вдвое длиннее (0xC000..0xC03F вместо 0xC000..0xC01F): "
             "32 байта кода ложатся в полосу панели страницы 0xC0 — ровно туда, где потом встанет "
             "зона счётчика LIGHT YEARS (столбцы 4..5). ЗАМЕРЕНО: прежняя порча этого гейта "
             "(A8_UPPER = 0xCF00) стала ХОЛОСТОЙ, как только появился раскладчик: он выдаёт свои "
             "ORG'и поверх начала региона, и сдвиг A8_UPPER не меняет ни байта образа — поэтому "
             "порча заменена. a8_regions судит РАЗМЕЩЕНИЕ по одному листингу, без сценария и без "
             "прогона, за 0.1 с; check_plane2 ловит ту же порчу, но только своим --walk",
         file="tools/a8_z80_to_8080.py",
         old="    wins = [(lo, min(lo + 0x20, hi) - lo)]\n",
         new="    wins = [(lo, min(lo + 0x40, hi) - lo)]   # ПОРЧА: первая дыра в картинку\n"),
    dict(name="hudzone", gate="hudcolor",
         why="зона счётчика LIGHT YEARS сдвинута на 4 строки (0xC4, 2, 56 -> 60): маска "
             "закрывает не знакоместо ZX, а его половину, и цифры счётчика режутся на два "
             "цвета — верх белый, низ цветом комнаты. Ассемблер и все гейты плоскости 0 при "
             "этом ЗЕЛЁНЫЕ: картинка, состояние и темп не меняются ни на бит, маска живёт в "
             "ДРУГОЙ плоскости. Проверки «вне зон плоскость 2 = 0» и «зона заполнена целиком» "
             "порчу тоже не видят — они читают ту же испорченную таблицу; ловит её только "
             "проверка «знакоместо одного цвета»",
         file="tools/a8_vec.py",
         old="vec_hudcols:\tDB\t\t0xC4, 2, 56, 8",
         new="vec_hudcols:\tDB\t\t0xC4, 2, 60, 8   ; ПОРЧА: зона сдвинута на 4 строки"),
    dict(name="hudat", gate="hudfilm",
         why="маска белого HUD ставится в ОБЩЕЙ точке блока (loc_A724) вместо ветки с панелью "
             "(A8_HUD_AT: panel -> common). Через loc_A724 проходят ДВЕ дороги, и вторая — "
             "loc_A741, флаг `byte_5B24 != 0` — это экран RE-PROGRAMMING (сборка робота после "
             "GAME OVER): панели там нет, colour_something не вызывается, на ZX весь экран "
             "остаётся ярко-красным от clr_attr. Маска белила рамку — ЭТО ТОТ САМЫЙ ДЕФЕКТ, "
             "который владелец увидел на MiSTer 2026-09-16. ЗАМЕР НЕВАКУУМНОСТИ: при этой "
             "порче ЗЕЛЁНЫЕ и zxpix, и локстеп, и roomsweep, и одиночный hudcolor по меню, "
             "GAME OVER и игровой комнате — краснеет ТОЛЬКО плёнка (12 кадров из 106, "
             "466 точек рамки покрашены белым пером)",
         file="tools/a8_vec.py",
         old="A8_HUD_AT = os.environ.get('A8_HUD_AT', 'panel')",
         new="A8_HUD_AT = os.environ.get('A8_HUD_AT', 'common')   # ПОРЧА: маска на обеих дорогах"),
    dict(name="spresv", gate="spcheck",
         why="буфер под стеком урезан с 256 до 32 байт: замеренная глубина (44 Б на ходьбе, 68 Б "
             "на обходе комнат) в него не влезает, то есть стек сел бы на код нижнего региона. "
             "Ассемблер этого не видит — ASSERT потолка кода при этом ЗЕЛЁНЫЙ, кода там ещё "
             "2 КБ свободных, — видит только замер глубины",
         file="tools/a8_vec.py",
         old="A8_SP_RESV = 0x100      # буфер под стеком.",
         new="A8_SP_RESV = 0x20       # ПОРЧА: буфер под стеком."),
    dict(name="ladder", gate="recolour",
         why="лесенка audio_msx_ladder снова не бережёт DE (`push de` -> `push hl`: на выходе "
             "DE := HL входа): счётчик D перекраски loc_B005 (вентиль на гнезде криокамеры) "
             "портится, 16 ступеней мигания не выходят. Сценарии стенда этот путь не достают — "
             "ни локстеп, ни zxpix, ни гейты гибели его не видят",
         file="tools/a8_sound_ay.py",
         old="        push de\n        xor a\n        ld (msx_si), a                          ; слот 0 -> канал A\n",
         new="        push hl\n        xor a\n        ld (msx_si), a                          ; слот 0 -> канал A\n"),
    dict(name="splashzone", gate="splashzone",
         why="итоговый релиз: ISR заставки каждый кадр пишет байт в 0x228B — в свободную память "
             "над своим стеком (её потом затирает распаковка потока L). Картинка, мелодия (c64tune), "
             "распаковка (unpack) и старт игры целы — ловит только трасса писателей заставки",
         file="tools/a8_pack.py",
         old="\t\t\t\tld\t\t(spl_flag), a\n\t\t\t\tpop\t\thl\n",
         new="\t\t\t\tld\t\t(spl_flag), a\n\t\t\t\tld\t\t(spl_stack_top), a\t; ПОРЧА\n\t\t\t\tpop\t\thl\n"),
    dict(name="unpackbyte", gate="unpack",
         why="итоговый релиз: один бит одного байта потока L (смещение 5000) инвертирован при сборке "
             "образа — модель упаковщика видит чистый поток и пропускает; распаковка на Векторе даёт "
             "не образ эталона (или игра не доходит до START)",
         file="tools/a8_pack.py",
         old="    s.append(_db(cl))\n",
         new="    s.append(_db(cl[:5000] + bytes([cl[5000] ^ 0x01]) + cl[5001:]))   # ПОРЧА\n"),
    dict(name="unpackdelta", gate="unpack",
         why="поток L лёг на 4 байта ниже запаса delta и модель in-place упаковщика отключена: "
             "распаковщик на месте пишет в ещё не прочитанный байт потока — стенд ловит чтение "
             "затёртого и расхождение с эталоном",
         file="tools/a8_pack.py",
         old='    shift = int(os.environ.get("A8_PACK_SHIFT", "0"))   # ТОЛЬКО для негативного контроля\n',
         new='    shift = 4; os.environ["A8_PACK_NOCHECK"] = "1"   # ПОРЧА\n'),
    dict(name="c64tick", gate="c64tune",
         why="итоговый релиз: тик мелодии заставки шагает по записям голосов на 40 вместо 41 — "
             "голоса B и C читают чужое состояние; картинка, распаковка и игра целы",
         file="tools/a8_pack.py",
         old="\t\t\t\tadd\t\ta, 41\n",
         new="\t\t\t\tadd\t\ta, 40\t\t; ПОРЧА\n"),
    dict(name="splashpal", gate="splashpix",
         why="итоговый релиз: ISR заставки грузит палитру со сдвигом на запись (spl_pal+14 вместо "
             "+15) — плоскости в памяти целы, мелодия и распаковка тоже; неверны только цвета на экране",
         file="tools/a8_pack.py",
         old="\t\t\t\tld\t\thl, spl_pal + 15\n",
         new="\t\t\t\tld\t\thl, spl_pal + 14\t; ПОРЧА\n"),
    dict(name="unpackp2", gate="unpack",
         why="итоговый релиз: стековая заливка ступени 2 кроет 0x8000..0xBFFF вместо 0x8000..0xDFFF — "
             "картинка заставки остаётся в плоскости 2 (селектор белого HUD) к START; сторож "
             "a8_regions для итогового релиза плоскость 2 пропускает (там картинка на время "
             "заставки) — ловит проверка чистоты плоскости 2 к START в стенде распаковки",
         file="tools/a8_pack.py",
         old="\t\t\t\tld\t\thl, 0xE000\t\t\t; заливка, 2 Б за push (под di, стек — ниже в SP)\n"
             "\t\t\t\tld\t\tsp, hl\n\t\t\t\tld\t\tbc, 0x0300",
         new="\t\t\t\tld\t\thl, 0xC000\t; ПОРЧА\n"
             "\t\t\t\tld\t\tsp, hl\n\t\t\t\tld\t\tbc, 0x0200"),
    dict(name="splashroom", gate="regions",
         why="итоговый релиз: стек заставки раздут до 7000 Б — код, мелодия, потоки H/P3 и стек "
             "налезают на поток L; новая строка регионов (ASSERT под потоком L) обязана покраснеть",
         file="tools/a8_pack.py",
         old='spl_stack:\\t\\tDS\\t\\t128',
         new='spl_stack:\\t\\tDS\\t\\t7000'),
    dict(name="bootpal", gate="tracecmp",
         why="итоговый релиз: хвост ступени 2 не зовёт vec_set_pal 7 (как vec_boot эталона) — "
             "распаковка байт в байт та же (гейт unpack зелёный: ячейки палитры просто остаются как "
             "в образе), но игра стартует с чёрной палитрой вместо белой: ISR грузит в порт 0x0C "
             "другое, чем у эталона из той же точки",
         file="tools/a8_pack.py",
         old="\t\t\t\tcall\tG_VEC_SET_PAL\t\t; белая палитра меню, как vec_boot\n",
         new="\t\t\t\tor\t\ta\t\t; ПОРЧА\n"),
    dict(name="roomsilence", gate="aycheck",
         why="снято глушение ВИ53 на входе в game_loop: на смене комнаты счётчик держит последний "
             "делитель всю отрисовку новой комнаты (~38 кадров) — дефект с железа",
         file="tools/a8_sound_ay.py",
         old='"game_loop:\\n        call msx_tv_mute   ; смена комнаты / после гибели: нота не висит на отрисовке\\n"',
         new='"game_loop:\\n"'),
    dict(name="gameoversilence", gate="aycheck",
         why="снято глушение ВИ53 на входе в game_over: нота висит на экране GAME OVER до мелодии",
         file="tools/a8_sound_ay.py",
         old='"game_over:\\n        call msx_tv_mute   ; GAME OVER: экран рисуется без слива\\n"',
         new='"game_over:\\n"'),
    dict(name="pausesilence", gate="aycheck",
         why="снято глушение ВИ53 на паузе: нота висит, пока держат ВК",
         file="tools/a8_sound_ay.py",
         old='"        ret nz\\n        call msx_tv_mute   ; пауза: нота не висит, пока держат ВК\\na8_pz_rel:\\n"',
         new='"        ret nz\\na8_pz_rel:\\n"'),
    dict(name="sfx", gate="aycheck",
         why="период шума эффекта 1 маскируется 0x0F вместо 0x1F: R6, а с ним делитель шума "
             "(R6&0x1F)*256 на ВИ53 расходятся с моделью MSX. Прежняя порча 0x3F на ВИ53 мертва — "
             "слив сам берёт R6 & 0x1F (mvc_noise), и гейт её справедливо пропускал",
         file="tools/a8_sound_ay.py",
         old="\t\t\t\tcpl\n\t\t\t\tand\t\t0x1F\n\t\t\t\tld\t\tb, a\n\t\t\t\tld\t\tc, 6\n",
         new="\t\t\t\tcpl\n\t\t\t\tand\t\t0x0F\n\t\t\t\tld\t\tb, a\n\t\t\t\tld\t\tc, 6\n"),
]

ENV = {"i8080": {"A8_GATECHECK_I8080": "1"},
       "ixflags": {"A8_GATECHECK_IXFLAGS": "1"},
       "djnz": {"A8_GATECHECK_DJNZ": "1"}}

# гейты, живущие ВНУТРИ ./build.sh vec: код возврата у них общий (build.sh падает по set -e),
# поэтому дополнительно проверяется, что покраснел именно нужный — по его собственной строке-итогу
INBUILD = {
    "check_i8080":  re.compile(r'check_i8080: инструкций \d+, Z80-only (\d+)'),
    "check_ixflags": re.compile(r'check_ixflags: чтений испорченного переноса (\d+)'),
    "check_djnz":   re.compile(r'check_djnz: чтений флагов после djnz (\d+)'),
    "check_plane1": re.compile(r'check_plane1: В КАРТИНКЕ БУФЕРА (\d+) байт'),
    "check_plane2": re.compile(r'check_plane2(?: --walk)?: КАРТИНКУ ПЛОСКОСТИ 2 ЗАНИМАЮТ (\d+) байт'),
}


def run(cmd, env=None, cwd=ROOT):
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, text=True)


def build(target, env=None):
    return run(["./build.sh", target], env=env)


def gate_result(gate, env=None):
    """-> (rc, хвост вывода). rc != 0 = гейт покраснел."""
    if gate in INBUILD:
        r = build("vec", env)
        out = r.stdout + r.stderr
        m = INBUILD[gate].search(out)
        # красным считается только «покраснел ИМЕННО ЭТОТ гейт»: build.sh падает по set -e,
        # и ненулевой код сам по себе ещё не говорит, кто именно нашёл порчу
        rc = 1 if (r.returncode and m and int(m.group(1)) > 0) else 0
        return rc, out[-400:]
    if gate == "lockstep":
        # обе сборки: с компактными хелперами (по умолчанию) и с развёрткой (ix+d), как в
        # игре (A8_IX_HOT=1). Порча обязана краснеть в ОБЕИХ — иначе гейт проверяет не тот код.
        for hot in (None, "1"):
            e = dict(env or {})
            if hot:
                e["A8_IX_HOT"] = hot
            b = build("lockstep", e)
            if b.returncode:
                return b.returncode, (b.stdout + b.stderr)[-400:]
            for tag, inp, jrn in SCEN:
                r = run(["node", "tools/lockstep_vec.js", "build/alien8_8080.r0m",
                         "build/alien8_8080.sld", "600",
                         os.path.join(STAND, inp), os.path.join(STAND, jrn)], e)
                if r.returncode:
                    return r.returncode, ("hot=%s %s: " % (hot, tag)) + (r.stdout + r.stderr)[-300:]
        return 0, "все шесть прогонов (2 сборки x 3 сценария) зелёные"
    if gate == "asmcheck":
        # ГЕЙТ — САМ АССЕМБЛЕР. Порча обязана уронить сборку по ASSERT'у, а не просто
        # «как-нибудь»: код возврата тут общий у всего build.sh, поэтому вердикт выносится
        # по слову ASSERT в выводе sjasmplus.
        b = build("vec", env)
        out = b.stdout + b.stderr
        rc = 1 if (b.returncode and re.search(r'(?i)assert', out)) else 0
        return rc, out[-400:]
    if gate == "hudcolor":
        # ГЕЙТ БЕЛОГО HUD. Снимается четыре экрана, и у каждого своя сторона проверки:
        # две игровые комнаты с РАЗНЫМ цветом (маска обязана стоять и знакоместа быть
        # одноцветными по перу HUD) и два экрана БЕЗ панели — меню и GAME OVER, где маска
        # обязана быть погашена (в Knight Lore именно на GAME OVER она белила рамку кусками).
        b = build("vec", env)
        if b.returncode:
            return b.returncode, (b.stdout + b.stderr)[-400:]
        for tag, shot, hc in HUDSCEN:
            e = dict(env or {})
            e.update(shot)
            e["A8HS_DUMP"] = "build/gate_hud.txt"
            r = run(["node", "tools/hudshot_vec.js", "build/alien8_vec.r0m",
                     "build/alien8_vec.sld", e.pop("_iters", "40"), "build/gate_hud.png"], e)
            if r.returncode:
                return r.returncode, (tag + ": снимок не снялся: ") + (r.stdout + r.stderr)[-300:]
            r = run(["python3", "tools/hudcolor.py"] + hc + ["build/gate_hud.txt"], env)
            if r.returncode:
                return r.returncode, (tag + ": ") + (r.stdout + r.stderr)[-300:]
        return 0, "четыре экрана: знакоместа одноцветны, маска стоит в комнатах и погашена вне их"
    if gate == "hudfilm":
        # ПЛЁНКА: маска белого HUD на КАЖДОМ кадре перехода. Одиночный снимок сюда не достаёт —
        # дефект живёт РОВНО между гашением и показом (замер: при A8_HUD_AT=common одиночные
        # hudcolor по меню, GAME OVER и комнате ЗЕЛЁНЫЕ, а плёнка краснеет 12 кадрами).
        b = build("vec", env)
        if b.returncode:
            return b.returncode, (b.stdout + b.stderr)[-400:]
        d = os.path.join(ROOT, HUDFILM['dirn'])
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
        with open(os.path.join(ROOT, HUDFILM['keys']), 'w') as fh:
            for k in ('z', 'x', 'a', 'q', 'space', '0', '1', '2', '3'):
                fh.write('700 %s up\n' % k)
            for fr in range(760, 3000, 80):
                fh.write('%d 0 down\n%d 0 up\n' % (fr, fr + 24))
        e = dict(env or {})
        e.update(HUDFILM['env'])
        e['A8HS_KEYS'] = HUDFILM['keys']
        e['A8HS_INPUTS'] = os.path.join(STAND, HUDFILM['inputs'])
        e['A8HS_FILM'] = os.path.join(HUDFILM['dirn'], 'f')
        r = run(["node", "tools/hudshot_vec.js", "build/alien8_vec.r0m", "build/alien8_vec.sld",
                 HUDFILM['iters'], "build/gate_film.png"], e)
        if r.returncode:
            return r.returncode, "плёнка не снялась: " + (r.stdout + r.stderr)[-300:]
        r = run(["python3", "tools/hudfilm.py", HUDFILM['dirn']], env)
        return r.returncode, (r.stdout + r.stderr)[-400:]
    if gate == "regions":
        b = build("vec", env)
        if b.returncode:
            return b.returncode, (b.stdout + b.stderr)[-400:]
        # и релизная сборка (A8_SPLASH=1): у неё свои блоки в нижнем регионе и зоны заставки.
        # 2026-09-23 релиз не собирался (нижний регион 0x78F6 > 0x7700), а гейт смотрел
        # только vec — перебор прожил три коммита незамеченным.
        b = build("release", env)
        if b.returncode:
            return b.returncode, "release: " + (b.stdout + b.stderr)[-400:]
        r = run(["python3", "tools/a8_regions.py", "build/alien8_vec.lst",
                 "build/alien8_release_ref.lst", "build/alien8_release.lst"], env)
        return r.returncode, (r.stdout + r.stderr)[-400:]
    if gate == "splashzone":
        # ИТОГОВЫЙ РЕЛИЗ: до клавиши исполняется только код заставки (игра сжата) — писать он
        # может только в своё ОЗУ (ячейки, голоса мелодии, стек); потоки, мелодия, код и картинка
        # на заставке неприкосновенны
        b = build("release", env)
        if b.returncode:
            return b.returncode, "release: " + (b.stdout + b.stderr)[-400:]
        r = run(["node", "tools/splashzone_vec.js", "build/alien8_release.r0m",
                 "build/alien8_release.sld"], env)
        return r.returncode, (r.stdout + r.stderr)[-400:]
    if gate == "c64tune":
        # МЕЛОДИЯ C64 НА ЗАСТАВКЕ ИТОГОВОГО РЕЛИЗА: 8527 кадров x 3 счётчика ВИ53 против decode()
        # tools/a8_tune_c64.py; «0» -> PC в START (~124 кадра: распаковка) и таблицы на 0xF100
        b = build("release", env)
        if b.returncode:
            return b.returncode, "release: " + (b.stdout + b.stderr)[-400:]
        r = run(["node", "tools/c64tune_vec.js", "build/alien8_release.r0m"], env)
        return r.returncode, (r.stdout + r.stderr)[-400:]
    if gate == "splashpix":
        # ПИКСЕЛИ 16-ЦВЕТНОЙ ЗАСТАВКИ на кадрах 40 и 8500: плоскости в памяти, защёлкнутая палитра
        # и кадр эмулятора (картинка + чёрные поля/бордюр) против выхода tools/a8_splash.py
        b = build("release", env)
        if b.returncode:
            return b.returncode, "release: " + (b.stdout + b.stderr)[-400:]
        r = run(["node", "tools/splashpix_vec.js", "build/alien8_release.r0m"], env)
        return r.returncode, (r.stdout + r.stderr)[-400:]
    if gate == "tracecmp":
        # ПОСЛЕ START — КАК ЭТАЛОН: эталон из своей точки START дважды, во втором память
        # подменена памятью итогового релиза в его START; 1500 кадров (меню, новая игра, ходьба):
        # выводы во все порты и регистры каждый кадр равны, разница памяти мертва до перезаписи
        b = build("release", env)
        if b.returncode:
            return b.returncode, "release: " + (b.stdout + b.stderr)[-400:]
        r = run(["node", "tools/tracecmp_vec.js"], env)
        return r.returncode, (r.stdout + r.stderr)[-400:]
    if gate == "unpack":
        # ИТОГОВЫЙ РЕЛИЗ (tools/a8_pack.py): распаковка на месте без чтения затёртого; к
        # spl_unpacked память == эталон (плоскость 0 — нули); к START — то же, кроме ячеек
        # ISR/vec_set_pal (те же, что пишет эталон до START); плоскость 2 чиста; 0xF100..0xFFFF
        # после START сначала пишутся, потом читаются
        b = build("release", env)
        if b.returncode:
            return b.returncode, "release: " + (b.stdout + b.stderr)[-400:]
        r = run(["node", "tools/unpack_vec.js"], env)
        return r.returncode, (r.stdout + r.stderr)[-400:]
    if gate == "spcheck":
        # ГЛУБИНА СТЕКА против зарезервированного под ним буфера (стенд берёт его размер
        # из ASSERT'а листинга). Сценарий ходьбы в стартовой комнате: 44 Б — этого хватает,
        # чтобы порча «буфер 32 Б» покраснела, а обход 128 комнат (68 Б) стоил бы 2.5 минуты.
        b = build("vec", env)
        if b.returncode:
            return b.returncode, (b.stdout + b.stderr)[-400:]
        e = dict(env or {}); e["A8_IRQDROP"] = "1"
        r = run(["node", "tools/spcheck_vec.js", "build/alien8_vec.r0m", "build/alien8_vec.sld",
                 "600", os.path.join(STAND, "inputs_alive.txt")], e)
        return r.returncode, (r.stdout + r.stderr)[-400:]
    if gate == "spill":
        # ДВЕ СБОРКИ. 1) обычная: в 0xC000-0xC7FF не должно попасть ни байта (страницы плоскости 2
        # отданы под селектор цветного HUD). 2) A8_PSCW=test, где край объявлен столбцом 30 и клип
        # срабатывает: там проверяется ИНВАРИАНТ ЧТЕНИЯ СПРАЙТА (A8PSSP) — без такой сборки ветка
        # ps_fix непроверяема, в игре клип не срабатывает ни разу.
        for tag, benv, gh in (("обычная", {}, {}),
                              ("A8_PSCW=test", {"A8_PSCW": "test"}, {"A8PSSP": "1"})):
            e = dict(env or {}); e.update(benv)
            b = build("vec", e)
            if b.returncode:
                return b.returncode, (tag + ": ") + (b.stdout + b.stderr)[-400:]
            ge = dict(env or {}); ge.update(gh); ge["A8_IRQDROP"] = "1"
            r = run(["node", "tools/spillcheck_vec.js", "build/alien8_vec.r0m", "build/alien8_vec.sld",
                     "200", os.path.join(STAND, "inputs_alive.txt")], ge)
            if r.returncode:
                return r.returncode, (tag + ": ") + (r.stdout + r.stderr)[-300:]
        return 0, "обе сборки: ни одной записи в плоскость 2, SP цепочки сходится"
    b = build("vec", env)
    if b.returncode:
        return b.returncode, (b.stdout + b.stderr)[-400:]
    if gate == "zxpix":
        # ГЕЙТ ПИКСЕЛЕЙ ПРОТИВ ZX. Дампы экрана оригинала снимает zx_screen.lua стенда
        # (LOCKSTEP.md §10) — без них спрашивать не с чего, и это НЕ «порча поймана»:
        # гейт падает по отсутствию файла, а не по расхождению.
        for tag, inp, dump, room in PIXSCEN:
            d = os.path.join(STAND, dump)
            if not os.path.exists(d):
                return 0, "НЕТ ДАМПА ЭКРАНА %s — снять zx_screen.lua (LOCKSTEP.md §10)" % d
            e = dict(env or {})
            if room:
                e["A8ROOM"] = room
            r = run(["node", "tools/zxpix_vec.js", "build/alien8_vec.r0m", "build/alien8_vec.sld",
                     "600", os.path.join(STAND, inp), d], e)
            if r.returncode:
                return r.returncode, (tag + ": ") + (r.stdout + r.stderr)[-300:]
        return 0, "все сценарии пиксель в пиксель с ZX"
    if gate == "render_gate":
        r = run(["tools/render_gate.sh", "HEAD", "40", "104"], env)
    elif gate == "flipcheck":
        r = run(["node", "tools/flipcheck_vec.js", "build/alien8_vec.r0m",
                 "build/alien8_vec.sld"], env)
    elif gate == "nobjcheck":
        # Инвариант границы проверяется на ЧЕТЫРЁХ сценариях, а не в одной стартовой комнате:
        # смена комнаты (прогулка), ГИБЕЛЬ вне стартовой комнаты (сброс состояния и повторный
        # вход) и комната 137 с робомышью. Первый покрасневший — вердикт.
        for tag, inp, room, iters in NOBJSCEN:
            e = dict(env or {})
            if room:
                e["A8ROOM"] = room
            r = run(["node", "tools/nobjcheck_vec.js", "build/alien8_vec.r0m",
                     "build/alien8_vec.sld", iters, os.path.join(STAND, inp)], e)
            if r.returncode:
                return r.returncode, (tag + ": ") + (r.stdout + r.stderr)[-300:]
        return 0, "граница цела на всех сценариях"
    elif gate == "inputcheck":
        r = run(["node", "tools/inputcheck_vec.js", "build/alien8_vec.r0m",
                 "build/alien8_vec.sld"], env)
    elif gate == "tunecheck":
        # все шесть мелодий целиком: длительность в кадрах против модели MSX
        r = run(["node", "tools/tunecheck_vec.js", "build/alien8_vec.r0m",
                 "build/alien8_vec.sld"], env)
    elif gate == "aycheck":
        # ЭФФЕКТЫ НА ВИ53: журнал tools/aytrace_vec.js (делители счётчиков 1/2 по кадрам и по
        # сливам) против модели MSX + конверсии слива (tools/aycheck.py). Сценарии: ходьба стенда
        # даёт эффекты 3,4,5,7; эффекты 1,2,8,9 ходьбой не достаются — запуск стендом (A8SFX);
        # длинный шум 180 тиков держит движок занятым весь объектный цикл — инвариант 56 тиков;
        # A8LADDER — путь криокамеры loc_AFF8 с лесенкой (8 сливов на вызов, мимо msx_frame_off)
        for tag, iters, inp, ev, *need in AYSCEN:
            e = dict(env or {}); e.update(ev)
            t = run(["node", "tools/aytrace_vec.js", "build/alien8_vec.r0m", "build/alien8_vec.sld",
                     iters] + ([os.path.join(STAND, inp)] if inp else []), e)
            if t.returncode:
                return t.returncode, (tag + ": журнал не снялся: ") + (t.stdout + t.stderr)[-300:]
            open(os.path.join(ROOT, "build", "ay_gatecheck.txt"), "w", encoding="utf-8").write(t.stdout)
            r = run(["python3", "tools/aycheck.py", "build/ay_gatecheck.txt"]
                    + (["--need=" + need[0]] if need else []), env)
            if r.returncode:
                return r.returncode, (tag + ": ") + (r.stdout + r.stderr)[-300:]
        return 0, "все сценарии эффектов: делители ВИ53 совпали с моделью"
    elif gate == "palseq":
        # ПАЛИТРА ПРОТИВ СТИРАНИЯ ЭКРАНА: A8_IRQDROP=1 обязателен — без модели «прерывание не
        # защёлкивается» кадры под di не теряются, и момент загрузки палитры сдвигается
        e = dict(env or {}); e["A8_IRQDROP"] = "1"
        r = run(["node", "tools/palseq_vec.js", "build/alien8_vec.r0m",
                 "build/alien8_vec.sld", "250"], e)
    elif gate == "recolour":
        # ПЕРЕКРАСКА loc_AFF8 -> loc_B005 (вентиль на гнезде криокамеры): 16 ступеней мигания
        # обязаны кончиться, лесенка audio_msx_ladder — прозвучать на счётчиках 1/2 ВИ53
        r = run(["node", "tools/recolourcheck_vec.js", "build/alien8_vec.r0m",
                 "build/alien8_vec.sld"], env)
    elif gate == "kbcheck":
        # эталон tools/kbref.txt лежит В РЕПОЗИТОРИИ: без него гейт сверял бы таблицу
        # готовых ответов read_key саму с собой и любую правку vec_zxmap пропускал (§22 KL)
        r = run(["node", "tools/kbcheck_vec.js", "build/alien8_vec.r0m",
                 "build/alien8_vec.sld"], env)
    else:
        raise SystemExit("неизвестный гейт: " + gate)
    return r.returncode, (r.stdout + r.stderr)[-400:]


def main():
    want = sys.argv[1:]
    dirty = run(["git", "status", "--porcelain", "tools", "src"]).stdout.strip()
    if dirty:
        print("рабочее дерево не чистое — сначала закоммить:\n" + dirty)
        return 2
    bad = 0
    for m in MUTS:
        if want and m["name"] not in want:
            continue
        path = os.path.join(ROOT, m["file"])
        src = open(path, encoding="utf-8").read()
        n = src.count(m["old"])
        if n != 1:
            print(f"[{m['name']}] ЯКОРЬ ПОРЧИ НЕ НАЙДЕН в {m['file']} (вхождений {n}) — порча устарела")
            bad += 1
            continue
        open(path, "w", encoding="utf-8").write(src.replace(m["old"], m["new"], 1))
        # ЛОВУШКА, из-за которой порча в .py иногда не доходила до сборки: у mtime в кэше
        # .pyc разрешение в секунду, и если откат предыдущей порчи и запись следующей
        # попали в одну секунду, Python берёт СТАРЫЙ .pyc и собирает чистый код — гейт
        # «пропускает» порчу, которой в образе и нет. Кэш сносим всегда.
        shutil.rmtree(os.path.join(ROOT, "tools", "__pycache__"), ignore_errors=True)
        try:
            rc, out = gate_result(m["gate"], ENV.get(m["name"]))
        finally:
            run(["git", "checkout", "--", m["file"]])
            shutil.rmtree(os.path.join(ROOT, "tools", "__pycache__"), ignore_errors=True)
            build("lockstep"); build("vec"); build("release")   # все цели — чистыми, см. докстроку (релиз собирает гейт regions)
        ok = rc != 0
        print(f"[{m['name']}] гейт {m['gate']}: {'ПОЙМАЛ' if ok else 'ПРОПУСТИЛ'} (код {rc}) — {m['why']}")
        if not ok:
            print("   вывод гейта: " + out.replace("\n", " | ")[-300:])
            bad += 1
    print("все гейты ловят свою порчу" if not bad else f"ГЕЙТОВ-СЛЕПЫХ (или устаревших порч): {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda *a: (run(["git", "checkout", "--", "tools"]), sys.exit(130)))
    sys.exit(main())
