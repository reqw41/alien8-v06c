#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шаг B (часть 2): msx_viflush/msx_vcalc/msx_ay2vi/msx_viwant/msx_viemit перед
msx_frame_off; состояние — в добивке 0x7FC0.. (заменяет старый ASSERT $ <= 0x7FB8).
Раскладка состояния подобрана так, что все индексы viown+2c, vidiv+2c, viw+c,
vact+c, vdiv+2C не дают переноса из младшего байта (страница 0x7F) — адресация
`ld l,a / ld h,high ...` без adc. Атомарно: ассерты на границы. Номера — по ee34cd4."""
P = 'tools/a8_sound_ay.py'
lines = open(P, encoding='utf-8').read().split('\n')  # 0-based

def find(prefix):  # единственный якорь по тексту — порядок с splice_B1 не важен
    idx = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    assert len(idx) == 1, (prefix, idx)
    return idx[0]

FO_AT = find('msx_frame_off:')
V1_AT = find('msx_tv_v1:')
assert lines[V1_AT + 1].startswith('        ASSERT $ <= 0x7FB8'), lines[V1_AT + 1]

NEW_ROUTINES = r"""; ---- слив зеркала AY в счётчики ВИ53 (рецепт Knight Lore, kl_sound_ay.py:172-456) ----
; Мелодии пишет в счётчики 1,2 напрямую плеер a8_tv; этот тракт — для эффектов:
; msx_wr копит регистры AY в зеркале msx_ayregs, msx_frame_off раз в кадр сливает его
; в счётчики. Каналы: B->1, C->2; канал A (слот 0: чирп шара, приземление) ворует
; свободный (сперва 2, потом 1), третий одновременный эффект отбрасывается. Счётчик 0 —
; секундомер бюджета di, не участвует. Делитель = 13P + P/2 (таймер Вектора 1497600 Гц
; против AY 1.775M/16). Порты ПЕРЕСТАВЛЕНЫ: управление 0x08, счётчик 1 = 0x0A,
; счётчик 2 = 0x09. Управляющее слово — только при смене ВЛАДЕЛЬЦА счётчика (оно
; ПЕРЕЗАПУСКАЕТ счётчик); при смене владельца бить кэш делителя в 0xFFFF (иначе та же
; нота после паузы промолчит — те же грабли, что у a8_tv). vhold (отложенная нота KL)
; не перенесён: эффект короче кадра может не быть застигнут ни одним flush.
msx_viflush:	; раз в кадр из msx_frame_off: зеркало -> активность/делители -> раскладка -> emit
				push	bc
				push	de
				push	hl
				ld		c, 0
mvf_l:			call	msx_vcalc
				inc		c
				ld		a, c
				cp		3
				jp		nz, mvf_l
				call	msx_viwant
				ld		c, 1
mvf_e:			call	msx_viemit
				inc		c
				ld		a, c
				cp		3
				jp		nz, mvf_e
				pop		hl
				pop		de
				pop		bc
				ret

msx_vcalc:		; C = канал 0..2 -> msx_vact[C], msx_vdiv[C] (канал 0 = A, младший)
				ld		a, c
				add		a, 8
				ld		l, a
				ld		h, high msx_ayregs	; зеркало на 16 выровнено, 8+C < 16: переноса нет
				ld		a, (hl)
				and		0x10				; огибающая включена -> громкость считаем максимальной
				jp		nz, mvc_r7
				ld		a, (hl)
				and		0x0F
				cp		6					; порог 6/15: 0..5 — тише слышимого, молчит
				jp		c, mvc_off
mvc_r7:			ld		a, (msx_ayregs + 7)
				cpl							; в R7 ноль = включено; после cpl единица = включено
				ld		b, a
				ld		hl, msx_kmask		; маска канала: бит тона | бит шума (09/12/24)
				ld		a, c
				add		a, l
				ld		l, a
				ld		a, h
				adc		a, 0				; (таблица не выровнена — перенос возможен)
				ld		h, a
				ld		a, (hl)
				and		b
				jp		z, mvc_off			; ни тона, ни шума
				and		0x07
				jp		z, mvc_noise		; только шум: у ВИ53 шума нет — падающий тон из R6
				ld		a, c
				add		a, a
				ld		l, a
				ld		h, high msx_ayregs	; &периода канала: 2C, 2C+1
				ld		a, (hl)
				ld		e, a
				inc		l
				ld		a, (hl)
				and		0x0F				; старший байт периода — 4 бита
				ld		h, a
				ld		l, e				; HL = период AY
				call	msx_ay2vi
				jp		mvc_cmp
mvc_noise:		ld		a, (msx_ayregs + 6)
				and		0x1F
				jp		nz, mvc_n1
				inc		a					; R6=0 -> 1: делитель 256, не ноль
mvc_n1:			ld		h, a
				ld		l, 0					; делитель = R6*256
mvc_cmp:			ld		a, h				; делитель < 64 = выше ~23 кГц: слышно нечего
				or		a
				jp		nz, mvc_on
				ld		a, l
				cp		64
				jp		c, mvc_off
				jp		mvc_on
mvc_on:			ex		de, hl				; DE = делитель
				ld		a, c
				add		a, low msx_vact
				ld		l, a
				ld		h, high msx_vact	; (раскладка добивки: переноса из младшего нет)
				ld		(hl), 1				; канал активен
				ld		a, c
				add		a, a
				add		a, low msx_vdiv
				ld		l, a
				ld		h, high msx_vdiv
				ld		(hl), e				; делитель: младший
				inc		hl
				ld		(hl), d				; ...старший
				ret
mvc_off:			ld		a, c
				add		a, low msx_vact
				ld		l, a
				ld		h, high msx_vact
				ld		(hl), 0
				ret

msx_ay2vi:		; HL = период AY (12 бит) -> HL = 13P + P/2 (усечение вниз)
				push	bc
				push	de
				ld		b, h
				ld		c, l				; BC = P
				add		hl, hl				; 2P
				ld		e, l
				ld		d, h				; DE = 2P
				add		hl, hl				; 4P
				add		hl, de				; 6P
				add		hl, hl				; 12P
				add		hl, bc				; 13P
				or		a					; CY=0: сдвигаем P как 16-битное
				ld		a, b
				rra
				ld		b, a
				ld		a, c
				rra							; бит0(b) пришёл в бит7(c): BC = floor(P/2)
				ld		c, a
				add		hl, bc				; 13.5P
				pop		de
				pop		bc
				ret

msx_viwant:		; msx_viw[счётчик] = чей канал на нём играет (0xFF = счётчик свободен)
				ld		a, 0xFF
				ld		(msx_viw + 0), a	; счётчик 0 — секундомер бюджета di, не для каналов
				ld		a, (msx_vact + 1)
				or		a
				ld		a, 1
				jp		nz, mvo_b1
				ld		a, 0xFF				; канал B молчит — счётчик 1 свободен
mvo_b1:			ld		(msx_viw + 1), a
				ld		a, (msx_vact + 2)
				or		a
				ld		a, 2
				jp		nz, mvo_c1
				ld		a, 0xFF				; канал C молчит — счётчик 2 свободен
mvo_c1:			ld		(msx_viw + 2), a
				ld		a, (msx_vact + 0)	; канал A (слот 0) ищет свободный счётчик
				or		a
				ret		z
				ld		a, (msx_viw + 2)
				inc		a
				jp		nz, mvo_try1
				xor		a
				ld		(msx_viw + 2), a	; сперва счётчик 2: шаги обычно звучат на C
				ret
mvo_try1:			ld		a, (msx_viw + 1)
				inc		a
				ret		nz					; оба заняты — третий одновременный эффект отброшен
				xor		a
				ld		(msx_viw + 1), a
				ret

msx_viemit:		; C = счётчик 1/2: выставить на нём канал msx_viw[C] (0xFF = тишина)
				ld		a, 0x0B
				sub		c
				ld		(msx_vistub + 1), a	; порт счётчика: 1 -> 0x0A, 2 -> 0x09 (переставлены!)
				ld		a, c
				add		a, low msx_viw
				ld		l, a
				ld		h, high msx_viw
				ld		a, (hl)				; желаемый канал
				inc		a
				jp		z, mve_off
				dec		a
				ld		(msx_vich), a
				ld		a, c
				add		a, low msx_viown
				ld		l, a
				ld		h, high msx_viown
				ld		a, (msx_vich)		; &msx_viown[счётчик]
				cp		(hl)
				jp		z, mve_div			; владелец тот же — управляющее слово не слать
				ld		(hl), a
				push	hl
				call	mve_ctrl			; смена владельца: управляющее слово ПЕРЕЗАПУСКАЕТ счётчик
				pop		hl
				ld		a, 0xFF				; бой кэша делителя: &vidiv[c] = &viown[c] + 3
				inc		hl					; (массивы идут подряд: 3+2c+3 = 2c' + high)
				ld		(hl), a
				inc		hl
				ld		(hl), a
				jp		mve_div				; кэш 0xFFFF != любой делитель -> запись состоится
mve_ctrl:		ld		a, c				; управляющее слово «режим 3, LSB+MSB» счётчика C
				rrca
				rrca						; 1 -> 0x40, 2 -> 0x80
				and		0xC0
				add		a, 0x36				; 0x76 / 0xB6
				out		(0x08), a
				ret
mve_off:			ld		a, c
				add		a, low msx_viown
				ld		l, a
				ld		h, high msx_viown
				ld		a, (hl)
				inc		a
				ret		z					; счётчик уже остановлен — ничего не слать
				ld		(hl), 0xFF
				push	hl
				call	mve_ctrl			; тишина = управляющее слово БЕЗ делителя: счётчик встал
				pop		hl
				ret
mve_div:			ld		a, (msx_vich)		; делитель канала против кэша счётчика
				add		a, a
				add		a, low msx_vdiv
				ld		l, a
				ld		h, high msx_vdiv
				ld		b, (hl)				; B = младший байт делителя
				inc		hl
				ld		a, (hl)				; A = старший байт
				ld		(msx_vich + 1), a	; временный склад старшего (HL будет перезанят)
				ld		a, c
				add		a, a
				add		a, low msx_vidiv
				ld		l, a
				ld		h, high msx_vidiv	; HL = &кэш.младший
				ld		a, b
				cp		(hl)				; тот же младший?
				jp		nz, mve_w
				inc		hl
				ld		a, (msx_vich + 1)
				cp		(hl)				; тот же старший?
				ret		z					; тот же делитель — не пишем (запись перезапустила бы счётчик)
				dec		hl					; HL = &кэш.младший
mve_w:			ld		(hl), b				; кэш.младший = новый
				inc		hl
				ld		a, (msx_vich + 1)
				ld		(hl), a				; кэш.старший = новый
				ld		a, b
				call	msx_vistub			; в порт: сначала младший байт
				ld		a, (msx_vich + 1)	; ...старший (хвостовой вызов: загрузка по MSB)
				jp		msx_vistub""".split('\n')

STATE = r"""        ORG 0x7FC0              ; слив AY -> ВИ53: зеркало регистров и состояние msx_viflush
; (0x7FB8 не выровнено на 16, зеркалу нужно: 8 Б простора; все индексы ниже
;  viown+2c, vidiv+2c, viw+c, vact+c, vdiv+2C НЕ дают переноса из младшего байта)
msx_ayregs:		DS		16			; зеркало AY: msx_wr пишет по [C&0x0F], msx_viflush читает
msx_viown:		DS		3				; кто занимает счётчик 0/1/2 (0xFF = остановлен)
msx_vidiv:		DS		6				; кэш делителей счётчиков (младший+старший на счётчик)
msx_viw:			DS		3				; кого хотим поставить на счётчик (viwant)
msx_vact:			DS		3				; канал активен (vcalc)
msx_vdiv:			DS		6				; делитель канала (vcalc)
msx_vistub:		DS		3				; «out (порт),a / ret» — у i8080 нет out (c)
msx_vich:			DS		2				; текущий канал в msx_viemit + склад старшего байта
        ASSERT $ <= 0x7FF6   ; добивка: 0x7FC0.. занято 54 Б, остаток 10 Б до 0x8000""".split('\n')

lines[V1_AT + 1:V1_AT + 2] = STATE
lines[FO_AT:FO_AT] = NEW_ROUTINES

open(P, 'w', encoding='utf-8').write('\n'.join(lines))
print('splice B2 ok: +5 процедур перед msx_frame_off, состояние 0x7FC0..0x7FF5')
