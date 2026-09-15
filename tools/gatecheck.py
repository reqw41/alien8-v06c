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
NOBJSCEN = [('покой', 'inputs_idle.txt', None, '60'),
            ('прогулка', 'inputs_walk.txt', None, '600'),
            ('гибель в соседней', 'inputs_death.txt', None, '600'),
            ('137 + гибель', 'inputs_death137.txt', '137', '600')]

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
    dict(name="tune", gate="tunecheck",
         why="команда END потока нот не распознаётся (cp 7 -> cp 8): мелодия не кончается",
         file="tools/a8_sound_ay.py",
         old="\t\t\t\tcp\t\t7\n\t\t\t\tjp\t\tz, mf_end\n",
         new="\t\t\t\tcp\t\t8\n\t\t\t\tjp\t\tz, mf_end\n"),
    dict(name="mousetbl", gate="zxpix",
         why="снята починка адреса таблицы направлений робомыши: обратно `sub_B0E7+0x21` — "
             "смещение, верное только для длины тела НА Z80. Это и был дефект владельца "
             "(«враг забился в угол»): мышь читала три байта из хвоста собственного кода и "
             "получала нулевое направление. КРАСНЕЕТ ТОЛЬКО НА КОМНАТЕ 137 — в стартовой "
             "комнате и в комнатах 39/48/56/88/104 робомыши нет вовсе, и все прежние "
             "сценарии гейта эту порчу пропускают",
         file="tools/a8_native_logic.py",
         old='               "        ld hl, a8_mouse_dirs   ; A8: тело длиннее оригинала на 3 байта, смещение 0x21 не годится\\n",\n',
         new='               "        ld hl, sub_B0E7+0x21   ; ПОРЧА: снова смещение длины тела Z80\\n",\n'),
    dict(name="ixshift", gate="zxpix",
         why="`sla` по (ix+d) снова роняется в комментарий (как делал транслятор): мышь ходит "
             "половинным шагом. Сторож «ни одной строки UNHANDLED» при этом обойдён — порча "
             "подменяет само тело сдвига, а не выключает вставку",
         file="tools/a8_native_logic.py",
         old="_SHIFT_BODY = {'sla': ['add a,a'], 'srl': ['or a', 'rra']}",
         new="_SHIFT_BODY = {'sla': ['nop'], 'srl': ['or a', 'rra']}   # ПОРЧА: sla ничего не сдвигает"),
    dict(name="sfx", gate="aycheck",
         why="период шума эффекта 1 маскируется 0x3F вместо 0x1F: R6 расходится с моделью MSX",
         file="tools/a8_sound_ay.py",
         old="\t\t\t\tcpl\n\t\t\t\tand\t\t0x1F\n\t\t\t\tld\t\tb, a\n\t\t\t\tld\t\tc, 6\n",
         new="\t\t\t\tcpl\n\t\t\t\tand\t\t0x3F\n\t\t\t\tld\t\tb, a\n\t\t\t\tld\t\tc, 6\n"),
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
        # эффект 1 (шум) сценарием ходьбы не достаётся — запускаем принудительно,
        # журнал записей AY сверяется с моделью поканально
        e = dict(env or {}); e["A8SFX"] = "1:0:31:0:0"
        t = run(["node", "tools/aytrace_vec.js", "build/alien8_vec.r0m",
                 "build/alien8_vec.sld", "60"], e)
        open(os.path.join(ROOT, "build", "ay_gatecheck.txt"), "w", encoding="utf-8").write(t.stdout)
        r = run(["python3", "tools/aycheck.py", "build/ay_gatecheck.txt"], env)
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
            build("lockstep"); build("vec")      # обе цели — чистыми, см. докстроку
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
