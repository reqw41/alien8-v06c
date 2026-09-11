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


_BODIES = [
    ('set_draw_objs_overlapped', 'N_SET_DRAW'),
]


def apply(src):
    """Замена тел процедур готовым i8080 ПОСЛЕ трансляции."""
    src = scratch(src)
    for name, var in _BODIES:
        src = _sub(src,
                   r'^%s:\n.*?^        ; End of function %s\n' % (name, name),
                   globals()[var], 'тело ' + name, flags=re.M | re.S)
    return src


# ---------------------------------------------------------------------------
# set_draw_objs_overlapped — 21.6 % тактов итерации (1.9 вызова, цикл по занятым записям).
#
# Что изменилось против транслированной версии:
#   * четыре параметра объединённого прямоугольника (левый край, ширина, нижний Y, высота)
#     пролог кладёт НЕПОСРЕДСТВЕННО в иммедиаты sub/cp внутри цикла — сравнение стоит один
#     байт и не занимает регистров; DE освобождён под постоянный шаг 32;
#   * объект адресуется указателем в HL: поле флагов как l+7 без adc (младший байт записи
#     = (база&31)+32k, а (graphic_objs_tbl & 31) = 8, значит +7 не переносит — см. ASSERT),
#     pixel X/Y и ширина/высота кандидата — сдвигами того же указателя;
#   * exx/ld de,32/add iy,de/exx на каждом проходе заменены на add hl,de.
# Регистр C не трогается (как в оригинале): в прологе его роль играют иммедиаты-заготовки.
# IY на выходе = конец занятой части таблицы, как у укороченного цикла.
# ---------------------------------------------------------------------------
N_SET_DRAW = """set_draw_objs_overlapped:
		ASSERT (graphic_objs_tbl & 31) <= 24	; иначе l+7 переносит и адресация поля флагов ломается
		ld hl, graphic_objs_tbl
		ld (z80_iy), hl			; оригинал ставит IY ДО calc_2d_info
		call calc_2d_info		; он же пересчитывает (ix+24)/(ix+25)
		; ---- ось X: левый край и ширина объединённого прямоугольника -> иммедиаты ----
		ld hl, (z80_ix)
		ld de, 24
		add hl, de
		ld a, (hl)
		ld (sd_id+1), a			; +24 ширина — временно в иммедиат ширины
		inc hl
		inc hl
		ld a, (hl)			; +26 pixel X
		rrca
		rrca
		rrca
		and 0x1F
		ld b, a				; xb
		inc hl
		inc hl
		ld e, (hl)			; +28 старая ширина
		inc hl
		inc hl
		ld a, (hl)			; +30 старый pixel X
		rrca
		rrca
		rrca
		and 0x1F
		ld d, a				; oxb
		cp b
		jp c, sd_x1
		ld a, b
sd_x1:		ld (sd_ie+1), a			; левый край = min(xb, oxb)
		ld a, d
		add a, e
		ld e, a				; oxb + старая ширина
		ld hl, sd_id+1
		ld a, b
		add a, (hl)			; xb + ширина
		ld b, a
		ld a, e
		cp b
		jp nc, sd_x2
		ld a, b
sd_x2:		ld hl, sd_ie+1
		sub (hl)
		ld (sd_id+1), a			; ширина = max(...) - левый край
		; ---- ось Y ----
		ld hl, (z80_ix)
		ld de, 25
		add hl, de
		ld a, (hl)
		ld (sd_ih+1), a			; +25 высота — временно в иммедиат высоты
		inc hl
		inc hl
		ld b, (hl)			; +27 pixel Y
		inc hl
		inc hl
		ld e, (hl)			; +29 старая высота
		inc hl
		inc hl
		ld d, (hl)			; +31 старый pixel Y
		ld a, b
		cp d
		jp c, sd_y1
		ld a, d
sd_y1:		ld (sd_il+1), a			; нижний Y = min(Y, oY)
		ld a, d
		add a, e
		ld e, a				; oY + старая высота
		ld hl, sd_ih+1
		ld a, b
		add a, (hl)			; Y + высота
		ld b, a
		ld a, e
		cp b
		jp nc, sd_y2
		ld a, b
sd_y2:		ld hl, sd_il+1
		sub (hl)
		ld (sd_ih+1), a			; высота = max(...) - нижний Y
		; ---- цикл по занятым записям таблицы ----
		ld hl, graphic_objs_tbl
		ld de, 32			; шаг записи живёт в DE весь цикл
		ld a, (a8_nobj)
		ld b, a
sd_loop:	ld a, (hl)			; graphic_no
		or a
		jp z, sd_next
		ld a, l
		add a, 7
		ld l, a				; -> +7 (переноса нет, см. ASSERT)
		ld a, (hl)
		and 0x10			; уже DRAW?
		jp nz, sd_n7
		push hl
		ld a, l
		add a, 19
		ld l, a
		jp nc, sd_p26
		inc h
sd_p26:		ld a, (hl)			; +26 pixel X
		rrca
		rrca
		rrca
		and 0x1F
sd_ie:		sub 0				; - левый край (иммедиат из пролога)
		jp c, sd_xneg
sd_id:		cp 0				; >= ширины объединённого?
		jp nc, sd_pn
		jp sd_yc
sd_xneg:	cpl
		inc a				; neg: левый край - ax
		dec hl
		dec hl				; -> +24 ширина кандидата
		cp (hl)
		jp nc, sd_pn
		inc hl
		inc hl
sd_yc:		inc hl				; -> +27 pixel Y
		ld a, (hl)
sd_il:		sub 0				; - нижний Y
		jp c, sd_yneg
sd_ih:		cp 0				; >= высоты объединённого?
		jp nc, sd_pn
		jp sd_set
sd_yneg:	cpl
		inc a
		dec hl
		dec hl				; -> +25 высота кандидата
		cp (hl)
		jp nc, sd_pn
sd_set:		pop hl				; -> +7
		ld a, (hl)
		or 0x10				; set 4 — пометить DRAW
		ld (hl), a
		jp sd_n7
sd_pn:		pop hl
sd_n7:		ld a, l
		sub 7
		ld l, a
sd_next:	add hl, de
		dec b
		jp nz, sd_loop
		ld hl, (a8_objend)		; IY после цикла = конец занятой части таблицы
		ld (z80_iy), hl
		ret
        ; End of function set_draw_objs_overlapped
"""
