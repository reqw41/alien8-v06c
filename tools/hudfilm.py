#!/usr/bin/env python3
"""ГЕЙТ ПЕРЕХОДОВ: маска белого HUD — по КАЖДОМУ КАДРУ плёнки, а не по одному снимку.

  node tools/hudshot_vec.js ... A8HS_FILM=build/film/f A8HS_FILMFR=a,b[,шаг]
  python3 tools/hudfilm.py build/film            # каталог с f_*.txt

ЗАЧЕМ ОТДЕЛЬНЫЙ ГЕЙТ. `hudcolor.py` судит ОДИН кадр, и кадр «после» ничего не говорит о том,
что было в середине перехода. Владелец увидел на MiSTer белые куски на рамке экрана
«RE-PROGRAMMING» (сборка робота после GAME OVER) — а снимок GAME OVER, снятый одним кадром
позже гашения, был зелёным. Дефект живёт РОВНО в переходе, и ловится только плёнкой.

ЧТО ПРОВЕРЯЕТСЯ НА КАЖДОМ КАДРЕ

1. ЭКРАН БЕЗ ПАНЕЛИ -> МАСКА ПУСТА. Экран без панели опознаётся ДВУМЯ способами, и ни один
   из них не «на глаз»:
   * ТОЧНО, по флагу самого порта: `byte_5B24 != 0` — это экран «RE-PROGRAMMING». Игровой
     цикл при нём уходит на loc_A741 в обход sub_AD66, display_panel и colour_something
     (`ld a,(byte_5B24) / and a / jp nz, loc_A741` в onscreen_loop), то есть панели на экране
     нет, а на ZX атрибуты остались от clr_attr — экран ОДНОГО цвета;
   * по ПОЛНОЭКРАННОЙ РАМКЕ (меню, GAME OVER, финал — они вне игрового цикла, и флага у них
     нет): столбцы 0..1 заполнены более чем на 3/4 высоты картинки. ЗАМЕР разделения:
     рамка 152 строки из 192, игровые комнаты 58 и 83 (стартовая и 137) — порог 144 лежит
     между ними с запасом; сторож `--sep` печатает статистику по всей плёнке.

2. ПОКРЫТИЕ. Хотя бы один кадр каждого класса обязан быть увиден, иначе гейт падает: плёнка,
   не доехавшая до экрана без панели, «зелёная» ни о чём не говорит (ровно так прошёл мимо
   дефекта одиночный снимок GAME OVER).

3. НА ЭКРАНЕ С ПАНЕЛЬЮ — проверки hudcolor.py, но БЕЗ «зона заполнена целиком» (`--nofill`):
   в переходе картинка нарисована наполовину (идёт vec_wipe0 или update_screen), и маска
   ложится между стиранием и показом — требовать полноту зоны на таком кадре нельзя. Полноту
   зоны судит одиночный hudcolor на устоявшемся экране.

Код возврата 1 при любом нарушении и при непокрытом классе.
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hudcolor

COL_FULL = 144                  # порог «полноэкранная рамка» по столбцам 0..1 (замер в шапке)
PIC = hudcolor.PIC


def framed(p0):
    """Столбцы 0..1 заполнены почти на всю высоту картинки — полноэкранная рамка."""
    return sum(1 for r in range(PIC[0], PIC[1] + 1) if p0[r][0] == '#' or p0[r][1] == '#')


def main(argv):
    show = '--sep' in argv
    d = [a for a in argv if not a.startswith('-')]
    d = d[0] if d else 'build/film'
    files = sorted(glob.glob(os.path.join(d, '*.txt')))
    assert files, 'плёнки нет в %s (сними hudshot_vec.js A8HS_FILM=...)' % d
    bad, n_nopanel, n_panel, n_reprog, sep = 0, 0, 0, 0, []
    for f in files:
        pl, _, st = hudcolor.load(f)
        p0, p2 = pl[0], pl[2]
        npix = sum(s.count('#') for s in p0.values())
        col = framed(p0)
        sep.append((os.path.basename(f), npix, col, st.get('b5B24', 0)))
        reprog = st.get('b5B24', 0) != 0
        nopanel = reprog or (npix and col >= COL_FULL)
        if npix == 0:                       # чёрный экран — судить нечего
            continue
        if nopanel:
            n_nopanel += 1
            n_reprog += reprog
            white = [(x, r) for r, s in p2.items() if PIC[0] <= r <= PIC[1]
                     for x, ch in enumerate(s) if ch == '#' and p0[r][x] == '#']
            any2 = sum(s.count('#') for r, s in p2.items() if PIC[0] <= r <= PIC[1])
            if any2:
                bad += 1
                print('!!! %s: ЭКРАН БЕЗ ПАНЕЛИ (%s), а маска стоит: %d точек плоскости 2, '
                      'из них %d покрасили картинку'
                      % (os.path.basename(f),
                         'byte_5B24=%d' % st.get('b5B24', 0) if reprog else 'рамка %d/192' % col,
                         any2, len(white)))
        else:
            n_panel += 1
            rc = hudcolor.main([f, '--nofill', '--quiet'])
            if rc:
                bad += 1
                print('    (кадр %s)' % os.path.basename(f))
    if show:
        for nm, npix, col, b in sep:
            print('    %-16s p0 %5d  столбцы 0..1 %3d/192  byte_5B24 %d' % (nm, npix, col, b))
    if not n_nopanel:
        bad += 1
        print('!!! ПОКРЫТИЕ: ни одного кадра БЕЗ панели — плёнка не доехала до перехода')
    if not n_reprog:
        bad += 1
        print('!!! ПОКРЫТИЕ: ни одного кадра RE-PROGRAMMING (byte_5B24 != 0)')
    if not n_panel:
        bad += 1
        print('!!! ПОКРЫТИЕ: ни одного кадра С панелью')
    print('плёнка %s: кадров %d, с панелью %d, без панели %d (из них RE-PROGRAMMING %d), '
          'нарушений %d' % (d, len(files), n_panel, n_nopanel, n_reprog, bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
