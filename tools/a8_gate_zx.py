#!/usr/bin/env python3
"""Гейт этапа 1: сборка дизассемблера обязана совпасть с оригиналом байт в байт.

    python3 tools/a8_gate_zx.py build/alien8_zx.bin build/alien8_orig_ram.bin

Сверяется область кода и данных $6288-$D1EA. Остальное сверять нельзя:
$4000-$5AFF — экран и атрибуты, $5B00-$6287 — переменные, $D200+ — видеобуфер
и таблицы, строящиеся при старте; в снимке там состояние работающей игры.
Код НЕ самомодифицируется ни в одном байте — если бы модифицировался,
расхождение вылезло бы именно здесь.
"""
import sys

BASE = 0x4000
LO, HI = 0x6288, 0xD1EA      # включительно


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    a = open(sys.argv[1], 'rb').read()
    b = open(sys.argv[2], 'rb').read()
    if len(a) != 49152 or len(b) != 49152:
        print(f'ОШИБКА: ожидались образы 49152 Б, получено {len(a)} и {len(b)}')
        return 1
    lo, hi = LO - BASE, HI - BASE + 1
    bad = [i for i in range(lo, hi) if a[i] != b[i]]
    n = hi - lo
    if not bad:
        print(f'ГЕЙТ ZX: OK — {n} байт ${LO:04X}-${HI:04X} совпали байт в байт')
        return 0
    print(f'ГЕЙТ ZX: ПРОВАЛ — расхождений {len(bad)} из {n}')
    grp = []
    s = p = bad[0]
    for i in bad[1:]:
        if i == p + 1:
            p = i
        else:
            grp.append((s, p))
            s = p = i
    grp.append((s, p))
    for s, p in grp[:40]:
        print(f'  {s + BASE:04X}-{p + BASE:04X} ({p - s + 1} Б) '
              f'сборка={a[s:p + 1][:12].hex()} снимок={b[s:p + 1][:12].hex()}')
    if len(grp) > 40:
        print(f'  ... всего групп {len(grp)}')
    return 1


if __name__ == '__main__':
    sys.exit(main())
