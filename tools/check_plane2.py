#!/usr/bin/env python3
"""Гейт «полоса HUD чиста»: в плоскости 2 нет кода и данных там, где будет панель.

Плоскость 2 (0xC000..0xDFFF) отдана под селектор БЕЛОГО HUD, как в Knight Lore. Панель
Alien 8 занимает нижние 32 строки картинки — ZX-строки 160..191, — а буфер Вектора
столбцовый: адрес = база + столбец*256 + 32 + Y, Y = 223 - строка ZX. Значит панель лежит
не одним куском, а полосой 0x20..0x3F в КАЖДОЙ из 32 страниц плоскости. Любой байт кода
или данных в этих полосах будет затёрт панелью на первом же кадре (а до того нарисован
на экране), и ассемблер такое пропускает молча — судит только этот гейт, по ЛИСТИНГУ.

  python3 tools/check_plane2.py build/alien8_vec.lst
  python3 tools/check_plane2.py build/alien8_vec.lst --walk build/alien8_vec.asm

--walk обязателен в сборке: он считает не ВЫДАННЫЕ байты, а ЗАНЯТЫЕ адреса (a8_walk), и
только так видно `метка: DS n` — ячейка резервирует место, но в листинге байтов не выдаёт,
а панель затрёт её так же, как код. Заодно сверяется счёт длин (_i8080_len/_db_len) с
адресами листинга: тем же счётом раскладчик a8_layout_upper решает, куда лягут блоки.

ДО ПЕРЕЕЗДА ПЕРЕМЕННЫХ (ветка varmove) переменные игры лежат в 0xC800..0xCF87, то есть
поперёк восьми полос. Их диапазон исключается ПО МЕТКАМ seed_1..a8_vars_end и печатается
отдельной строкой; после переезда исключение опустеет само, и тогда весь 0xC800..0xCFFF
обязан быть пуст (это проверяется и сейчас — для всего, что не переменные).
"""
import sys, re, os

RE_B = re.compile(r'^\s*\d+\+?\s+([0-9A-Fa-f]{4})\s((?:\s?[0-9A-Fa-f]{2}){1,4})\s')
RE_A = re.compile(r'^\s*(\d+)\s+([0-9A-Fa-f]{4})\s')
RE_L = re.compile(r'^\s*\d+\s+([0-9A-Fa-f]{4})\s+([A-Za-z_]\w*):')
PLANE = (0xC000, 0xE000)        # плоскость 2 целиком
HUD_LO, HUD_HI = 0x20, 0x3F     # полоса панели в каждой странице
VARS = (0xC800, 0xD000)         # страницы, которые освободит переезд переменных


def in_hud(a):
    return PLANE[0] <= a < PLANE[1] and HUD_LO <= (a & 0xFF) <= HUD_HI


def vars_span(lst):
    """Диапазон переменных игры по меткам seed_1..a8_vars_end (до varmove)."""
    lab = {}
    for line in open(lst, encoding='latin-1'):
        m = RE_L.match(line)
        if m and m.group(2) in ('seed_1', 'a8_vars_end'):
            lab[m.group(2)] = int(m.group(1), 16)
    if 'seed_1' in lab and 'a8_vars_end' in lab:
        return lab['seed_1'], lab['a8_vars_end']
    return None


def check_bytes(lst, vs):
    hud, dead, invars = [], [], False
    for line in open(lst, encoding='latin-1'):
        ml = RE_L.match(line)
        if ml and ml.group(2) in ('seed_1', 'a8_vars_end'):
            invars = ml.group(2) == 'seed_1'   # ИСКЛЮЧЕНИЕ ПО ТЕКСТУ, а не по адресам: чужой
        if invars:                             # блок, лёгший поверх переменных, обязан краснеть
            continue
        m = RE_B.match(line)
        if not m:
            continue
        a = int(m.group(1), 16)
        for k in range(len(m.group(2).split())):
            b = a + k
            if in_hud(b):
                hud.append((b, line.rstrip()[:100]))
            if VARS[0] <= b < VARS[1]:
                dead.append((b, line.rstrip()[:100]))
    rc = 0
    for name, bad in (("В ПОЛОСЕ HUD", hud), ("В 0xC800..0xCFFF (переезд переменных)", dead)):
        if not bad:
            continue
        rc = 1
        print("check_plane2: %s %d байт (страница 0x%02X, смещение 0x%02X и далее):"
              % (name, len(bad), bad[0][0] >> 8, bad[0][0] & 0xFF))
        for b, t in bad[:5]:
            print("   %04X  %s" % (b, t))
    return rc


def check_walk(lst, asm, vs):
    """Занятые АДРЕСА (а не выданные байты) против полос + сверка счёта длин с листингом."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import a8_z80_to_8080 as t
    lines = open(asm, encoding='utf-8').read().split('\n')
    at = t.a8_walk(lines, len(lines) - 1)
    if at is None:
        print("check_plane2 --walk: счёт адресов сбился (неизвестная инструкция)")
        return 1
    hud, dead, occupied, invars = [], [], 0, False
    for i, a in enumerate(at):
        ml = re.match(r'^(seed_1|a8_vars_end):', lines[i])
        if ml:                                  # ИСКЛЮЧЕНИЕ ПО ТЕКСТУ, а не по адресам:
            invars = ml.group(1) == 'seed_1'    # чужой блок поверх переменных обязан краснеть
        if invars or a is None or i + 1 >= len(at) or at[i + 1] is None or at[i + 1] <= a:
            continue
        m = t._H_ANYLBL.match(lines[i])
        code = ' '.join(t._nocom(lines[i][m.end():] if m else lines[i]).split())
        if re.match(r'(?i)^(ALIGN|ORG)\b', code):   # добивка и переезд — не код и не данные
            continue
        for b in range(a, at[i + 1]):
            if VARS[0] <= b < VARS[1]:
                dead.append((b, lines[i].strip()[:70]))
            if in_hud(b):
                hud.append((b, lines[i].strip()[:70]))
            elif PLANE[0] <= b < PLANE[1]:
                occupied += 1
    rc = 0
    for name, bad in (("ПОЛОСУ HUD ЗАНИМАЮТ", hud),
                      ("0xC800..0xCFFF (переезд переменных) ЗАНИМАЮТ", dead)):
        if not bad:
            continue
        rc = 1
        print("check_plane2 --walk: %s %d байт (первый %04X):" % (name, len(bad), bad[0][0]))
        for b, txt in bad[:5]:
            print("   %04X  %s" % (b, txt))
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
        print("check_plane2 --walk: занято вне полос %d байт плоскости 2; %d строк сборки, "
              "расхождений счёта 0" % (occupied, seen))
    return rc


def main():
    lst = sys.argv[1] if len(sys.argv) > 1 else 'build/alien8_vec.lst'
    vs = vars_span(lst)
    rc = check_bytes(lst, vs)
    if '--walk' in sys.argv:
        rc |= check_walk(lst, sys.argv[sys.argv.index('--walk') + 1], vs)
    if not rc:
        free = 32 * (HUD_HI - HUD_LO + 1)
        print("check_plane2: полосы 0x%02X..0x%02X всех 32 страниц плоскости 2 чисты (%d байт "
              "под панель)" % (HUD_LO, HUD_HI, free))
        if vs:
            print("check_plane2: переменные игры %04X..%04X исключены по меткам seed_1..a8_vars_end "
                  "— ДО varmove" % vs)
    sys.exit(rc)


if __name__ == '__main__':
    main()
