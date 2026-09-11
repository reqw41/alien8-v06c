#!/usr/bin/env python3
"""Сколько байт занимает сборка: сумма байт, напечатанных в листинге sjasmplus.
   python3 tools/a8_size.py build/alien8_vec.lst"""
import re, sys
tot = 0
for l in open(sys.argv[1], encoding='latin1'):
    m = re.match(r'^\s*\d+\+?\s+([0-9A-F]{4})\s+((?:[0-9A-F]{2}\s)+)', l)
    if m:
        tot += len(m.group(2).split())
print(tot)
