#!/usr/bin/env python3
"""Гейт «картинка плоскости 2 чиста»: код и данные — только в дырах вне картинки.

Плоскость 2 (0xC000..0xDFFF) отдана под селектор БЕЛОГО HUD: она даёт БИТ ИНДЕКСА ПАЛИТРЫ
(индекс = p0<<3|p1<<2|p2<<1|p3). Буфер Вектора столбцовый — адрес = база + столбец*256 +
(223 - строка ZX), — поэтому картинка это смещения 0x20..0xDF КАЖДОЙ из 32 страниц, а не
один кусок. Любой единичный бит внутри картинки поднимает p2 у восьми точек, и там, где
есть точка поля (p0=1), вместо цвета комнаты выйдет перо HUD: белая клякса поперёк поля.
Ассемблер такое пропускает молча — судит только этот гейт, по ЛИСТИНГУ.

  0x00..0x1F и 0xE0..0xFF — ДЫРЫ вне картинки: здесь код и данные разрешены (2048 Б);
  0x20..0x3F              — полоса панели: только маска vec_hudcols (нули или 0xFF);
  0x40..0xDF              — поле: всегда нули.

Полосу панели маска заполняет В РАНТАЙМЕ (vec_hud_mask), в образе там ноль — поэтому гейт
судит одинаково всю картинку 0x20..0xDF: ни байта кода и данных.

  python3 tools/check_plane2.py build/alien8_vec.lst
  python3 tools/check_plane2.py build/alien8_vec.lst --walk build/alien8_vec.asm

--walk обязателен в сборке: он считает не ВЫДАННЫЕ байты, а ЗАНЯТЫЕ адреса (a8_walk), и
только так видно `метка: DS n` — ячейка резервирует место, но в листинге байтов не выдаёт,
а маска и рендер затрут её так же, как код. Заодно сверяется счёт длин (_i8080_len/_db_len)
с адресами листинга: тем же счётом раскладчик a8_layout_upper решает, куда лягут блоки.
"""
import sys, re, os

RE_B = re.compile(r'^\s*\d+\+?\s+([0-9A-Fa-f]{4})\s((?:\s?[0-9A-Fa-f]{2}){1,4})\s')
RE_A = re.compile(r'^\s*(\d+)\s+([0-9A-Fa-f]{4})\s')
PLANE = (0xC000, 0xE000)        # плоскость 2 целиком
PIC_LO, PIC_HI = 0x20, 0xDF     # картинка в каждой странице (панель — её часть, 0x20..0x3F)


def in_pic(a):
    return PLANE[0] <= a < PLANE[1] and PIC_LO <= (a & 0xFF) <= PIC_HI


def report(bad, tag):
    if not bad:
        return 0
    print("check_plane2%s: КАРТИНКУ ПЛОСКОСТИ 2 ЗАНИМАЮТ %d байт (первый %04X, страница 0x%02X, "
          "смещение 0x%02X):" % (tag, len(bad), bad[0][0], bad[0][0] >> 8, bad[0][0] & 0xFF))
    for b, t in bad[:5]:
        print("   %04X  %s" % (b, t))
    return 1


def check_bytes(lst):
    bad = []
    for line in open(lst, encoding='latin-1'):
        m = RE_B.match(line)
        if not m:
            continue
        a = int(m.group(1), 16)
        for k in range(len(m.group(2).split())):
            if in_pic(a + k):
                bad.append((a + k, line.rstrip()[:100]))
    return report(bad, "")


def check_walk(lst, asm):
    """Занятые АДРЕСА (а не выданные байты) против картинки + сверка счёта длин с листингом."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import a8_z80_to_8080 as t
    lines = open(asm, encoding='utf-8').read().split('\n')
    at = t.a8_walk(lines, len(lines) - 1)
    if at is None:
        print("check_plane2 --walk: счёт адресов сбился (неизвестная инструкция)")
        return 1
    bad, occupied = [], 0
    for i, a in enumerate(at):
        if a is None or i + 1 >= len(at) or at[i + 1] is None or at[i + 1] <= a:
            continue
        m = t._H_ANYLBL.match(lines[i])
        code = ' '.join(t._nocom(lines[i][m.end():] if m else lines[i]).split())
        if re.match(r'(?i)^(ALIGN|ORG)\b', code):   # добивка и переезд — не код и не данные
            continue
        for b in range(a, at[i + 1]):
            if in_pic(b):
                bad.append((b, lines[i].strip()[:70]))
            elif PLANE[0] <= b < PLANE[1]:
                occupied += 1
    rc = report(bad, " --walk")
    # сверка счёта длин с адресами листинга — им же считает раскладчик
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
        rc = 1
        print("check_plane2 --walk: РАСХОЖДЕНИЙ СЧЁТА %d из %d строк:" % (len(diff), seen))
        for n, mine, real, txt in diff[:10]:
            print("   строка %-6d счёт %04X, листинг %04X  %s" % (n, mine, real, txt))
    if not rc:
        print("check_plane2 --walk: в дырах вне картинки %d байт из 2048; %d строк сборки, "
              "расхождений счёта 0" % (occupied, seen))
    return rc


def main():
    lst = sys.argv[1] if len(sys.argv) > 1 else 'build/alien8_vec.lst'
    rc = check_bytes(lst)
    if '--walk' in sys.argv:
        rc |= check_walk(lst, sys.argv[sys.argv.index('--walk') + 1])
    if not rc:
        print("check_plane2: картинка плоскости 2 (смещения 0x%02X..0x%02X всех 32 страниц) чиста "
              "— %d байт, из них %d под панель" % (PIC_LO, PIC_HI, 32 * (PIC_HI - PIC_LO + 1),
                                                   32 * 0x20))
    sys.exit(rc)


if __name__ == '__main__':
    main()
