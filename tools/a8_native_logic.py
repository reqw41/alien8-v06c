# -*- coding: utf-8 -*-
"""Нативные i8080-процедуры Alien 8 (логика) и укорочение циклов по таблице объектов.

Аналог kl_native_logic.py из Knight Lore. Два вида правок:
  presub(src)  — на тексте Z80 ДО трансляции (обе цели): граница занятых записей таблицы;
  apply(src)   — замена тел процедур готовым i8080 ПОСЛЕ трансляции (обе цели).

ОБЕ правки идут в ОБЕ цели, и это важно для метода. У Knight Lore шаг «спецификация на
Python -> дамп реальных вызовов -> прогон спецификации по дампу» нужен был затем, чтобы
поймать НЕПОНИМАНИЕ процедуры до ассемблера. Здесь его роль берёт на себя локстеп
против журнала ОРИГИНАЛА (ZX, 600 итераций × 3 сценария, 1928 байт всех переменных игры
байт в байт на КАЖДОЙ итерации): это тот же оракул, только снятый с настоящей игры и
покрывающий не выборку вызовов, а весь прогон целиком. Поэтому spec/ и calldump тут не
заводились — вместо них судья сильнее.

Где локстепа мало (он не видит вывод) — гейт картинки tools/render_gate.sh.
Где нужен инвариант, а не сверка, — tools/nobjcheck_vec.js (граница таблицы объектов).
Где решение принято перебором, а не замером, — проверка исчерпывающая: дерево классов
перекрытия сверено со всеми 27 входами таблицы off_C833 программно.
"""
import re

# Дополнение к scratch-области 0x0040..0x00A0 обеих целей.
SCRATCH = """a8_nobj:		DB		56			; занятых записей graphic_objs_tbl (ставит zero_end_of_graphic_objs_tbl)
a8_objend:		DW		0			; graphic_objs_tbl + a8_nobj*32 — конец занятой части
cdo_scan:		DS		2			; calc_display_order_and_render: первая ещё не отрисованная запись
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
    ('list_objects_to_draw', 'N_LIST_OBJS'),
    ('set_both_deadly_flags', 'N_DEADLY'),
    ('calc_pixel_XY', 'N_CALC_PIXEL_XY'),
    ('do_objs_intersect_on_x', 'N_INTERSECT_X'),
]

# Блоки, конец которых задан следующей меткой, а не комментарием «End of function».
_RANGES = [
    ('calc_display_order_and_render', 'render_list', 'N_DISPLAY_ORDER'),
    ('set_pixel_adj', 'adj_m2_m8', 'N_SET_PIXEL_ADJ'),
    ('upd_02', 'sub_C082', 'N_UPD_02'),
    ('wipe_next_object', 'loc_CF5F', 'N_WIPE'),
]


def apply(src):
    """Замена тел процедур готовым i8080 ПОСЛЕ трансляции."""
    src = scratch(src)
    for name, var in _BODIES:
        src = _sub(src,
                   r'^%s:\n.*?^        ; End of function %s\n' % (name, name),
                   globals()[var], 'тело ' + name, flags=re.M | re.S)
    m = re.search(r'^update_sprite_loop:\n\s*ld sp, (\S+)\n', src, re.M)
    assert m, 'a8_native_logic: не нашёл ld sp в update_sprite_loop'
    src = _sub(src, r'^update_sprite_loop:\n.*?(?=^done_sprite_updates:)',
               N_UPD_LOOP % {'sp': m.group(1)}, 'тело update_sprite_loop', flags=re.M | re.S)
    for name, stop, var in _RANGES:
        src = _sub(src, r'^%s:\n.*?(?=^%s:)' % (name, stop),
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


# ---------------------------------------------------------------------------
# calc_display_order_and_render — 22.4 % тактов итерации: перебор пар объектов из
# objects_to_draw с вычислением класса перекрытия (27 классов, таблица off_C833).
#
# Тело движка совпадает с Knight Lore поле в поле (оси: вес 1 — поля +3/+6, вес 3 — +2/+5,
# вес 9 — +1/+4; класс = z + 3y + 9x), поэтому переносится разбор KL (§17 рецепта):
#
#  * КЛАСС НЕ ВЫЧИСЛЯЕТСЯ ЦЕЛИКОМ. По всем 27 входам таблицы интересны ровно
#    {3,4,6,7,12,15,16} -> d_3467121516 и {13} -> objs_coincide, то есть
#    «y != 0 И x != 2 И z != 2», а 13 — это (x,y,z) = (1,1,1). Значит достаточно дерева:
#    сперва y (y = 0 — единственный выход по ПЕРВОМУ сравнению оси и самый частый),
#    затем x, затем z. Таблица переходов и jump_to_tbl_entry не нужны вовсе.
#  * ГРАНИЦЫ ОБЪЕКТА 1 (шесть чисел) считаются один раз на объект 1 (ov_prep) и живут
#    ИММЕДИАТАМИ внутри сравнений: сравнение с полем объекта 2 не занимает регистров.
#  * ОБЪЕКТ 2 читается указателем HL по месту (inc l / dec l — младший байт записи
#    не переносит, см. ASSERT), копий в память нет.
#  * «Тот же объект?» — сравнение ИНДЕКСОВ (иммедиат cdo_i1) ДО вычисления адреса,
#    а не 16-битное вычитание указателей после.
#  * render_obj_2 пишется не на каждый объект 2, а только в d_3467121516: до него
#    DE = тот самый указатель списка (класс перекрытия DE не трогает).
#  * cdo_scan — первая ещё не отрисованная запись objects_to_draw: перезапуск разбора
#    начинается с неё, а не с начала списка. Бит 7 в этом проходе только СТАВИТСЯ,
#    поэтому записи до cdo_scan отмечены навсегда, и искомый индекс (объект 2 не
#    отрисован) всегда лежит не раньше cdo_scan.
#  * bit 7,a -> or a / jp m; set 7,(hl) -> ld a,(hl) / or 0x80 / ld (hl),a.
#
# Отличия Alien 8 от Knight Lore сохранены дословно: objs_coincide сначала проверяет
# бит 1 поля +7 у ОБОИХ объектов, порог спрайта 0x60..0x63 (cp 4) и подстановка 0x40.
# ---------------------------------------------------------------------------
N_DISPLAY_ORDER = """calc_display_order_and_render:
		ASSERT (graphic_objs_tbl & 31) <= 25	; иначе l+6 переносит и чтение полей объекта 2 ломается
		ld hl, objects_to_draw
		ld (cdo_scan), hl		; отсюда начинается обход списка
cdo_rest:	ld hl, (cdo_scan)
		ex de, hl
cdo_o1:		ld a, (de)			; graphic no
		inc de
		cp 0xFF				; конец списка?
		jp z, cdo_done
		or a
		jp m, cdo_o1			; бит 7 = уже отрисован
		ld (cdo_i1+1), a		; индекс объекта 1 -> иммедиат сравнения
		ld h, d
		ld l, e
		ld (render_obj_1), hl
		dec hl
		ld (cdo_scan), hl		; первая ненарисованная запись
		ld a, (cdo_i1+1)
		call cdo_ptr			; HL = объект 1
		ld (z80_ix), hl
		call ov_prep			; шесть границ объекта 1 -> иммедиаты
cdo_o2:		ld a, (de)			; следующий graphic no
		inc de
		or a				; бит 7 чист -> кандидат (частый случай)
		jp p, cdo_i1
		cp 0xFF				; конец списка?
		jp z, cdo_no2
		jp cdo_o2
cdo_i1:		cp 0				; тот же объект? (иммедиат = индекс объекта 1)
		jp z, cdo_o2
		call cdo_ptr
		inc l
		inc l				; HL = объект 2 + 2 (поле оси веса 3)
		; ---- ось веса 3 ----
		ld a, (hl)
		ld b, a
		inc l
		inc l
		inc l				; +5
		add a, (hl)
		ld c, a				; f2 + d2
ov_ym:		ld a, 0				; [f1 - d1]
		sub c
		jp nc, cdo_o2			; y = 0 -> любой класс продолжает цикл
		ld a, b
		sub (hl)			; f2 - d2
ov_yp:		sub 0				; [f1 + d1]
		jp c, ov_y1			; y = 1
		; y = 2: интересно только при x != 2 и z != 2, и это всегда d_3467121516
		dec l
		dec l
		dec l
		dec l				; +1
		ld a, (hl)
		ld b, a
		inc l
		inc l
		inc l				; +4
		add a, (hl)
		ld c, a
ov_xm2:		ld a, 0				; [f1 - d1]
		sub c
		jp nc, ov_zs			; x = 0
		ld a, b
		sub (hl)
ov_xp2:		sub 0				; [f1 + d1]
		jp nc, cdo_o2			; x = 2 -> продолжить цикл
ov_zs:		dec l				; +3
		ld a, (hl)
		ld b, a
		inc l
		inc l
		inc l				; +6
		add a, (hl)
		ld c, a
ov_z1s:		ld a, 0				; [z1]
		sub c
		jp nc, d_3467121516		; z = 0
		ld a, b				; z2
ov_zhs:		sub 0				; [z1 + h1]
		jp nc, cdo_o2			; z = 2 -> продолжить цикл
		jp d_3467121516			; z = 1
ov_y1:		dec l
		dec l
		dec l
		dec l				; +1
		ld a, (hl)
		ld b, a
		inc l
		inc l
		inc l				; +4
		add a, (hl)
		ld c, a
ov_xm1:		ld a, 0				; [f1 - d1]
		sub c
		jp nc, ov_zs			; x = 0 -> классы 3/4 при z != 2
		ld a, b
		sub (hl)
ov_xp1:		sub 0				; [f1 + d1]
		jp nc, cdo_o2			; x = 2
		dec l				; x = 1, y = 1: +3
		ld a, (hl)
		ld b, a
		inc l
		inc l
		inc l				; +6
		add a, (hl)
		ld c, a
ov_z1f:		ld a, 0				; [z1]
		sub c
		jp nc, d_3467121516		; z = 0 -> класс 12
		ld a, b
ov_zhf:		sub 0				; [z1 + h1]
		jp nc, cdo_o2			; z = 2 -> класс 14
		; z = 1 -> класс 13: объекты совпали
		ld a, l				; сюда всегда с L = объект 2 + 6
		sub 6
		ld l, a
		ld (z80_iy), hl
		ld a, l
		add a, 7
		ld l, a				; +7 объекта 2
		ld b, (hl)
		ld hl, (z80_ix)
		ld a, l
		add a, 7
		ld l, a				; +7 объекта 1
		ld a, (hl)
		or b
		and 2				; бит 1 хоть у одного — ничего не делать
		jp nz, cdo_o2
		ld a, l
		sub 7
		ld l, a				; graphic_no объекта 1
		ld a, (hl)
		sub 0x60
		cp 4
		jp nc, cdo_co2
		ld (hl), 0x40
		jp cdo_o2
cdo_co2:	ld hl, (z80_iy)			; graphic_no объекта 2
		ld a, (hl)
		sub 0x60
		cp 4
		jp nc, cdo_o2
		ld (hl), 0x40
		jp cdo_o2
        ; ---------------------------------------------------------------------------
d_3467121516:	ld a, l				; сюда всегда с L = объект 2 + 6
		sub 6
		ld l, a
		ld (z80_iy), hl			; объект 2 понадобится ниже
		ld h, d				; DE = render_obj_2 (класс перекрытия DE не трогает)
		ld l, e
		ld (render_obj_2), hl
		dec hl				; -> запись объекта 2
		ld c, (hl)			; индекс
		ld de, render_list
cdo_rl:		ld a, (de)
		cp 0xFF				; пустая запись?
		jp z, cdo_add
		cp c				; уже в списке?
		jp z, cdo_found
		inc de
		jp cdo_rl
        ; ---------------------------------------------------------------------------
cdo_add:	ld a, c
		ld (de), a			; добавить в список
		inc de
		ld a, 0xFF
		ld (de), a			; конец списка
		ld a, c
		ld (cdo_i1+1), a		; объект 2 становится объектом 1
		ld hl, (z80_iy)
		ld (z80_ix), hl
		call ov_prep
		ld hl, (render_obj_2)
		ld (render_obj_1), hl
		ld hl, (cdo_scan)		; записи до cdo_scan уже отрисованы
		ex de, hl
		jp cdo_o2
        ; ---------------------------------------------------------------------------
cdo_found:	ld hl, (cdo_scan)
cdo_fl:		ld a, (hl)
		inc hl
		cp 0xFF				; конец списка?
		jp z, cdo_rest
		cp c				; тот, который ищем?
		jp nz, cdo_fl
		push hl
		ld hl, (z80_iy)
		ld (z80_ix), hl			; объект 2 становится объектом 1
		pop hl
		jp cdo_mark
        ; ---------------------------------------------------------------------------
cdo_no2:	ld hl, (render_obj_1)
cdo_mark:	dec hl				; -> запись объекта в objects_to_draw
		ld a, (hl)
		or 0x80				; пометить отрисованным
		ld (hl), a
		ld a, 0xFF
		ld (render_list), a
		ld hl, rendered_objs_cnt
		inc (hl)
		call loc_D013
		jp cdo_rest
        ; ---------------------------------------------------------------------------
cdo_done:	pop hl				; восстановить IY, IX вызывателя
		ld (z80_iy), hl
		pop hl
		ld (z80_ix), hl
		ret
        ; ---------------------------------------------------------------------------
cdo_ptr:	; A = индекс объекта -> HL = адрес записи. Портит A и HL, BC/DE целы.
		add a, a
		ld l, a
		ld h, high a8_optr
		ld a, (hl)
		inc l
		ld h, (hl)
		ld l, a
		ret
		ALIGN 256
a8_optr:	; индекс объекта (0..55) -> адрес записи. Таблица СТАТИЧЕСКАЯ.
		; Индексы приходят ТОЛЬКО из objects_to_draw, а туда их кладёт list_objects_to_draw
		; как счётчик 0..a8_nobj-1, то есть строго меньше 56; записи с битом 7 (отрисован)
		; отсеиваются до вызова. Поэтому маска 0x7F оригинального get_ptr_object не нужна.
		DW graphic_objs_tbl+32*0,  graphic_objs_tbl+32*1,  graphic_objs_tbl+32*2,  graphic_objs_tbl+32*3
		DW graphic_objs_tbl+32*4,  graphic_objs_tbl+32*5,  graphic_objs_tbl+32*6,  graphic_objs_tbl+32*7
		DW graphic_objs_tbl+32*8,  graphic_objs_tbl+32*9,  graphic_objs_tbl+32*10, graphic_objs_tbl+32*11
		DW graphic_objs_tbl+32*12, graphic_objs_tbl+32*13, graphic_objs_tbl+32*14, graphic_objs_tbl+32*15
		DW graphic_objs_tbl+32*16, graphic_objs_tbl+32*17, graphic_objs_tbl+32*18, graphic_objs_tbl+32*19
		DW graphic_objs_tbl+32*20, graphic_objs_tbl+32*21, graphic_objs_tbl+32*22, graphic_objs_tbl+32*23
		DW graphic_objs_tbl+32*24, graphic_objs_tbl+32*25, graphic_objs_tbl+32*26, graphic_objs_tbl+32*27
		DW graphic_objs_tbl+32*28, graphic_objs_tbl+32*29, graphic_objs_tbl+32*30, graphic_objs_tbl+32*31
		DW graphic_objs_tbl+32*32, graphic_objs_tbl+32*33, graphic_objs_tbl+32*34, graphic_objs_tbl+32*35
		DW graphic_objs_tbl+32*36, graphic_objs_tbl+32*37, graphic_objs_tbl+32*38, graphic_objs_tbl+32*39
		DW graphic_objs_tbl+32*40, graphic_objs_tbl+32*41, graphic_objs_tbl+32*42, graphic_objs_tbl+32*43
		DW graphic_objs_tbl+32*44, graphic_objs_tbl+32*45, graphic_objs_tbl+32*46, graphic_objs_tbl+32*47
		DW graphic_objs_tbl+32*48, graphic_objs_tbl+32*49, graphic_objs_tbl+32*50, graphic_objs_tbl+32*51
		DW graphic_objs_tbl+32*52, graphic_objs_tbl+32*53, graphic_objs_tbl+32*54, graphic_objs_tbl+32*55
		ASSERT (a8_optr & 0xFF) == 0
        ; ---------------------------------------------------------------------------
ov_prep:	; HL = объект 1: шесть границ -> иммедиаты сравнений. Портит A, B, HL.
		inc l
		ld a, (hl)			; +1
		ld b, a
		inc l
		inc l
		inc l				; +4
		add a, (hl)
		ld (ov_xp1+1), a
		ld (ov_xp2+1), a
		ld a, b
		sub (hl)
		ld (ov_xm1+1), a
		ld (ov_xm2+1), a
		dec l
		dec l				; +2
		ld a, (hl)
		ld b, a
		inc l
		inc l
		inc l				; +5
		add a, (hl)
		ld (ov_yp+1), a
		ld a, b
		sub (hl)
		ld (ov_ym+1), a
		dec l
		dec l				; +3
		ld a, (hl)
		ld (ov_z1s+1), a
		ld (ov_z1f+1), a
		inc l
		inc l
		inc l				; +6
		add a, (hl)
		ld (ov_zhs+1), a
		ld (ov_zhf+1), a
		ret
        ; ---------------------------------------------------------------------------
"""


# ---------------------------------------------------------------------------
# set_pixel_adj — 4.9 % тактов итерации (38 вызовов, тело из двух записей (ix+d)).
#
# `ld (ix+18),l : ld (ix+19),h : ret` — и больше ничего: оригинал не трогает НИ ОДНОГО
# регистра и не меняет флагов, а вызывают его почти всегда хвостом (`jr set_pixel_adj`
# из десятка adj_*/upd_*), то есть флаги и A видны в вызывающем вызывающего. Поэтому
# нативная версия сохраняет всё: AF через стек, DE через стек, HL — обменом.
#
# Указатель объекта в HL, поле +18 — сложением младшего байта: (graphic_objs_tbl & 31) = 8,
# запись 32-байтная, значит l ≡ 8 (mod 32), l+19 ≤ 251 — переноса нет (ASSERT).
# IX здесь всегда запись graphic_objs_tbl: все вызыватели — обработчики upd_* диспетчера
# update_sprite_loop и их adj_*-обёртки.
# 332 такта на вызов -> 112.
# ---------------------------------------------------------------------------
N_SET_PIXEL_ADJ = """set_pixel_adj:
		ASSERT (graphic_objs_tbl & 31) <= 12	; иначе l+19 переносит и адресация поля ломается
		push af				; оригинал (ld (ix+d),r) флаги и A не трогает
		push de
		ex de, hl			; DE = значение (pixel_x_adj, pixel_y_adj)
		ld hl, (z80_ix)
		ld a, l
		add a, 18
		ld l, a				; -> +18 (переноса нет, см. ASSERT)
		ld (hl), e
		inc l
		ld (hl), d			; -> +19
		ex de, hl			; HL обратно = значение, DE = указатель
		pop de
		pop af
		ret
        ; ---------------------------------------------------------------------------
"""


# ---------------------------------------------------------------------------
# set_both_deadly_flags — 2.9 % тактов итерации (20 вызовов).
# `ld a,(ix+13) : or 0xA0 : ld (ix+13),a : ret`: чтение и запись одного поля, развёрнутые
# транслятором в две вставки (ix+d) с сохранением A и флагов вокруг каждой.
# Нативно — один указатель в HL. Оригинал портит только A и флаги (флаги ставит `or 0xA0`,
# и вызыватели их видят: `jr set_both_deadly_flags` хвостом), поэтому HL сохраняется через
# стек, а `pop hl` флагов не меняет — результат `or 0xA0` доходит до вызывающего.
# 372 такта на вызов -> 85.
# ---------------------------------------------------------------------------
N_DEADLY = """set_both_deadly_flags:
		ASSERT (graphic_objs_tbl & 31) <= 18	; иначе l+13 переносит
		push hl
		ld hl, (z80_ix)
		ld a, l
		add a, 13
		ld l, a				; -> +13 flags13 (переноса нет, см. ASSERT)
		ld a, (hl)
		or 0xA0
		ld (hl), a
		pop hl				; POP rp флагов не трогает — Z/S/P от `or` целы
		ret
        ; End of function set_both_deadly_flags
"""


# ---------------------------------------------------------------------------
# calc_pixel_XY — 4.1 % тактов итерации (6.9 вызова): изометрия объекта в пиксельные X/Y.
# Восемь чтений и две записи (ix+d) — транслятор разворачивал каждое в отдельную вставку
# со своим сохранением A и флагов.
#
# Нативно весь проход идёт ОДНИМ указателем HL: сперва +18/+19 (обе поправки — в C и B),
# затем возврат на +1 и ход по X, Y, Z шагами inc/dec l. Запись в +26/+27 — единственное
# место, где младший байт может перенести (l ≡ 8 mod 32, 8+26 = 34 > 31), поэтому там
# явный `jp nc / inc h`; все остальные смещения ≤ +19 в 32-байтную запись укладываются
# (ASSERT). `srl a` -> `or a` + `rra`, как это делает и транслятор.
#
# Оригинал портит ТОЛЬКО A и флаги (BC, DE, HL целы) — BC и HL сохраняются стеком, DE не
# нужен. Выход: A = пиксельный Y, флаги от `cp 192` (вызыватели читают перенос:
# loc_D01F делает `call calc_pixel_XY : ret nc`), либо A = byte_5B24 и CY=1 из ранней
# ветки — оба пути оставлены дословно. POP rp флагов не трогает, поэтому `cp 192` стоит
# после снятия со стека.
# 1527 тактов на вызов -> 302.
# ---------------------------------------------------------------------------
N_CALC_PIXEL_XY = """calc_pixel_XY:
		ASSERT (graphic_objs_tbl & 31) <= 12	; иначе l+19 переносит
        ld a, (byte_5B24)
        and a
        scf
        ret nz
		push hl
		push bc
		ld hl, (z80_ix)
		ld a, l
		add a, 18
		ld l, a				; -> +18
		ld c, (hl)			; pixel_x_adj
		inc l
		ld b, (hl)			; +19 pixel_y_adj
		ld a, l
		sub 18
		ld l, a				; -> +1
		ld a, (hl)			; X
		inc l				; -> +2
		add a, (hl)			; + Y
		sub 128
		add a, c			; + pixel_x_adj
		ld c, a				; пиксельный X
		ld a, (hl)			; Y
		dec l				; -> +1
		sub (hl)			; - X
		add a, 128
		or a				; srl a
		rra
		inc l
		inc l				; -> +3
		add a, (hl)			; + Z
		sub 40
		add a, b			; + pixel_y_adj
		ld b, a				; пиксельный Y
		ld a, l
		add a, 23
		ld l, a				; -> +26 (единственный перенос)
		jp nc, cpxy_st
		inc h
cpxy_st:	ld (hl), c			; +26 пиксельный X
		inc l
		ld (hl), b			; +27 пиксельный Y
		ld a, b
		pop bc
		pop hl
        cp 192   ; bottom line of screen?
        ret
        ; End of function calc_pixel_XY
"""


# ---------------------------------------------------------------------------
# upd_02 (арка, 3.0 % тактов итерации, 4 вызова) — вся цепочка upd_02 .. loc_C080.
#
# Тело коротко, но почти целиком состоит из обращений к полям: bit 6,(ix+7); X/Y (+1/+2);
# dX/dY/dZ (+9/+10/+11); Z (+3); (iy+0), bit 3,(iy+7); в редкой ветке ещё четыре.
# Нативно — два указателя-прохода по HL и абсолютная адресация там, где IY константа.
#
# Что доказано и на что опирается перепись:
#  * IX здесь — запись graphic_objs_tbl (upd_02 стоит только в таблице обработчиков
#    upd_sprite_jmp_tbl, куда диспетчер входит с IX = текущая запись), поэтому поля
#    адресуются младшим байтом: l ≡ 8 (mod 32), максимум l+11 = 243 — переноса нет (ASSERT).
#  * `ld iy, graphic_objs_tbl` — КОНСТАНТА, и до loc_C050/loc_C069 её никто не меняет
#    (sub_C099 только читает (iy+1..3); loc_C312 -> get_sprite_dir трогает лишь (ix+7)/(ix+0)
#    и HL; jump_to_tbl_entry — HL/BC). Значит (iy+d) в хвосте — абсолютные адреса.
#    Запись `ld (z80_iy), hl` всё равно обязательна: sub_C099 и sub_C082 читают IY оттуда.
#  * BC не трогается: допуск sub_C099 (0x60F/0xF06/0xF0F) живёт в HL, как в оригинале,
#    а `push bc`/`pop bc` вокруг диспетчера off_C048 сохранены дословно.
#  * Чтение X/Y ПЕРЕД set_pixel_adj вместо «после» равнозначно: set_pixel_adj пишет
#    только +18/+19.
#  * HL на всех выходах — ровно как в оригинале (0x0F0F на ранних `ret z`).
#  * `bit n,(iy+7)` -> `and маска` (Z тот же; A и перенос после не читаются),
#    `neg` -> `cpl : inc a`.
# 1750 тактов на вызов -> ~460.
# ---------------------------------------------------------------------------
N_UPD_02 = """upd_02:
		ASSERT (graphic_objs_tbl & 31) <= 20	; иначе l+11 переносит
		ld hl, (z80_ix)
		ld a, l
		add a, 7
		ld l, a				; -> +7
		ld a, (hl)
		and 0x40			; bit 6, (ix+7)
		jp nz, u02_far
		ld a, l
		sub 6
		ld l, a				; -> +1
		ld d, (hl)			; dX = X
		inc l				; -> +2
		ld a, (hl)			; Y
		add a, 13
		ld e, a				; dY = Y + 13
		ld hl, 0xF9FA			; -7,-6
		call set_pixel_adj
		call u02_store
		ld hl, 0x060F
		call sub_C082
		jp u02_iy
u02_far:	ld a, l
		sub 6
		ld l, a				; -> +1
		ld a, (hl)			; X
		sub 13
		ld d, a				; dX = X - 13
		inc l				; -> +2
		ld e, (hl)			; dY = Y
		ld hl, 0xFAF6
		call set_pixel_adj
		call u02_store
		ld hl, 0x0F06
		call sub_C082
u02_iy:		ld hl, graphic_objs_tbl		; IY = игрок
		ld (z80_iy), hl
		ld hl, 0x0F0F			; допуск sub_C099 (как в оригинале — до проверок)
		ld a, (graphic_objs_tbl)	; (iy+0) player graphic no
		or a
		ret z
		ld a, (graphic_objs_tbl+7)
		and 8				; bit 3, (iy+7)
		ret z
		call sub_C099
		ret nc
		push bc
		ld bc, off_C048
		jp loc_C312
        ; ---------------------------------------------------------------------------
off_C048:
        DW loc_C050
        DW loc_C050
        DW loc_C069
        DW loc_C069
        ; ---------------------------------------------------------------------------
loc_C050:	ld a, (graphic_objs_tbl+7)
		and 0x40			; bit 6, (iy+7)
		jp nz, loc_C080
		ld hl, (z80_ix)
		ld a, l
		add a, 10
		ld l, a
		ld a, (hl)			; (ix+10) dY
		ld hl, graphic_objs_tbl+2
		cp (hl)				; (iy+2)
		jp z, loc_C080
		ld a, 1
		jp nc, u02_s15
		cpl
		inc a				; neg
u02_s15:	ld (graphic_objs_tbl+15), a
		jp loc_C080
        ; ---------------------------------------------------------------------------
loc_C069:	ld a, (graphic_objs_tbl+7)
		and 0x40			; bit 6, (iy+7)
		jp z, loc_C080
		ld hl, (z80_ix)
		ld a, l
		add a, 9
		ld l, a
		ld a, (hl)			; (ix+9) dX
		ld hl, graphic_objs_tbl+1
		cp (hl)				; (iy+1)
		jp z, loc_C080
		ld a, 1
		jp nc, u02_s14
		cpl
		inc a				; neg
u02_s14:	ld (graphic_objs_tbl+14), a
loc_C080:	pop bc
		ret
        ; ---------------------------------------------------------------------------
u02_store:	; D = dX, E = dY -> +9/+10, dZ = Z (+3) -> +11. Портит A и HL.
		ld hl, (z80_ix)
		ld a, l
		add a, 3
		ld l, a				; -> +3
		ld a, (hl)			; Z
		inc l
		inc l
		inc l
		inc l
		inc l
		inc l				; -> +9
		ld (hl), d
		inc l
		ld (hl), e			; +10
		inc l
		ld (hl), a			; +11 dZ = Z
		ret
        ; ---------------------------------------------------------------------------
"""


# ---------------------------------------------------------------------------
# wipe_next_object — 3.0 % тактов итерации: по списку objects_to_draw стирается окно
# «объединение старого и нового положения объекта». На объект со взведённым битом 5
# приходилось 16 обращений (ix+d): +7 дважды, затем восьмёрка +24..+31 в разном порядке.
#
# Регистров на всё не хватает (оригинал держит запись в IX, а A/B/C/E/H/L заняты счётом),
# поэтому указатель записи живёт в DE — поля читаются как `ld a,(de)` + `inc e` по 12 тактов
# вместо 130. Позиционирование на +24 — единственное место с возможным переносом младшего
# байта (l ≡ 8 mod 32, 8+24 = 32), дальше e ≡ 0 (mod 32) и +24..+31 лежат в одном блоке.
#
# Разведение результатов по регистрам: ось X даёт C (min пиксельный X) и H (ширина в
# колонках), ось Y — B (min пиксельный Y) и L (высота); обе оси считаются одними и теми же
# временными регистрами, поэтому пара X кладётся на стек и снимается после оси Y
# (`pop de` + `ld c,e` / `ld h,d`). Стек внутри сбалансирован: ранние выходы — либо ДО
# push (бит 5 чист), либо ПОСЛЕ pop (левый край >= 192).
#
# Прочее:
#  * `call get_ptr_object` -> `and 0x7F` + `cdo_ptr` (таблица a8_optr): маска нужна,
#    индексы приходят из objects_to_draw уже с битом «отрисован»;
#  * `ld (z80_ix), hl` сохранено — IX в этой области видят вызываемые процедуры и
#    `pop ix` в конце render_dynamic_objects;
#  * `bit 5,(ix+7)`/`res 5,(ix+7)` -> `and 0x20` / `and 0xDF` по одному указателю;
#  * `neg` -> `cpl : inc a`; хвост от отсечения по 0xC0 и до fill_window — дословно.
# ---------------------------------------------------------------------------
N_WIPE = """wipe_next_object:
		ASSERT (graphic_objs_tbl & 31) <= 24	; иначе l+7 переносит
        ld hl, (tmp_objects_to_draw)
        ld a, (hl)
        inc hl
        ld (tmp_objects_to_draw), hl
        cp 0xFF
        jp z, loc_CF5F
		and 0x7F			; индекс приходит с битом «отрисован»
		call cdo_ptr			; HL = запись объекта (таблица a8_optr)
		ld (z80_ix), hl			; IX этой области видят и вызываемые, и pop ix в конце
		ld a, l
		add a, 7
		ld l, a				; -> +7
		ld a, (hl)
		and 0x20			; bit 5, (ix+7)
		jp z, wipe_next_object
		ld a, (hl)
		and 0xDF			; res 5, (ix+7)
		ld (hl), a
		ld a, l
		add a, 17
		ld l, a				; -> +24 (единственный перенос)
		jp nc, wno_p24
		inc h
wno_p24:	ex de, hl			; DE = указатель на +24, HL свободен
        ; ---- ось X: min пиксельного X и максимум правых краёв ----
		ld a, (de)			; +24 ширина новая
		ld c, a
		inc e
		inc e				; +26
		ld a, (de)
		ld b, a				; X новый
		rrca
		rrca
		rrca
		and 0x1F
		add a, c
		ld c, a				; правый край новый
		inc e
		inc e				; +28
		ld a, (de)
		ld h, a				; ширина старая
		inc e
		inc e				; +30
		ld a, (de)
		ld l, a				; X старый
		rrca
		rrca
		rrca
		and 0x1F
		add a, h
		ld h, a				; правый край старый
		ld a, c
		cp h
		jp nc, wno_xmax
		ld c, h
wno_xmax:	ld a, b				; C = max правых краёв
		sub l
		jp c, wno_xmin
		ld b, l
wno_xmin:	ld a, b				; B = min(X новый, X старый)
		rrca
		rrca
		rrca
		and 0x1F
		ld l, a				; левая колонка
		ld a, c
		sub l
		ld h, a				; ширина в колонках
		ld c, b				; min пиксельный X
		push hl
		push bc				; пара оси X — на стек, регистры нужны оси Y
        ; ---- ось Y ----
		ld a, e
		sub 5
		ld e, a				; -> +25
		ld a, (de)			; высота новая
		ld b, a
		inc e
		inc e				; +27
		ld a, (de)
		ld c, a				; Y новый
		add a, b
		ld b, a				; Y новый + высота новая
		inc e
		inc e				; +29
		ld a, (de)
		ld h, a				; высота старая
		inc e
		inc e				; +31
		ld a, (de)
		ld l, a				; Y старый
		add a, h
		ld h, a				; Y старый + высота старая
		ld a, b
		cp h
		jp nc, wno_ymax
		ld b, h
wno_ymax:	ld a, c				; B = max нижних краёв
		sub l
		jp c, wno_ymin
		ld c, l
wno_ymin:	ld a, b				; C = min(Y новый, Y старый)
		sub c
		ld l, a				; высота окна
		ld b, c				; min пиксельный Y
		pop de
		ld c, e				; C = min пиксельный X
		pop de
		ld h, d				; H = ширина в колонках
        ; ---- отсечение по нижней строке экрана (дословно) ----
		ld a, b
        cp 0xC0   ; 'A'
		jp nc, wipe_next_object
        add a, l
        sub 0xC0   ; 'A'
		jp c, wno_win
		cpl
		inc a				; neg
        add a, l
        ld l, a
wno_win:
        call BC_to_Attr_In_DE
        call calc_screen_buffer_addr
        ld a, l
        ld l, c
        ld c, a
        ld a, h
        ld h, b
        ld b, a
        ld a, (objs_wiped_cnt)
        inc a
        ld (objs_wiped_cnt), a
        push bc
        push de
        push hl
        xor a
        call fill_window
        jp wipe_next_object
        ; ---------------------------------------------------------------------------
"""


# ---------------------------------------------------------------------------
# update_sprite_loop + jump_to_upd_object + jump_to_tbl_entry + ret_from_tbl_jp —
# диспетчер обновления объектов, 56 (теперь 40) проходов на итерацию, 22 % тактов.
#
# Что сделано:
#  * четыре копии полей (+24..+27 -> +28..+31) идут парой указателей HL/DE по 32 такта
#    на поле вместо восьми обращений (ix+d) по 130;
#  * ret_from_tbl_jp: подмешивание `ld a,r` в seed_3 УБРАНО целиком. На i8080 регистра R
#    нет, транслятор ставит `ld a,0`, и детерминированный снимок ZX-стенда патчен так же
#    (см. LOCKSTEP.md, три сайта ED 5F -> 3E 00), то есть `seed_3 += 0` — запись того же
#    значения. Локстеп это подтверждает байт в байт.
#  * шаг к следующей записи и сравнение с концом занятой части — 8-битными операциями
#    (sub l / sbb h), без 16-битной эмуляции sbc hl,bc с восстановлением флагов.
# jump_to_tbl_entry остаётся общей точкой (L = индекс, BC = таблица): в неё прыгает
# calc_plyr_dXY. jump_to_upd_object — точка входа для upd_3F.
# ---------------------------------------------------------------------------
N_UPD_LOOP = """update_sprite_loop:
		ld sp, %(sp)s
		ld hl, ret_from_tbl_jp		; адрес возврата обработчика
		push hl
		ld hl, (z80_ix)
		ld d, h
		ld e, l
		ld a, l
		add a, 24
		ld l, a
		ld a, h
		adc a, 0
		ld h, a				; HL = +24 (ширина, высота, X, Y)
		ld a, e
		add a, 28
		ld e, a
		ld a, d
		adc a, 0
		ld d, a				; DE = +28 (их «старые» копии)
		ld a, (hl)
		ld (de), a
		inc hl
		inc de
		ld a, (hl)
		ld (de), a
		inc hl
		inc de
		ld a, (hl)
		ld (de), a
		inc hl
		inc de
		ld a, (hl)
		ld (de), a
jump_to_upd_object:
		ld hl, (z80_ix)
		ld a, (hl)			; graphic_no -> номер обработчика
		ld l, a
		ld bc, upd_sprite_jmp_tbl
jump_to_tbl_entry:
		ld h, 0
		add hl, hl
		add hl, bc
		ld a, (hl)
		inc hl
		ld h, (hl)
		ld l, a
		jp (hl)
        ; ---------------------------------------------------------------------------
ret_from_tbl_jp:
		; `ld a,r : ld c,a : ld a,(seed_3) : add a,c : ld (seed_3),a` — на i8080 R нет,
		; a = 0, то есть seed_3 не меняется; снято целиком.
		ld hl, (z80_ix)
		ld a, l
		add a, 32			; следующая запись таблицы
		ld l, a
		jp nc, usl_nc
		inc h
usl_nc:		ld (z80_ix), hl
		ex de, hl
		ld hl, (a8_objend)
		ld a, e
		sub l
		ld a, d
		sbc a, h			; конец занятой части пройден?
		jp nc, done_sprite_updates
		jp update_sprite_loop
        ; ---------------------------------------------------------------------------
"""


# ---------------------------------------------------------------------------
# list_objects_to_draw: индексы непустых объектов с флагом DRAW (бит 4 поля +7) ->
# objects_to_draw, терминатор 0xFF. Один вызов, 40 проходов, 430 тактов на проход.
# Указатель объекта в HL, поле флагов как l+7 (переноса нет, см. ASSERT в
# set_draw_objs_overlapped), возврат к базе слит с шагом +32 в одно сложение +25.
# Оригинал сохраняет только IX; DE/HL/BC он портит — здесь тоже.
# ---------------------------------------------------------------------------
N_LIST_OBJS = """list_objects_to_draw:
		ld hl, (z80_ix)
		push hl
		ld hl, graphic_objs_tbl
		ld de, objects_to_draw
		ld c, 0
		ld a, (a8_nobj)
		ld b, a
lo_1:		ld a, (hl)			; graphic_no
		or a
		jp z, lo_skip
		ld a, l
		add a, 7
		ld l, a				; -> +7
		ld a, (hl)
		and 0x10			; DRAW?
		jp z, lo_n7
		ld a, c
		ld (de), a			; индекс -> список
		inc de
lo_n7:		ld a, l
		add a, 25			; -7 и сразу +32
		ld l, a
		jp nc, lo_step
		inc h
		jp lo_step
lo_skip:	ld a, l
		add a, 32
		ld l, a
		jp nc, lo_step
		inc h
lo_step:	inc c
		dec b
		jp nz, lo_1
		ld a, 0xFF
		ld (de), a			; конец списка
		pop hl
		ld (z80_ix), hl
		ret
        ; End of function list_objects_to_draw
"""


# ---------------------------------------------------------------------------
# do_objs_intersect_on_x — 10.9 % тактов комнаты 48 (75.7 вызова, 1099 тактов на вызов).
# Четыре обращения (ix+4), (iy+4), (ix+1), (iy+1) — четыре компактных хелпера по 260 тактов.
#
# Нативно: два указателя записей (по одному за раз в HL), поля — сдвигом младшего байта.
# (graphic_objs_tbl & 31) = 8, запись 32-байтная => l ≡ 8 (mod 32), l+4 ≤ 236 — переноса
# нет (ASSERT).
#
# ЧТО ДОЛЖНО ДОЙТИ ДО ВЫЗЫВАЮЩЕГО. Все пять вызывателей (do_any_objs_intersect,
# adj_dX/dY/dZ_for_obj_intersect, is_on_or_near_obj) читают РОВНО перенос (`jr nc`/`jr c`),
# держа в B счётчик, в C — dX, в L — dY, в H — dZ, в IX — свой объект, в IY — кандидата.
# Поэтому B, C, H, L, IX, IY обязаны уцелеть, а последней командой стоит тот же `sub`,
# что и в оригинале, — флаги совпадают побитно. DE оригинал портит (D = сумма ширин),
# нативная версия его СОХРАНЯЕТ: опереться на порчу нельзя, а восстановление бесплатно
# (POP rp на i8080 флагов не трогает, поэтому стоит после `sub`).
# 1099 тактов на вызов -> 209.
# ---------------------------------------------------------------------------
N_INTERSECT_X = """do_objs_intersect_on_x:
		ASSERT (graphic_objs_tbl & 31) <= 27	; иначе l+4 переносит
		push hl
		push de
		ld hl, (z80_ix)
		ld a, l
		add a, 4
		ld l, a				; -> +4 полуширина по X
		ld d, (hl)
		dec l
		dec l
		dec l				; -> +1 X
		ld e, (hl)
		ld hl, (z80_iy)
		ld a, l
		add a, 4
		ld l, a				; -> +4
		ld a, d
		add a, (hl)
		ld d, a				; D = сумма полуширин
		dec l
		dec l
		dec l				; -> +1
		ld a, e
		add a, c			; X своего объекта + dX
		sub (hl)
		jp p, doi_x1
		cpl
		inc a				; neg
doi_x1:
		sub d
		pop de				; POP rp флагов не трогает — перенос от `sub` цел
		pop hl
		ret
        ; End of function do_objs_intersect_on_x
"""
