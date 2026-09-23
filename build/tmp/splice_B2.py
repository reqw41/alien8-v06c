#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шаг B (часть 2), ПЕРЕПИСАНО после сверки с KL (kl_sound_ay.py:172-456, PORT_RECIPE §16/§20).
Слив зеркала AY в счётчики 1,2 ВИ53: msx_frame_off/msx_silence/msx_viflush/msx_vcalc(+ay2vi)/
msx_vhkill — в дыре за хвостом спрайтов (a8_spr_top..0xF100, 226 Б на ee34cd4; всё целиком —
370 Б — не влезает); msx_viwant/msx_viemit/msx_vhnew — в нижнем регионе за ядром драйвера;
ячейки — в добивке 0x7FC0 (страница 0x7F). tools/a8_sound_ay.py:
  * константы VI_CODE (код дыры), VI_LOW (нижний регион) и VI_STATE (ячейки) после _VI53_STATE;
  * emit(): цель vec — ORG-блоки перед SAVEBIN (состояние плеера 0x7F88, ячейки слива 0x7FC0,
    код a8_spr_top), метка a8_spr_top ставится на конец хвоста спрайтов; цель lockstep —
    всё то же БЕЗ ORG, сразу за данными драйвера (раньше ORG 0x7F88 ложился на КОД
    lockstep-сборки: там 0x7F88 — середина нижнего региона, DS затирал его нулями).
Якоря — текстовые, порядок с splice_B1 любой, каждый — ОДИН раз."""
P = 'tools/a8_sound_ay.py'
src = open(P, encoding='utf-8').read()


def rep(old, new, what):
    global src
    n = src.count(old)
    assert n == 1, (what, n)
    src = src.replace(old, new, 1)


VI = r'''

# ---- слив зеркала AY в ВИ53 (рецепт Knight Lore: kl_sound_ay.py msx_viflush/vcalc/ay2vi/
#      viwant/viemit и отложенная нота msx_vhold, PORT_RECIPE §16 и §20) ----
# Код — в дыре за хвостом спрайтов (a8_spr_top..0xF100): START её не трогает (build_lookup_tbls
# строит 0xF100..0xFFFF), print_sprite страницу 0xF0 не читает (сдвиг 0 обходит таблицы),
# записей туда нет (spillcheck_vec.js, A8SPILL=F000-F0FF A8SPILL_OFF=1E-FF, 128 комнат).
VI_CODE = """
; ================= ЗВУК ЭФФЕКТОВ: зеркало AY -> счётчики 1,2 ВИ53 (рецепт Knight Lore) =================
; Мелодии пишет в счётчики 1,2 напрямую плеер msx_tv (msx_play=1, игра стоит); этот тракт —
; для эффектов: msx_wr копит регистры AY в зеркале msx_ayregs, msx_frame_off в конце игровой
; итерации сливает его в счётчики. Счётчик 0 — секундомер бюджета di, не участвует.
; Каналы: B -> 1, C -> 2; канал A (слот 0: чирп шара, приземление) ворует свободный (сперва 2,
; потом 1); третий одновременный эффект отбрасывается. Делитель = 13P + P/2 (таймер 1497600 Гц
; против AY 1.775M/16). Громкость: порог 6/15, бит огибающей = полный голос. Только шум ->
; падающий тон R6*256. Делитель < 64 -> тишина.
; Порты ПЕРЕСТАВЛЕНЫ против даташита: управление 0x08, счётчик 1 = 0x0A, счётчик 2 = 0x09.
; Управляющее слово ПЕРЕЗАПУСКАЕТ счётчик — только при смене ВЛАДЕЛЬЦА, и тогда кэш делителя
; бьётся в 0xFFFF; тот же делитель не пишется; тишина = управляющее слово БЕЗ делителя.
; Все ячейки — в странице добивки (ASSERT у VI_STATE): адресация `ld h,high / ld l,low+i`.

msx_frame_off:	; конец игровой итерации (MSX 0x41A6): слить зеркало в ВИ53, потом тишина AY.
				; Мелодию не трогаем: её счётчики пишет msx_tv. Регистры вызывателя целы.
				ld		a, (msx_play)
				or		a
				ret		nz
				push	bc
				push	de
				push	hl
				call	msx_viflush
				pop		hl
				pop		de
				pop		bc
msx_silence:	; полная тишина AY — список MSX «стоп» (R7 := 0xBF, громкости 0) прямо в зеркало
				ld		a, 0xBF
				ld		(msx_ayregs + 7), a
				xor		a
				ld		(msx_ayregs + 8), a
				ld		(msx_ayregs + 9), a
				ld		(msx_ayregs + 10), a
				ret

msx_viflush:	; зеркало -> активность/делители трёх каналов -> раскладка -> счётчики 1,2
				ld		c, 0
mvf_l:			call	msx_vcalc
				inc		c
				ld		a, c
				cp		3
				jp		nz, mvf_l
				call	msx_viwant
				ld		c, 1
				call	msx_viemit
				ld		c, 2
				jp		msx_viemit

msx_vcalc:		; C = канал 0..2 (A,B,C) -> msx_vact[C], msx_vdiv[C]. C цел, портит AF,B,DE,HL.
				ld		h, high msx_ayregs
				ld		a, c
				add		a, low (msx_ayregs + 8)
				ld		l, a
				ld		a, (hl)				; R(8+C): 4 бита громкости + бит 4 огибающей (регистр 5-битный)
				cp		6					; порог 6/15; с битом огибающей значение >= 16 — полный голос
				jp		c, mvc_off
				ld		a, (msx_ayregs + 7)
				cpl							; в R7 ноль = включено; после cpl единица = включено
				ld		b, a
				ld		hl, msx_kmask		; 0x09/0x12/0x24 = биты тона и шума канала
				ld		a, l
				add		a, c
				ld		l, a
				ld		a, h
				adc		a, 0				; таблица в нижнем регионе, не выровнена
				ld		h, a
				ld		a, (hl)
				and		b
				jp		z, mvc_off			; ни тона, ни шума
				and		0x07
				jp		z, mvc_noise		; только шум: у ВИ53 шума нет — падающий тон из R6
mvc_tone:		ld		h, high msx_ayregs
				ld		a, c
				add		a, a
				add		a, low msx_ayregs
				ld		l, a
				ld		e, (hl)
				inc		l
				ld		a, (hl)
				and		0x0F				; период тона — 12 бит
				ld		h, a
				ld		l, e				; HL = период AY
msx_ay2vi:		; HL = P -> HL = 13P + P/2 (усечение вниз); P <= 4095 -> <= 55282, переполнения нет
				push	bc
				ld		b, h
				ld		c, l				; BC = P
				add		hl, hl
				ld		e, l
				ld		d, h				; DE = 2P
				add		hl, hl				; 4P
				add		hl, de				; 6P
				add		hl, hl				; 12P
				add		hl, bc				; 13P
				ld		a, b
				or		a					; CY = 0
				rra
				ld		b, a
				ld		a, c
				rra							; бит 0 старшего -> бит 7 младшего: BC = P/2
				ld		c, a
				add		hl, bc				; 13.5P
				pop		bc
				ld		a, h
				or		a
				jp		nz, mvc_on
				ld		a, l
				cp		64					; < 64 = выше 23 кГц: слышать нечего, а счётчик перезапускался бы
				jp		c, mvc_off
				jp		mvc_on
mvc_noise:		ld		a, (msx_ayregs + 6)
				and		0x1F
				jp		nz, mvc_n1
				inc		a					; R6 = 0 -> 1: делитель 256, не ноль
mvc_n1:			ld		h, a
				ld		l, 0				; делитель = R6*256: 5850..188 Гц
mvc_on:			ex		de, hl				; DE = делитель
				ld		h, high msx_vact
				ld		a, c
				add		a, low msx_vact
				ld		l, a
				ld		(hl), 1				; канал активен
				ld		a, c
				add		a, a
				add		a, low msx_vdiv
				ld		l, a
				ld		(hl), e
				inc		l
				ld		(hl), d
				ld		a, c
				add		a, low msx_vhold
				ld		l, a
				ld		(hl), 3				; голос слышали живьём — откладывать его нечего
				ret
; ОТЛОЖЕННАЯ НОТА (KL §20). Эффект MSX в 7..31 тиков при 56 тиках на итерацию обычно
; рождается и гаснет между двумя сливами — слив застал бы его живым только случайно.
; Поэтому msx_sfx_kill, гася слот, оставляет в msx_vhold метку «отзвучал, а его никто не слил»
; (1 тон, 2 шум), и первый же слив выдаёт последнюю ноту эффекта (период ещё в зеркале) на
; одну итерацию. Метка 3 «слышали живьём» (mvc_on) не даёт удлинить уже слышанный эффект.
; Метка обнуляется ДО перехода в mvc_tone/mvc_noise, поэтому отказ по делителю < 64 приходит
; сюда повторно уже с нулём и кончается тишиной.
mvc_off:		ld		h, high msx_vhold
				ld		a, c
				add		a, low msx_vhold
				ld		l, a
				ld		a, (hl)
				ld		(hl), 0
				dec		a
				jp		z, mvc_tone			; 1 — отложен тон
				dec		a
				jp		z, mvc_noise		; 2 — отложен шум (эффект 1)
				ld		a, c
				add		a, low msx_vact
				ld		l, a
				ld		(hl), 0				; канал молчит
				ret

msx_vhkill:		; из msx_sfx_kill: A = id погашенного эффекта, (msx_si) = слот = канал
				ld		b, a
				ld		h, high msx_vhold
				ld		a, (msx_si)
				add		a, low msx_vhold
				ld		l, a
				ld		a, (hl)
				or		a
				ret		nz					; 3 = слышали живьём (или уже отложен) — не удлиняем
				ld		a, b
				cp		1
				ld		(hl), 1				; 1 = отложен тон
				ret		nz
				ld		(hl), 2				; эффект 1 — шум: делитель из R6
				ret
"""

# Не влезло в дыру (226 Б): раскладка счётчиков, выдача в порты и сброс метки — в нижний регион
# (он после снятия msx_wlist/msx_stop/msx_frame_off освободил страницу выравнивания vec_rptab).
VI_LOW = """
; ---- слив AY -> ВИ53, продолжение (начало — VI_CODE в дыре за хвостом спрайтов) ----
msx_viwant:		; msx_viw[1..2] = канал AY на счётчике или 0xFF (счётчик 0 — секундомер, не наш)
				ld		a, (msx_vact + 1)
				or		a
				ld		a, 1
				jp		nz, mvo_b
				ld		a, 0xFF				; канал B молчит — счётчик 1 свободен
mvo_b:			ld		(msx_viw + 1), a
				ld		a, (msx_vact + 2)
				or		a
				ld		a, 2
				jp		nz, mvo_c
				ld		a, 0xFF				; канал C молчит — счётчик 2 свободен
mvo_c:			ld		(msx_viw + 2), a
				ld		a, (msx_vact + 0)	; канал A ищет свободный счётчик
				or		a
				ret		z
				ld		a, (msx_viw + 2)	; сперва счётчик 2
				inc		a
				jp		nz, mvo_1
				ld		(msx_viw + 2), a	; A = 0 = канал A
				ret
mvo_1:			ld		a, (msx_viw + 1)
				inc		a
				ret		nz					; оба заняты — третий одновременный эффект отброшен
				ld		(msx_viw + 1), a
				ret

msx_viemit:		; C = счётчик 1/2: поставить на него канал msx_viw[C]. C цел, портит AF,B,DE,HL.
				ld		a, 0x0B
				sub		c
				ld		(msx_vistub + 1), a	; порт счётчика: 1 -> 0x0A, 2 -> 0x09 (ПЕРЕСТАВЛЕНЫ)
				ld		h, high msx_viw
				ld		a, c
				add		a, low msx_viw
				ld		l, a
				ld		b, (hl)				; B = желаемый канал (0xFF = молчать)
				ld		a, c
				add		a, low msx_viown
				ld		l, a				; HL = &msx_viown[C]
				ld		a, b
				inc		a
				jp		z, mve_off
				ld		a, b
				cp		(hl)
				jp		z, mve_div			; владелец тот же — управляющее слово не слать
				ld		(hl), a
				call	mve_ctrl			; смена владельца: управляющее слово ПЕРЕЗАПУСКАЕТ счётчик...
				ld		a, c
				add		a, a
				add		a, low msx_vidiv
				ld		l, a
				ld		(hl), 0xFF			; ...и бой кэша делителя: запись ниже состоится
				inc		l
				ld		(hl), 0xFF
mve_div:		ld		a, b
				add		a, a
				add		a, low msx_vdiv
				ld		l, a
				ld		e, (hl)
				inc		l
				ld		d, (hl)				; DE = делитель канала
				ld		a, c
				add		a, a
				add		a, low msx_vidiv
				ld		l, a				; HL = &кэш счётчика
				ld		a, (hl)
				cp		e
				jp		nz, mve_w
				inc		l
				ld		a, (hl)
				cp		d
				ret		z					; тот же делитель — не пишем (запись перезапустила бы счётчик)
				dec		l
mve_w:			ld		(hl), e
				inc		l
				ld		(hl), d
				ld		a, e
				call	msx_vistub			; сначала младший байт...
				ld		a, d
				jp		msx_vistub			; ...потом старший (режим LSB+MSB)
mve_off:		ld		a, (hl)
				inc		a
				ret		z					; уже стоит — ничего не слать
				ld		(hl), 0xFF
mve_ctrl:		ld		a, c				; управляющее слово «счётчик C, LSB+MSB, режим 3»
				rrca
				rrca						; 1 -> 0x40, 2 -> 0x80
				add		a, 0x36				; 0x76 / 0xB6; тишина = это слово БЕЗ делителя
				out		(0x08), a
				ret

msx_vhnew:		; из msx_sfx_start: C = слот; новый эффект — метка отложенной ноты сброшена.
				; Портит A,HL (B,C,DE целы — их ждёт msx_sfx_start)
				ld		h, high msx_vhold
				ld		a, c
				add		a, low msx_vhold
				ld		l, a
				ld		(hl), 0
				ret
"""

_VI_ASSERTS = """        ASSERT (msx_ayregs & 0x0F) == 0   ; msx_wr складывает номер регистра с младшим байтом
        ASSERT high msx_ayregs == high ($ - 1)   ; все ячейки слива в одной странице:
                                               ;  адресация `ld h,high / add a,low` без переноса
"""

VI_STATE = """msx_ayregs:		DS		16			; зеркало регистров AY: msx_wr пишет по [C&0x0F], слив читает
msx_viown:		DS		3			; владелец счётчика 0/1/2 (0xFF = счётчик стоит); [0] не используется
msx_vidiv:		DS		6			; кэш делителей счётчиков (lo, hi)
msx_viw:		DS		3			; кого поставить на счётчик в этом сливе; [0] не используется
msx_vact:		DS		3			; канал AY активен в этом сливе
msx_vdiv:		DS		6			; делитель ВИ53 канала (lo, hi)
msx_vhold:		DS		3			; отложенная нота канала: 0 нет, 1 тон, 2 шум, 3 слышали живьём
msx_vistub:		EQU		msx_tv_stub	; «out (порт),a / ret» — общая с плеером мелодий: оба зовутся
								;  из основного потока и друг друга не прерывают
"""
'''

rep('''

def emit(src, target):''', VI + '''

def emit(src, target):''', 'VI_CODE/VI_STATE')

rep('''    src = src.replace(mark, driver(target) + data_block(), 1)
    src, n = re.subn(r'^        SAVEBIN [^\\n]*$', lambda m: _VI53_STATE + m.group(0) + '\\n',
                     src, count=1, flags=re.M)
    if n != 1:
        raise SystemExit('a8_sound_ay: строка SAVEBIN не найдена')
    return src''', '''    if target != 'vec':
        # lockstep: раскладки Вектора нет (0x7F88 там — середина кода, 0xF0xx — zxvram), всё
        # идёт сразу за данными драйвера, без ORG
        flat = '\\n'.join(l for l in _VI53_STATE.split('\\n')
                          if not re.match(r'\\s+(ORG|ASSERT) ', l))
        return src.replace(mark, driver(target) + VI_LOW + data_block() + VI_CODE + flat
                           + '        ALIGN 64                ; 40 Б ячеек слива — в одной странице\\n'
                           + VI_STATE + _VI_ASSERTS, 1)
    src = src.replace(mark, driver(target) + VI_LOW + data_block(), 1)
    # конец хвоста спрайтов (0xE000..): за ним до таблиц 0xF100 — дыра под код слива
    tail = '        ASSERT $ <= 0xf100   ; хвост спрайтов не должен налезть на таблицы сдвига\\n'
    if src.count(tail) != 1:
        raise SystemExit('a8_sound_ay: конец хвоста спрайтов не найден')
    src = src.replace(tail, 'a8_spr_top:     equ $   ; конец хвоста спрайтов: дальше код слива AY -> ВИ53\\n'
                      + tail, 1)
    blk = (_VI53_STATE
           + '        ORG 0x7FC0              ; слив AY -> ВИ53: зеркало регистров и ячейки (добивка)\\n'
           + VI_STATE + _VI_ASSERTS
           + '        ASSERT $ <= 0x8000        ; добивка кончается плоскостью 0\\n'
           + '        ORG a8_spr_top          ; код слива AY -> ВИ53: дыра за хвостом спрайтов\\n'
           + VI_CODE
           + '        ASSERT $ <= 0xF100        ; слив AY -> ВИ53 не должен налезть на таблицы сдвига\\n')
    src, n = re.subn(r'^        SAVEBIN [^\\n]*$', lambda m: blk + m.group(0) + '\\n',
                     src, count=1, flags=re.M)
    if n != 1:
        raise SystemExit('a8_sound_ay: строка SAVEBIN не найдена')
    return src''', 'emit')

open(P, 'w', encoding='utf-8').write(src)
print('splice B2 ok: VI_CODE (дыра a8_spr_top..0xF100) + VI_STATE (0x7FC0) + emit vec/lockstep')
