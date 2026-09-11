#!/usr/bin/env python3
"""Свободное место в регионах раскладки: адрес на каждом ASSERT $ <= N из листинга.
   python3 tools/a8_regions.py build/alien8_vec.lst"""
import re, sys
for l in open(sys.argv[1], encoding='utf-8', errors='replace'):
    m = re.search(r'^\s*\d+\s+([0-9A-F]{4}).*ASSERT \$ <= (0x[0-9a-fA-F]+)', l)
    if m:
        cur, lim = int(m.group(1), 16), int(m.group(2), 16)
        print("%-40s текущий %04X, предел %04X, свободно %d" %
              (l.split(';')[-1].strip()[:40], cur, lim, lim - cur))
