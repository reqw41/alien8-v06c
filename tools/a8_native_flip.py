# -*- coding: utf-8 -*-
"""Нативный i8080-разворот спрайтов Alien 8 (ветка flipcache).

Две правки, как и в a8_native_logic (модуль отдельный, чтобы не конфликтовать с ветками,
которые правят тот файл):
  presub(src) — на тексте Z80 ДО трансляции: «разворот про запас» в calc_2d_info -> sprite_addr;
  apply(src)  — замена тел flip_sprite и chunk'а vflip_sprite_data готовым i8080 ПОСЛЕ неё.
Обе идут в ОБЕ цели (lockstep и vec): судья логики — локстеп против журнала оригинала,
судья самих байтов спрайта — tools/flipcheck_vec.js (локстеп их не видит, см. рецепт).

ЗАЧЕМ (замер tools/flipstat_vec.js, 150 итераций, шесть комнат):
  * V-разворот не исполняется НИ РАЗУ (0.00/итер) — но код обязан быть верным, его проверяет гейт;
  * H-разворотов 0.06..0.11/итер, но КАЖДЫЙ стоит 72..110 тысяч тактов = 220..330 тактов на байт
    спрайта: H-ветка оригинала держит указатель в альтернативном наборе, а `exx` на i8080
    эмулируется обменом регистров через память;
  * холостая проверка «спрайт уже в нужной ориентации» — 686..1111 тактов на вызов при
    5..18 вызовах за итерацию (в комнатах 88 и 48 это БОЛЬШЕ самих разворотов): виноваты
    развёрнутые (ix+0) и два (ix+7) по ~130 тактов.
Кэш развёрнутых копий (Knight Lore 404039c) здесь ОТВЕРГНУТ замером: в Alien 8
разворачиваются крупные спрайты героя (338/290/250 Б), слоты под них не влезают в долю
ветки (800 Б), а выигрыш после нативного разворота — 0.5 % (см. рецепт, заход 3).

ФОРМАТ СПРАЙТА: байт 0 — бит 7 хранимый V, бит 6 хранимый H, младший ниббл — ширина в ПАРАХ
(байт маски + байт данных); байт 1 — высота; дальше 2*w*h байт. Разбор всех 77 спрайтов:
биты 4-5 не заняты ни у одного, поэтому `and 0x3F` V-ветки и `and 0x0F` H-ветки равны.
"""
import re

# Таблица бит-реверса: её строит build_lookup_tbls по фиксированному адресу 0xF100
# (оригинал адресует её как `ld b, 0xF1` / `ld a,(bc)`), метки у неё нет.
REV_TBL = 0xF100


def _sub(src, pat, repl, name, count=1, flags=re.M):
    src, n = re.subn(pat, lambda m: repl, src, count=count, flags=flags)
    assert n == count, "a8_native_flip: не найдено (%s): %d вместо %d" % (name, n, count)
    return src


def presub(src):
    """Проверки на тексте Z80 ДО трансляции.

    ДОКАЗАТЕЛЬСТВО (KL b950776 + трассер A8SPRTRACE=1 в tools/flipstat_vec.js):
    из развёрнутых данных calc_2d_info читает РОВНО два байта — заголовок (ширина, `and 0xF`)
    и высоту, — а разворот меняет в заголовке только биты 7/6 и переставляет байты данных:
    ширина и высота от разворота не зависят. Трассер по всем байтам всех спрайтов
    подтверждает: на 186 вызовов calc_2d_info приходится ровно 186 чтений на метке
    calc_2d_info и 186 на loc_C64D — по одному байту каждое, данных она не трогает.
    Единственные ПИСАТЕЛИ байтов спрайта — сам разворот (loc_D1DA и loc_D1AF), единственный
    читатель данных — вывод print_sprite, а он вызывает flip_sprite сам.
    Путь «пустой спрайт -> выход ЗА вызывающего» (inc sp/inc sp/ret) сохранён дословно.
    Замер: сам «разворот про запас» не развернул НИ ОДНОГО спрайта на шести комнатах,
    но стоил 1 310..3 056 тактов/итер одной только проверкой.
    """
    # адрес таблицы бит-реверса зашит в нативном H-развороте — проверить, что её всё ещё
    # строят по тому же адресу
    assert len(re.findall(r'^        ld hl, 0x%04X\n' % REV_TBL, src, re.M | re.I)) == 1, \
        'a8_native_flip: build_lookup_tbls больше не строит таблицу бит-реверса на 0x%04X' % REV_TBL
    return src


# ---------------------------------------------------------------------------
# Голова: адрес спрайта по (ix+0). Два входа с одним телом не делаются нарочно — общее тело
# пришлось бы звать `call`, а обе процедуры при ПУСТОМ спрайте обязаны вернуться ЗА своего
# вызывающего (inc sp/inc sp/ret), и лишний кадр стека это ломает.
# ---------------------------------------------------------------------------
N_HEAD = """flip_sprite:
        ; A8(flipcache): нативная голова вместо развёрнутых (ix+d) — было 686..1111 тактов
        ; на вызов только на проверку «спрайт уже в нужной ориентации».
        ld hl, (z80_ix)
        ld a, (hl)   ; (ix+0) = номер спрайта
        ld l, a
        ld h, 0
        add hl, hl
        ld bc, sprite_tbl
        add hl, bc
        ld e, (hl)
        inc hl
        ld d, (hl)   ; DE = данные спрайта
        ld a, (de)
        and a
        jp nz, vflip_sprite_data
        inc sp
        inc sp   ; пустой спрайт: возврат ЗА вызывающего
        ret
sprite_addr:
        ; То же, но БЕЗ разворота (для calc_2d_info): ширина и высота от разворота не зависят.
        ld hl, (z80_ix)
        ld a, (hl)
        ld l, a
        ld h, 0
        add hl, hl
        ld bc, sprite_tbl
        add hl, bc
        ld e, (hl)
        inc hl
        ld d, (hl)
        ld a, (de)
        and a
        ret nz
        inc sp
        inc sp   ; пустой спрайт: возврат ЗА вызывающего
        ret
        ; End of function flip_sprite
"""

# ---------------------------------------------------------------------------
# Тело разворота. Вход: DE = данные спрайта, (ix+7) = требуемая ориентация (биты 7/6).
# Выход: DE = тот же адрес (мастер разворачивается НА МЕСТЕ, как в оригинале; кэша нет —
# см. докстроку). Портит A, BC, HL — ровно как оригинал, только без альтернативного набора.
# Отличие от оригинала ОДНО и намеренное: вырожденные спрайты (ширина 0, высота 0 или
# высота 1 у V-разворота) пропускаются. У оригинала `srl c` при h=1 даёт 0, и `dec c/jr nz`
# уходит на 256 проходов по чужой памяти; в игре таких вызовов не бывает (h=1 только у
# spr_28), а гейт сверяет с моделью, где перестановка одной строки — тождество.
# ---------------------------------------------------------------------------
N_BODY = """        ; START OF FUNCTION CHUNK FOR flip_sprite
fl_rev          equ     %(rev)#06x   ; reverse_bits_table (её строит build_lookup_tbls)
vflip_sprite_data:
        ld hl, (z80_ix)
        ld bc, 7
        add hl, bc   ; HL = &(ix+7)
        ld a, (de)
        xor (hl)
        and 0xC0
        ret z   ; быстрый путь: ориентация уже нужная
        ld (fl_need), a   ; какие биты переворачивать
        push de
        and 0x80
        jp z, fl_h
        ; ---- V: обмен строк i <-> h-1-i ----
        ld a, (de)
        xor 0x80
        ld (de), a
        and 0x3F   ; ширина в парах (как в оригинале)
        add a, a
        ld (fl_w2), a   ; байт в строке = 2*w
        jp z, fl_h
        inc de
        ld a, (de)
        inc de   ; DE = строка 0
        ld (fl_cnt2), a
        cp 2
        jp c, fl_h   ; h < 2 — менять нечего
        dec a
        ld b, a   ; шагов вниз = h-1
        ld h, d
        ld l, e
        ld a, (fl_w2)
        ld c, a
fl_vq:
        ld a, l
        add a, c
        ld l, a
        ld a, h
        adc a, 0
        ld h, a
        dec b
        jp nz, fl_vq   ; HL = последняя строка
        ld a, (fl_cnt2)
        and a   ; сбросить перенос перед rra
        rra
        ld (fl_cnt2), a   ; пар строк = h/2 (>= 1, потому что h >= 2)
fl_vrow:
        ld a, (fl_w2)
        ld b, a
fl_vb:
        ld a, (de)
        ld c, (hl)
        ld (hl), a
        ld a, c
        ld (de), a
        inc hl
        inc de
        dec b
        jp nz, fl_vb
        ld a, (fl_w2)
        add a, a
        ld c, a
        ld a, l
        sub c
        ld l, a
        ld a, h
        sbc a, 0
        ld h, a   ; HL = предыдущая строка снизу
        ld a, (fl_cnt2)
        dec a
        ld (fl_cnt2), a
        jp nz, fl_vrow
        ; ---- H: зеркало строки по парам + бит-реверс каждого байта ----
fl_h:
        pop de
        push de
        ld a, (fl_need)
        and 0x40
        jp z, fl_ret
        ld a, (de)
        xor 0x40
        ld (de), a
        and 0x0F   ; ширина в парах
        ld (fl_w), a
        jp z, fl_ret
        inc de
        ld a, (de)
        ld (fl_hh), a
        inc de   ; DE = строка 0
        and a
        jp z, fl_ret
        ld h, high fl_rev   ; H держим до конца: L = байт, (HL) = его бит-реверс
fl_hrow:
        push de   ; начало строки
        ld a, (fl_w)
        add a, a
        dec a
        dec a
        add a, e
        ld c, a
        ld a, d
        adc a, 0
        ld b, a   ; BC = последняя пара строки, DE = первая
        ld a, (fl_w)
        and a
        rra
        ld (fl_cnt), a   ; обменов = w/2
        and a   ; rra (RAR) на i8080 НЕ трогает Z: без этого при w=1 счётчик 0 крутил обмен 256 раз
        jp z, fl_hmid
fl_hswap:
        ld a, (de)   ; маска слева
        ld l, a
        ld a, (hl)
        push af
        ld a, (bc)   ; маска справа
        ld l, a
        ld a, (hl)
        ld (de), a
        pop af
        ld (bc), a
        inc de
        inc bc
        ld a, (de)   ; данные слева
        ld l, a
        ld a, (hl)
        push af
        ld a, (bc)   ; данные справа
        ld l, a
        ld a, (hl)
        ld (de), a
        pop af
        ld (bc), a
        inc de
        dec bc
        dec bc
        dec bc
        ld a, (fl_cnt)
        dec a
        ld (fl_cnt), a
        jp nz, fl_hswap
fl_hmid:
        ld a, (fl_w)
        and 1
        jp z, fl_hnext
        ld a, (de)   ; средняя пара: только бит-реверс
        ld l, a
        ld a, (hl)
        ld (de), a
        inc de
        ld a, (de)
        ld l, a
        ld a, (hl)
        ld (de), a
fl_hnext:
        pop de
        ld a, (fl_w)
        add a, a
        add a, e
        ld e, a
        ld a, d
        adc a, 0
        ld d, a   ; следующая строка
        ld a, (fl_hh)
        dec a
        ld (fl_hh), a
        jp nz, fl_hrow
fl_ret:
        pop de
        ret
fl_need:        DB      0   ; биты, которые надо перевернуть (7 = V, 6 = H)
fl_w2:          DB      0   ; V: байт в строке = 2*w
fl_cnt2:        DB      0   ; V: высота, затем счётчик пар строк
fl_w:           DB      0   ; H: ширина в парах
fl_hh:          DB      0   ; H: счётчик строк
fl_cnt:         DB      0   ; H: счётчик обменов в строке
        ; END OF FUNCTION CHUNK FOR flip_sprite
""" % {'rev': REV_TBL}


def apply(src):
    """Замена тел готовым i8080 ПОСЛЕ трансляции."""
    src = _sub(src, r'^flip_sprite:\n.*?^        ; End of function flip_sprite\n',
               N_HEAD, 'тело flip_sprite', flags=re.M | re.S)
    src = _sub(src,
               r'^        ; START OF FUNCTION CHUNK FOR flip_sprite\n'
               r'vflip_sprite_data:\n.*?^        ; END OF FUNCTION CHUNK FOR flip_sprite\n',
               N_BODY, 'чанк vflip_sprite_data', flags=re.M | re.S)
    return src
