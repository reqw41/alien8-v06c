#!/usr/bin/env python3
"""Свободное место в регионах раскладки: адрес на каждом ASSERT $ <= N из листинга.
   python3 tools/a8_regions.py [листинг ...] [--holes]
   (без листингов — build/alien8_vec.lst и, если собраны, эталон релиза build/alien8_release_ref.lst
    и итоговый релиз build/alien8_release.lst; код 1 при переборе)

Дыры вне картинки (строки 224..255/0..31 столбцов плоскости 1) — это 33 отдельных ASSERT'а,
по одному на дыру; в общей таблице они сворачиваются в ОДНУ строку-регион «дыры вне картинки».
`--holes` разворачивает их обратно — смотреть, какая дыра недобрана.

ГЕЙТ «КАРТИНКА ПЛОСКОСТИ 2 ЧИСТА» (код возврата 1). Плоскость 2 — селектор белого HUD, то
есть БИТ ИНДЕКСА ПАЛИТРЫ: единичный бит в картинке белит точки поля. Картинка в столбцовой
раскладке — смещения 0x20..0xDF КАЖДОЙ страницы 0xC0..0xDF; код и данные допустимы только в
дырах вне картинки (0xE0..0xFF страницы n + 0x00..0x1F страницы n+1, 64 Б подряд, 2048 Б
всего). Проверка идёт ПО ЛИСТИНГУ: где ассемблер положил байты и что зарезервировал `DS`.
Диапазон — A8_P2=C000-DFFF, смещения картинки — A8_P2_PIC=20-DF.

Почему по листингу, а не стендом: tools/spillcheck_vec.js судит ЗАПИСИ в эти адреса и
о коде, который там просто ЛЕЖИТ, ничего не знает — такой код гейт записей не увидит,
а на экране он всё равно побелит точки поля. Гейты дополняют друг друга."""
import os
import re
import sys

detail = '--holes' in sys.argv
RE_HOLE = re.compile(r'дыра (0x[0-9a-fA-F]+) \((\d+) Б\)')
HOLES = {1: ('дыры вне картинки (плоскость 1)', 0xA000, 0xC000),
         2: ('дыры вне картинки (плоскость 2)', 0xC000, 0xE000)}
def check(lst):
    over = 0
    hn = {1: 0, 2: 0}; hsz = {1: 0, 2: 0}; hused = {1: 0, 2: 0}
    lines = open(lst, encoding='utf-8', errors='replace').read().split('\n')
    for l in lines:
        m = re.search(r'^\s*\d+\s+([0-9A-F]{4}).*ASSERT \$ <= (0x[0-9a-fA-F]+)', l)
        if not m:
            continue
        cur, lim = int(m.group(1), 16), int(m.group(2), 16)
        if lim > 0xFFFF and cur < 0x100:
            cur += 0x10000       # зона до конца памяти: адрес $ = 0x10000 листинг печатает как 0000
        h = RE_HOLE.search(l)
        pl = next((k for k, (_, lo, hi) in HOLES.items() if lo < lim <= hi), None)
        if h and pl and not detail:
            hn[pl] += 1
            hsz[pl] += int(h.group(2))
            hused[pl] += int(h.group(2)) - (lim - cur)
            continue
        print("%-40s текущий %04X, предел %04X, свободно %d%s" %
              (l.split(';')[-1].strip()[:40], cur, lim, lim - cur, '   <<< ПЕРЕБОР' if lim < cur else ''))
        if lim < cur:
            over = 1
    for pl, (name, _, _) in HOLES.items():
        if hn[pl]:
            print("%-40s занято %d из %d в %d дырах, свободно %d" %
                  (name, hused[pl], hsz[pl], hn[pl], hsz[pl] - hused[pl]))

    # ---- ГЕЙТ: в плоскости 2 ни кода, ни данных ----
    # ИСКЛЮЧЕНИЕ — итоговый релиз (tools/a8_pack.py, метка spl_plane2): на время заставки
    # плоскость 2 — картинка 16 цветов, игра в ней не лежит (сжата). Раскладку игры судит
    # листинг эталона build/alien8_release_ref.lst (строками выше и этим же гейтом), а то,
    # что к START плоскость 2 чиста, — tools/unpack_vec.js по памяти эмулятора.
    if any(re.search(r'\bspl_plane2:', l) for l in lines):
        print("КАРТИНКА ПЛОСКОСТИ 2: итоговый релиз — на заставке там картинка (исключение); к START "
              "чистоту проверяет tools/unpack_vec.js, игру — листинг эталона alien8_release_ref.lst")
        return over
    LO, HI = (int(x, 16) for x in os.environ.get('A8_P2', 'C000-DFFF').split('-'))
    PIC_LO, PIC_HI = (int(x, 16) for x in os.environ.get('A8_P2_PIC', '20-DF').split('-'))
    # ЛОВУШКА ЛИСТИНГА: колонка байт обрезана («00 00 00...» у `DS 1664`, у длинных DB — тоже),
    # поэтому считать занятое по числу напечатанных байт НЕЛЬЗЯ. Длина берётся как РАЗНОСТЬ
    # адресов соседних содержательных строк — она точна для любой директивы.
    RE_CONTENT = re.compile(r'^\s*\d+\+?\s+([0-9A-F]{4})\s+(?:[0-9A-F]{2}[\s.]|DS\b)')
    RE_ADDR = re.compile(r'^\s*\d+\+?\s+([0-9A-F]{4})\s')
    content = []     # (адрес, строка) — только то, что занимает место
    addrs = []       # адрес каждой строки листинга с адресной колонкой (для длины по разности)
    for l in lines:
        m = RE_ADDR.match(l)
        if not m:
            continue
        a = int(m.group(1), 16)
        addrs.append(a)
        if RE_CONTENT.match(l) or re.search(r'(?i)(?:^|\s)DS\s', l.split(';')[0]):
            content.append((len(addrs) - 1, a, l))
    busy = {}
    for k, (i, a, l) in enumerate(content):
        nxt = addrs[i + 1] if i + 1 < len(addrs) else a
        n = nxt - a if nxt > a else 1
        for j in range(min(n, HI - LO + 2)):
            if LO <= a + j <= HI and PIC_LO <= ((a + j) & 0xFF) <= PIC_HI:
                busy.setdefault(a + j, l.rstrip()[:100])
    if busy:
        print("КАРТИНКА ПЛОСКОСТИ 2 %04X-%04X (смещения %02X..%02X): ЗАНЯТО %d байт"
              % (LO, HI, PIC_LO, PIC_HI, len(busy)))
        seen = set()
        for a in sorted(busy)[:400]:
            if busy[a] in seen:
                continue
            seen.add(busy[a])
            print("  %04X  %s" % (a, busy[a]))
            if len(seen) >= 8:
                break
        print("КРАСНЫЙ: селектор белого HUD побелит этими байтами точки поля")
        return 1
    print("КАРТИНКА ПЛОСКОСТИ 2 %04X-%04X (смещения %02X..%02X): чиста — ни байта кода, ни байта "
          "данных; код и данные только в дырах вне картинки" % (LO, HI, PIC_LO, PIC_HI))
    return over


# Без аргументов — ВСЕ цели: vec, эталон релиза (A8_SPLASH=1, build/alien8_release_ref.lst) и
# итоговый релиз (tools/a8_pack.py, build/alien8_release.lst — зоны заставки), каждая
# отдельным блоком строк. Релиз кладёт свой код в нижний регион и в зоны заставки, поэтому
# перебор у него свой: 2026-09-23 релиз не собирался (нижний регион 0x78F6 > 0x7700), а
# регионы смотрели только vec — и перебора никто не видел. Код возврата 1 — если хоть у
# одного листинга регион в минусе или картинка плоскости 2 занята.
args = [a for a in sys.argv[1:] if not a.startswith('-')]
if not args:
    args = ['build/alien8_vec.lst']
    for extra in ('build/alien8_release_ref.lst', 'build/alien8_release.lst'):
        if os.path.exists(extra):
            args.append(extra)
rc = 0
for lst in args:
    if len(args) > 1:
        print("==== %s ====" % lst)
    rc |= check(lst)
sys.exit(rc)
