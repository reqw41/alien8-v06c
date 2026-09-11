# -*- coding: utf-8 -*-
"""Нативные i8080-процедуры Alien 8 (логика) и укорочение циклов по таблице объектов.

Метод — §5–7 и §13 рецепта Knight Lore: спецификация (spec/a8_spec.py) -> дамп реальных
вызовов (tools/calldump_vec.js) -> прогон спецификации по дампу -> ассемблер -> гейты.
Гейты: локстеп против журнала ZX (600 итераций × 3 сценария, 1928 байт переменных байт в байт),
tools/render_gate.sh (картинка), tools/nobjcheck_vec.js (инвариант границы таблицы).

Два вида правок:
  presub(src)  — на тексте Z80 ДО трансляции (обе цели): граница занятых записей таблицы;
  apply(src)   — замена тел процедур готовым i8080 ПОСЛЕ трансляции (обе цели).
"""
import re

# Дополнение к scratch-области 0x0040..0x00A0 обеих целей.
SCRATCH = """a8_nobj:		DB		56			; занятых записей graphic_objs_tbl (ставит zero_end_of_graphic_objs_tbl)
a8_objend:		DW		0			; graphic_objs_tbl + a8_nobj*32 — конец занятой части
"""


def _sub(src, pat, repl, name, count=1, flags=re.M):
    src, n = re.subn(pat, lambda m: repl, src, count=count, flags=flags)
    assert n == count, "a8_native_logic: не найдено (%s): %d вместо %d" % (name, n, count)
    return src


# ---------------------------------------------------------------------------
# Граница «занято / пусто» таблицы объектов.
#
# Загрузчик комнаты (`retrieve_screen`) кладёт объекты ПОДРЯД, начиная с `other_objs_here`
# (слот 4; слоты 0..3 — две половины игрока и два спецобъекта), и в
# `zero_end_of_graphic_objs_tbl` обнуляет ВЕСЬ хвост от DE до font. Значит DE в этой точке —
# граница занятых записей, и она же верхняя граница всех живых объектов до следующей
# загрузки комнаты. Инвариант «последний живой слот < a8_nobj» проверяется гейтом
# tools/nobjcheck_vec.js: и на границе каждой итерации, и на КАЖДОЙ записи graphic_no != 0.
#
# `clr_graphic_objs_tbl` (GAME OVER) чистит всю таблицу, границу не двигая: завышенная
# граница безопасна (циклы просто проходят лишние пустые записи).
# ---------------------------------------------------------------------------
_NOBJ_HEAD = """zero_end_of_graphic_objs_tbl:
        push de   ; A8: DE = первый свободный слот -> граница занятых записей (a8_nobj/a8_objend)
        ld (a8_objend), de
        push hl
        ld hl, -graphic_objs_tbl
        add hl, de   ; HL = смещение в таблице, кратно 32, < 1792
        ld a, l
        rlca
        rlca
        rlca
        and 7   ; L/32
        ld l, a
        ld a, h
        add a, a
        add a, a
        add a, a   ; H*8
        or l
        ld (a8_nobj), a
        pop hl
        pop de
loc_zeg_lp:
"""


def scratch(src):
    """Подставить дополнение scratch-области (плейсхолдер в заголовках обеих целей)."""
    return _sub(src, r'^__A8_NATIVE_SCRATCH__', SCRATCH.rstrip('\n'), 'место под scratch')


def presub(src):
    """Правки на тексте Z80 ДО трансляции. Вызывать ПОСЛЕ подстановок font -> a8_vars_end."""
    # 1) считать границу при загрузке комнаты
    src = _sub(src, r'^zero_end_of_graphic_objs_tbl:\n', _NOBJ_HEAD, 'голова zero_end')
    src = _sub(src, r'^        jr zero_end_of_graphic_objs_tbl\n',
               "        jr loc_zeg_lp   ; A8: границу считать один раз, на входе\n", 'хвост zero_end')
    # 2) три цикла по объектам ходят до границы, а не по всем 56 записям
    src = _sub(src, r'^        ld b, 56   ; max objects\n',
               "        ld a, (a8_nobj)   ; A8: только занятые записи (было 56)\n        ld b, a\n",
               'счётчики циклов по объектам', count=2)
    src = _sub(src, r'^        ld bc, a8_vars_end   ; end of table\?\n',
               "        ld bc, (a8_objend)   ; A8: конец ЗАНЯТОЙ части таблицы (было: конец таблицы)\n",
               'конец таблицы в ret_from_tbl_jp')
    return src


def apply(src):
    """Замена тел процедур готовым i8080 ПОСЛЕ трансляции."""
    return scratch(src)
