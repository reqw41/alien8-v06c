#!/usr/bin/env python3
"""Свободное место в регионах раскладки: адрес на каждом ASSERT $ <= N из листинга.
   python3 tools/a8_regions.py build/alien8_vec.lst [--holes]

Дыры вне картинки (строки 224..255/0..31 столбцов плоскости 1) — это 33 отдельных ASSERT'а,
по одному на дыру; в общей таблице они сворачиваются в ОДНУ строку-регион «дыры вне картинки».
`--holes` разворачивает их обратно — смотреть, какая дыра недобрана."""
import re, sys

lst = sys.argv[1] if len(sys.argv) > 1 else 'build/alien8_vec.lst'
detail = '--holes' in sys.argv
RE_HOLE = re.compile(r'дыра (0x[0-9a-fA-F]+) \((\d+) Б\)')
hn = hsz = hused = 0
for l in open(lst, encoding='utf-8', errors='replace'):
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
