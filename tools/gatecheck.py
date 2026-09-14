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
  (проверено md5), поэтому спрашивать с локстепа тут нечего — он её физически не видит.
"""
import os
import re
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

MUTS = [
    dict(name="render", gate="render_gate",
         why="окно update_screen на строку ниже (приёмник ld l,32 -> 33): чистый ВЫВОД, логика не меняется",
         file="tools/a8_vec.py",
         old="us_dst:\t\t\tld\t\th, 0\t\t\t\t; патч: страница экрана\n"
             "\t\t\t\tld\t\tl, 32\t\t\t\t; HL = приёмник\n",
         new="us_dst:\t\t\tld\t\th, 0\t\t\t\t; патч: страница экрана\n"
             "\t\t\t\tld\t\tl, 33\t\t\t\t; HL = приёмник\n"),
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
    if gate == "render_gate":
        r = run(["tools/render_gate.sh", "HEAD", "40", "104"], env)
    elif gate == "flipcheck":
        r = run(["node", "tools/flipcheck_vec.js", "build/alien8_vec.r0m",
                 "build/alien8_vec.sld"], env)
    elif gate == "nobjcheck":
        r = run(["node", "tools/nobjcheck_vec.js", "build/alien8_vec.r0m",
                 "build/alien8_vec.sld", "60"], env)
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
        try:
            rc, out = gate_result(m["gate"], ENV.get(m["name"]))
        finally:
            run(["git", "checkout", "--", m["file"]])
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
