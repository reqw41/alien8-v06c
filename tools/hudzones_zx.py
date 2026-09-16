#!/usr/bin/env python3
"""ЗАМЕР: какие знакоместа панели ZX ярко-белые (0x47) — и что это в раскладке Вектора.

Судья геометрии белого HUD — не глаз и не исходник, а АТРИБУТНАЯ ПАМЯТЬ ОРИГИНАЛА.
`zx-stand/zx_screen.lua` пишет на каждой итерации 6144 байта пикселей и 768 байт атрибутов;
здесь читается последняя итерация одного или нескольких дампов, и по ним строится таблица
`vec_hudcols`.

ПОЧЕМУ ДОКАЗАТЕЛЬСТВО ТОЧНОЕ. Атрибут ZX красит знакоместо 8x8 целиком, поэтому зона,
выровненная по знакоместу, не может покрасить ни одной лишней точки: что бы в неё ни
нарисовали, на ZX оно тоже белое. Зоны здесь выровнены по знакоместам ПО ПОСТРОЕНИЮ —
значит окрас Вектора совпадает с оригиналом точка в точку, и «обходить рамку
прямоугольниками» (как пришлось в Knight Lore) не нужно.

Пересчёт: буфер Вектора столбцовый, адрес = база + столбец*256 + (223 - строка ZX).
Строка атрибутов R занимает строки ZX 8R..8R+7, то есть смещения 216-8R .. 223-8R.
Все четыре зоны ложатся в 0x20..0x3F — ровно в полосу, которую держит пустой check_plane2.

  python3 tools/hudzones_zx.py                       # дампы по умолчанию (4 комнаты)
  python3 tools/hudzones_zx.py <дамп.bin> ...        # свои дампы
  A8HZ_ROWS=16,23 python3 tools/hudzones_zx.py       # печатать другие строки атрибутов

Код возврата 1, если белые знакоместа в дампах РАЗНЫЕ (геометрия зависела бы от комнаты).
"""
import os
import sys

STAND = os.path.expanduser('~/projects/alien8-research/zx-stand')
DEFAULT = ['zx_screen_idle.bin', 'zx_screen_r39.bin', 'zx_screen_r137.bin', 'zx_screen_r104.bin']
REC, PIX = 6912, 6144
WHITE = 0x47                    # яркий белый на чёрном: ровно им оригинал красит элементы HUD
R0, R1 = (int(x) for x in os.environ.get('A8HZ_ROWS', '18,23').split(','))


def attrs(path):
    """Атрибуты последней итерации дампа (768 байт)."""
    data = open(path, 'rb').read()
    n = len(data) // REC
    assert n, path
    return data[(n - 1) * REC + PIX:n * REC]


def zones(white):
    """Белые знакоместа -> записи vec_hudcols (страница, столбцов, строка, строк).

    Склейка по столбцам в пределах строки атрибутов, затем склейка соседних строк атрибутов
    с тем же диапазоном столбцов (строка R+1 лежит ВЫШЕ R по смещению, поэтому объединяются
    записи с соседними смещениями)."""
    runs = []                                            # (первое смещение, строк, столбец, столбцов)
    for r in sorted({r for r, _ in white}):
        cols = sorted(c for rr, c in white if rr == r)
        i = 0
        while i < len(cols):
            j = i
            while j + 1 < len(cols) and cols[j + 1] == cols[j] + 1:
                j += 1
            runs.append([216 - 8 * r, 8, cols[i], cols[j] - cols[i] + 1])
            i = j + 1
    runs.sort(key=lambda z: (z[2], z[3], z[0]))
    out = []
    for z in runs:
        p = next((q for q in out if q[2] == z[2] and q[3] == z[3] and q[0] + q[1] == z[0]), None)
        if p:
            p[1] += z[1]
        else:
            out.append(z)
    return sorted(out, key=lambda z: (z[2], z[0]))


def main(argv):
    paths = argv or [os.path.join(STAND, f) for f in DEFAULT]
    paths = [p for p in paths if os.path.exists(p)]
    assert paths, 'дампов не нашлось: сними zx_screen.lua (LOCKSTEP.md §10)'
    sets, bad = [], 0
    for p in paths:
        a = attrs(p)
        print('== %s' % os.path.basename(p))
        print('     ' + ' '.join('%2d' % c for c in range(32)))
        for r in range(R0, R1 + 1):
            print('%3d: ' % r + ' '.join('%02X' % a[r * 32 + c] for c in range(32)))
        sets.append({(r, c) for r in range(24) for c in range(32) if a[r * 32 + c] == WHITE})
    if any(s != sets[0] for s in sets[1:]):
        print('РАСХОЖДЕНИЕ: белые знакоместа зависят от дампа', file=sys.stderr)
        bad = 1
    print('\nбелые знакоместа (0x%02X), одинаковы во всех %d дампах: %s'
          % (WHITE, len(paths), ', '.join('R%d C%d' % rc for rc in sorted(sets[0]))))
    print('\nvec_hudcols (страница = 0xC0 + столбец, столбцов, первая строка, строк):')
    for off, n, c, w in zones(sets[0]):
        assert 0x20 <= off and off + n - 1 <= 0x3F, (off, n)
        print('\t\t\t\t\tDB\t\t0x%02X, %d, %d, %d, 0xFF\t; столбцы %d..%d, строки %d..%d'
              % (0xC0 + c, w, off, n, c, c + w - 1, off, off + n - 1))
    return bad


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
