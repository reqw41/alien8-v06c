#!/usr/bin/env python3
"""Свободное место в регионах раскладки: адрес на каждом ASSERT $ <= N из листинга.
   python3 tools/a8_regions.py build/alien8_vec.lst [--holes]

Дыры вне картинки (строки 224..255/0..31 столбцов плоскости 1) — это 33 отдельных ASSERT'а,
по одному на дыру; в общей таблице они сворачиваются в ОДНУ строку-регион «дыры вне картинки».
`--holes` разворачивает их обратно — смотреть, какая дыра недобрана.

ГЕЙТ «ПЛОСКОСТЬ 2 СВОБОДНА» (код возврата 1). Под цветной HUD (селектор белого) нужны
страницы плоскости 2 БЕЗ кода и данных: C0..C7 освободил attrcut (атрибуты ZX вырезаны,
печать обрезана по столбцу 31), C8..CF — переезд переменных игры в нижний регион. Проверка
идёт ПО ЛИСТИНГУ: где ассемблер положил байты и что зарезервировал `DS`. Диапазон —
A8_P2=C000-CFFF (0xD000..0xDFFF пока занят верхним регионом кода, это следующий шаг).

Почему по листингу, а не стендом: tools/spillcheck_vec.js судит ЗАПИСИ в эти адреса и
о коде, который там просто ЛЕЖИТ, ничего не знает — такой код гейт записей не увидит,
а на экране он всё равно побелит точки поля. Гейты дополняют друг друга."""
import os
import re
import sys

lst = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else 'build/alien8_vec.lst'
detail = '--holes' in sys.argv
RE_HOLE = re.compile(r'дыра (0x[0-9a-fA-F]+) \((\d+) Б\)')
hn = hsz = hused = 0
lines = open(lst, encoding='utf-8', errors='replace').read().split('\n')
for l in lines:
    m = re.search(r'^\s*\d+\s+([0-9A-F]{4}).*ASSERT \$ <= (0x[0-9a-fA-F]+)', l)
    if not m:
        continue
    cur, lim = int(m.group(1), 16), int(m.group(2), 16)
    h = RE_HOLE.search(l)
    if h and not detail:
        hn += 1
        hsz += int(h.group(2))
        hused += int(h.group(2)) - (lim - cur)
        continue
    print("%-40s текущий %04X, предел %04X, свободно %d" %
          (l.split(';')[-1].strip()[:40], cur, lim, lim - cur))
if hn:
    print("%-40s занято %d из %d в %d дырах, свободно %d" %
          ("дыры вне картинки (плоскость 1)", hused, hsz, hn, hsz - hused))

# ---- ГЕЙТ: в плоскости 2 ни кода, ни данных ----
LO, HI = (int(x, 16) for x in os.environ.get('A8_P2', 'C000-CFFF').split('-'))
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
        if LO <= a + j <= HI:
            busy.setdefault(a + j, l.rstrip()[:100])
if busy:
    print("ПЛОСКОСТЬ 2 %04X-%04X: ЗАНЯТО %d байт" % (LO, HI, len(busy)))
    seen = set()
    for a in sorted(busy)[:400]:
        if busy[a] in seen:
            continue
        seen.add(busy[a])
        print("  %04X  %s" % (a, busy[a]))
        if len(seen) >= 8:
            break
    print("КРАСНЫЙ: под селектор белого HUD эти страницы обязаны быть пусты")
    sys.exit(1)
print("ПЛОСКОСТЬ 2 %04X-%04X: свободна — ни байта кода, ни байта данных" % (LO, HI))
