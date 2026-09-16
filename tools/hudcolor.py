#!/usr/bin/env python3
"""ГЕЙТ БЕЛОГО HUD по дампу плоскостей (tools/hudshot_vec.js A8HS_DUMP=...).

  python3 tools/hudcolor.py build/hud_room19.txt            # экран С панелью
  python3 tools/hudcolor.py --nomask build/hud_menu.txt     # экран БЕЗ панели: маска погашена
  python3 tools/hudcolor.py --nofill --quiet <кадр>         # кадр ПЕРЕХОДА (см. tools/hudfilm.py):
        # там картинка нарисована наполовину (идёт vec_wipe0 или update_screen), и требовать
        # «зона заполнена» нельзя — маска ложится между стиранием и показом

Три проверки, и каждая ловит свой класс дефектов:

1. КАЖДОЕ ЗНАКОМЕСТО ОДНОГО ЦВЕТА ПО ПЕРУ HUD. Цвет точки картинки — байт палитры по индексу
   p0<<3|p2<<1: p3 записан парами, а p1 СОЗНАТЕЛЬНО НЕ УЧИТЫВАЕТСЯ — через него идёт синяя
   полоса подсветки меню (индексы 8..11 синие, 12..15 белые), и там разноцветное знакоместо
   ЗАКОННО (замер: 9 знакомест в строках 160..167 меню — буквы поверх полосы). Этот гейт
   судит селектор белого HUD, то есть плоскость 2. Клетка 8x8, выровненная по СЕТКЕ АТРИБУТОВ ZX
   (строки памяти 32..223 кратны 8 от 32), где встретилось больше одного цвета — дефект:
   на ZX атрибут красит знакоместо ЦЕЛИКОМ, значит и на Векторе клетка обязана быть
   одноцветной. Сдвиг зоны на несколько строк режет цифру на два цвета и ловится здесь.
   ПОЧЕМУ НЕ «КАЖДЫЙ ЭЛЕМЕНТ», КАК В KNIGHT LORE: в Alien 8 арка счётчика (на ZX 0x42,
   ярко-красная) КАСАЕТСЯ цифр счётчика (0x47, белые) — замер: одна связная компонента
   x 205..242, строки 45..58, 214 точек. В оригинале она тоже двуцветная, то есть
   «компонента одного цвета» — не свойство этой игры, а знакоместо — свойство.

2. ВНЕ ЗОН ПЛОСКОСТЬ 2 = 0 (внутри картинки, строки памяти 32..223). Единичный бит мимо зон
   белит точки поля, и проверка 1 его НЕ ПОЙМАЕТ, если он покрасил связную компоненту целиком.
   Зоны читаются из таблицы `vec_hudcols` в tools/a8_vec.py — гейт и код не могут разойтись.

3. ЗОНЫ ЗАПОЛНЕНЫ ЦЕЛИКОМ (или пусты целиком при --nomask; `--nofill` снимает эту проверку).
   vec_hud_mask кладёт зону
   прямоугольником, vec_hud_off гасит; половина зоны — это оборванный обход таблицы.
   --nomask — для экранов без панели (меню, GAME OVER, финал, RE-PROGRAMMING): там маска
   ОБЯЗАНА быть погашена, иначе рамка и текст красятся пером HUD.

Код возврата 1 при любом нарушении.
"""
import collections
import os
import re
import sys

A8VEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'a8_vec.py')
PIC = (32, 223)                 # строки памяти внутри картинки


def zones(path=A8VEC):
    """Таблица vec_hudcols из tools/a8_vec.py -> [(столбец, столбцов, строка, строк)]."""
    src = open(path, encoding='utf-8').read()
    i = src.index('vec_hudcols:')
    out = []
    for line in src[i:].split('\n'):
        m = re.search(r'DB\s+0x([0-9A-Fa-f]{2}),\s*(\d+),\s*(\d+),\s*(\d+)', line)
        if m:
            out.append((int(m.group(1), 16) - 0xC0, int(m.group(2)), int(m.group(3)), int(m.group(4))))
        elif re.search(r'DB\s+0\s*$', line.split(';')[0]):
            break
    assert out, 'в %s не нашлась таблица vec_hudcols' % path
    return out


def load(path):
    """-> (плоскости, палитра, флаги порта). Строки `state` может не быть (одиночный снимок)."""
    pl, pal, st = {0: {}, 1: {}, 2: {}, 3: {}}, None, {}
    for l in open(path):
        q = l.rstrip('\n').split()
        if not q:
            continue
        if q[0] == 'state':
            st = {q[i]: int(q[i + 1]) for i in range(1, len(q) - 1, 2)}
            continue
        if q[0] == 'pal':
            pal = [int(t, 16) for t in q[1:]]
            continue
        pl[int(q[1][1])][int(q[0])] = q[2]
    assert pal, 'в дампе нет строки pal (нужен свежий hudshot_vec.js)'
    return pl, pal, st


def main(argv):
    nomask, nofill, quiet = '--nomask' in argv, '--nofill' in argv, '--quiet' in argv
    path = [a for a in argv if not a.startswith('-')][0]
    pl, pal, _ = load(path)
    p0, p1, p2 = pl[0], pl[1], pl[2]
    zs = zones()
    bad = 0

    # ---- 1. каждое знакоместо одного цвета ----
    col = lambda x, r: pal[8 | (2 if p2[r][x] == '#' else 0)]
    cells = collections.defaultdict(collections.Counter)
    npix = 0
    for r, s in p0.items():
        if not PIC[0] <= r <= PIC[1]:
            continue
        for x, c in enumerate(s):
            if c == '#':
                npix += 1
                cells[(x // 8, r // 8)]['цвет %02X' % col(x, r)] += 1
    mixed = 0
    for (cx, cr), cnt in sorted(cells.items()):
        if len(cnt) > 1:
            mixed += 1
            print('!!! РАЗНОЦВЕТНОЕ ЗНАКОМЕСТО столбец %2d строки %3d..%3d: %s'
                  % (cx, cr * 8, cr * 8 + 7, ', '.join('%s %d' % kv for kv in cnt.most_common())))
    bad += mixed

    # ---- 2. вне зон плоскость 2 чиста, 3. зоны заполнены целиком ----
    inzone = {(x, r) for c, w, r0, h in zs for r in range(r0, r0 + h)
              for x in range(c * 8, (c + w) * 8)}
    stray = sorted((x, r) for r, s in p2.items() if PIC[0] <= r <= PIC[1]
                   for x, ch in enumerate(s) if ch == '#' and (x, r) not in inzone)
    if stray:
        bad += 1
        print('!!! ПЛОСКОСТЬ 2 ВНЕ ЗОН: %d точек, первая x=%d строка=%d (столбец %d)'
              % (len(stray), stray[0][0], stray[0][1], stray[0][0] // 8))
    want = '.' if nomask else '#'
    for c, w, r0, h in zs if not nofill else ():
        wrong = [(x, r) for r in range(r0, r0 + h) for x in range(c * 8, (c + w) * 8)
                 if p2.get(r, '.' * 256)[x] != want]
        if wrong:
            bad += 1
            print('!!! ЗОНА столбцы %d..%d строки %d..%d: %d точек не %s (первая x=%d строка=%d)'
                  % (c, c + w - 1, r0, r0 + h - 1, len(wrong),
                     'погашено' if nomask else 'закрашено', wrong[0][0], wrong[0][1]))
    n2 = sum(s[x] == '#' for r, s in p2.items() if PIC[0] <= r <= PIC[1] for x in range(256))
    if not (quiet and not bad):
        print('%s: точек картинки %d в %d знакоместах, разноцветных %d; точек плоскости 2 в '
              'картинке %d, зон %d (%s)'
              % (os.path.basename(path), npix, len(cells), mixed, n2, len(zs),
                 'маска погашена' if nomask else 'маска на месте'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
