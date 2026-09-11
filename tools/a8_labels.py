#!/usr/bin/env python3
"""Карта меток из .sld sjasmplus: имя -> адрес.

    python3 tools/a8_labels.py build/alien8_zx.sld [имя ...]
Без имён печатает весь список, отсортированный по адресу.
"""
import sys, json


def load(path):
    labs = {}
    for l in open(path):
        f = l.rstrip('\n').split('|')
        if len(f) >= 8 and f[6] in ('F', 'L', 'D') and f[5].isdigit():
            labs[f[7]] = int(f[5])
    return labs


if __name__ == '__main__':
    labs = load(sys.argv[1])
    if len(sys.argv) > 2:
        if sys.argv[2] == '--json':
            print(json.dumps(labs, indent=0, sort_keys=True))
        else:
            for n in sys.argv[2:]:
                print(f'{n:28s} {labs.get(n, -1):04X}' if n in labs else f'{n:28s} —')
    else:
        for n, a in sorted(labs.items(), key=lambda x: x[1]):
            print(f'{a:04X} {n}')
