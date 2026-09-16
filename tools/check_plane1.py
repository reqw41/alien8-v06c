#!/usr/bin/env python3
"""Гейт «буфер чист»: в плоскости 1 (0xA000..0xBFFF) код и данные лежат ТОЛЬКО вне картинки.

Плоскость 1 — столбцовый видеобуфер (адрес = 0xA000 + столбец*256 + 32 + Y). Строки 32..223
каждого столбца — сама картинка: туда пишет рендер и постолбцовая clear_scrn_buffer, и любой
байт кода там был бы затёрт на первом же кадре (а до того — нарисован на экране). Строки
224..255 столбца c и 0..31 столбца c+1 лежат в памяти подряд (64 Б) и не тронуты никем —
это и есть дыры, куда a8_pack_holes увозит процедуры нижнего региона.

  python3 tools/check_plane1.py build/alien8_vec.lst
  python3 tools/check_plane1.py build/alien8_vec.lst --walk build/alien8_vec.asm

--walk: сверка счёта длин (_i8080_len/_db_len/a8_walk из tools/a8_z80_to_8080.py) с адресами
листинга — тем самым счётом упаковщик решает, сколько байт съедает добивка ALIGN 256 перед
a8_optr. Требование: НОЛЬ расхождений на всех строках сборки.

Сторож записей (а не байтов образа) — tools/holescan_vec.js: он ловит случай, когда байты
в дыре лежат законно, но кто-то в них ПИШЕТ во время игры.
"""
import sys, re, os

RE_B = re.compile(r'^\s*\d+\+?\s+([0-9A-Fa-f]{4})\s((?:\s?[0-9A-Fa-f]{2}){1,4})\s')
RE_A = re.compile(r'^\s*(\d+)\s+([0-9A-Fa-f]{4})\s')
PLANE = 0xA000
LO, HI = 32, 223


def check_bytes(lst):
    bad, holes = [], 0
    for line in open(lst, encoding='latin-1'):
        m = RE_B.match(line)
        if not m:
            continue
        a = int(m.group(1), 16)
        for k in range(len(m.group(2).split())):
            b = a + k
            if not PLANE <= b < PLANE + 0x2000:
                continue
            if LO <= (b & 0xFF) <= HI:
                bad.append((b, line.rstrip()[:100]))
            else:
                holes += 1
    if bad:
        print("check_plane1: В КАРТИНКЕ БУФЕРА %d байт (столбец %d, строка %d и далее):"
              % (len(bad), (bad[0][0] >> 8) & 0x1F, bad[0][0] & 0xFF))
        for b, t in bad[:5]:
            print("   %04X  %s" % (b, t))
        return 1
    print("check_plane1: строки %d..%d плоскости 1 чисты; в дырах вне картинки %d байт из 2048"
          % (LO, HI, holes))
    return 0


def check_walk(lst, asm):
    """Счёт длин по исходнику против адресов листинга: 0 расхождений на всех строках."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import a8_z80_to_8080 as t
    lines = open(asm, encoding='utf-8').read().split('\n')
    at = t.a8_walk(lines, len(lines) - 1)
    if at is None:
        print("check_plane1 --walk: счёт адресов сбился (неизвестная инструкция)")
        return 1
    ref = {}
    for line in open(lst, encoding='latin-1'):
        m = RE_A.match(line)
        if m:
            ref.setdefault(int(m.group(1)), int(m.group(2), 16))
    diff, seen = [], 0
    for n, a in sorted(ref.items()):
        i = n - 1
        if i >= len(at) or at[i] is None:
            continue
        seen += 1
        if at[i] != a:
            diff.append((n, at[i], a, lines[i].rstrip()[:70]))
    if diff:
        print("check_plane1 --walk: РАСХОЖДЕНИЙ %d из %d строк:" % (len(diff), seen))
        for n, mine, real, txt in diff[:10]:
            print("   строка %-6d счёт %04X, листинг %04X  %s" % (n, mine, real, txt))
        return 1
    print("check_plane1 --walk: %d строк сборки, расхождений счёта с листингом 0" % seen)
    return 0


def main():
    lst = sys.argv[1] if len(sys.argv) > 1 else 'build/alien8_vec.lst'
    rc = check_bytes(lst)
    if '--walk' in sys.argv:
        rc |= check_walk(lst, sys.argv[sys.argv.index('--walk') + 1])
    sys.exit(rc)


if __name__ == '__main__':
    main()
