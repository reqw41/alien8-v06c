#!/usr/bin/env python3
"""Номера ВСЕХ комнат игры — из таблицы `location_tbl` собранной ZX-версии.

Зачем отдельный инструмент. «Комната N» в стендах (`A8ROOM`, `ZXSCR_ROOM`) — это байт,
который `init_start_location` кладёт в поле +8 записей объектов 0 и 1, а `retrieve_screen`
потом ИЩЕТ в таблице `location_tbl`:

    find_screen:  ld a,(hl) : inc hl : cp (ix+8) : jr z,found_screen
                  ld a,(hl) : call add_HL_A         ; HL += длина записи
                  and a : sbc hl,bc : jr nc,zero_end_of_graphic_objs_tbl   ; таблица кончилась
                  jr find_screen

Запись: [номер][длина][данные], следующая запись = адрес длины + длина. Номера НЕ идут
подряд 0..127: их 128 штук, но разбросаны от 2 до 248 (номер кодирует положение комнаты
в 3D-сетке). Отсюда и запись в журнале «из 26 проверенных комнат 9 не грузятся вовсе»:
проверялись номера 0..25 подряд, а половины из них в таблице просто нет — игра уходит
в `zero_end_of_graphic_objs_tbl` и строит ПУСТУЮ комнату. Такой номер не дефект порта,
а несуществующая комната.

  python3 tools/a8_rooms.py            # по одному номеру в строке
  python3 tools/a8_rooms.py --len      # «номер длина_записи»

Нужна сборка ZX (`./build.sh zx`): читаются build/alien8_zx.bin и build/alien8_zx.sld.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, 'build', 'alien8_zx.bin')
SLD = os.path.join(ROOT, 'build', 'alien8_zx.sld')
BASE = 0x4000            # build/alien8_zx.bin — образ ОЗУ 48К, начинается с 0x4000


def labels():
    out = {}
    for line in open(SLD, encoding='utf-8', errors='replace'):
        f = line.rstrip('\n').split('|')
        if len(f) >= 8 and f[6] == 'F':
            out[f[7]] = int(f[5])
    return out


def rooms():
    if not (os.path.exists(BIN) and os.path.exists(SLD)):
        sys.exit('нет build/alien8_zx.bin или .sld — сначала ./build.sh zx')
    d = open(BIN, 'rb').read()
    L = labels()
    p, end = L['location_tbl'], L['block_type_tbl']
    out = []
    while True:
        rid, ln = d[p - BASE], d[p + 1 - BASE]
        assert ln, 'нулевая длина записи по адресу %#06x' % p
        out.append((rid, ln))
        p += 1 + ln
        if p >= end:
            break
    return out


if __name__ == '__main__':
    wl = '--len' in sys.argv[1:]
    r = rooms()
    assert len(set(i for i, _ in r)) == len(r), 'номера комнат повторяются'
    for rid, ln in r:
        print('%d %d' % (rid, ln) if wl else rid)
