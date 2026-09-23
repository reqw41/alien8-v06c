#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Звук Alien 8 на AY-3-8910 Вектора-06Ц: перенос драйвера MSX-версии.

Заменяет весь ZX-путь (бипер `out (0xFE)`):
  * мелодии — проигрыватель MSX (0x45B6..0x4752), БЛОКИРУЮЩИЙ, как в оригинале: один тик =
    один видеокадр, за кадр отматывается MSX_PASSES «проходов» главного цикла MSX;
  * эффекты — движок MSX (0x439D..0x45B5), тик из объектного цикла: MSX_TICKS раз за
    игровую итерацию (у MSX объектов ровно 56 и тик стоит в цикле по объектам, а у нас
    цикл ходит только до a8_nobj — 16..48 занятых записей, поэтому остаток тиков
    добирается одним циклом на выходе из объектного цикла, см. msx_sfx_rest);
  * данные — src/msx_tunes.bin (650 байт, извлечены из картриджа MSX моделью
    ~/projects/alien8-research/msx/msx_psg_model.py); формат ноты тот же, что на ZX;
    таблица периодов взята КАК ЕСТЬ (AY Вектора 1.775 МГц против 1.789772 МГц MSX ->
    все ноты ниже ровно на 14.35 цента, строй сохраняется; пересчёт дал бы ошибку
    округления до 10 центов, то есть хуже).

Железо: `out (0x15)` — номер регистра AY, `out (0x14)` — данные. ВИ53 не используется
(в отличие от Knight Lore: там AY могло не быть, здесь звук идёт прямо на AY).

Разбор оригинала: ~/projects/alien8-research/msx/SOUND.md и SFX_SITES.md.
"""
import os
import re
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
TUNES = os.path.join(HERE, '..', 'src', 'msx_tunes.bin')
VI53 = os.path.join(HERE, '..', 'src', 'msx_tunes_vi53.bin')

# карта src/msx_tunes.bin (msx_psg_model.py export)
O_PERIODS = 0x0000   # 128 байт: периоды нот 0..63 (0..7 — слова таблицы команд MSX,
                     #            их пишет «пустой» канал-заглушка с громкостью 0)
O_STEPS = 0x0080     # 16 байт: ноты эффекта «шаги»
O_INIT = 0x0090      # 13 байт: список PSG перед мелодией
O_STOP = 0x009D      # 9 байт: полная тишина
O_ENV = 0x00A6       # 3 байта: R13 := 0
O_HEADERS = 0x00A9   # 36 байт: 6 заголовков по 3 слова (смещения в пуле потоков)
O_STREAMS = 0x00CD   # 445 байт: пул потоков нот (MSX 0x4784..0x4940)
SIZE = 650

TUNE_NAMES = ['start_game', 'game_over', 'game_complete', 'menu', 'obj_5C', 'blip']

# Темп проигрывателя: «проходов» главного цикла MSX за видеокадр 50 Гц.
# Живой замер на headless WebMSX, см. SOUND.md §2.4.
MSX_PASSES = 114

# Тиков эффектов за игровую итерацию: у MSX объектный цикл 0xDA00..0xE100 шаг 0x20 = 56.
MSX_TICKS = 56


def _db(name, data, comment=''):
    out = []
    head = name + ':'
    pad = '\t' * max(1, 4 - len(head) // 4)
    for i in range(0, len(data), 16):
        chunk = ', '.join('0x%02X' % b for b in data[i:i + 16])
        if i == 0:
            out.append('%s%sDB\t%s%s' % (head, pad, chunk, ('\t; ' + comment) if comment else ''))
        else:
            out.append('\t\t\t\tDB\t' + chunk)
    return '\n'.join(out) + '\n'


def data_block():
    """Данные драйвера как asm-текст (читаются из src/msx_tunes.bin, а не хранятся в коде)."""
    with open(TUNES, 'rb') as f:
        d = f.read()
    assert len(d) == SIZE, 'msx_tunes.bin: ожидалось %d байт, получено %d' % (SIZE, len(d))
    per = [d[O_PERIODS + 2 * i] | (d[O_PERIODS + 2 * i + 1] << 8) for i in range(64)]
    stp = d[O_STEPS:O_STEPS + 16]
    txt = '\n; ---- данные звука (извлечены из картриджа MSX, src/msx_tunes.bin) ----\n'
    # real-time проигрыватель мелодий MSX снят (мелодии — готовые потоки ВИ53, см. ниже);
    # от данных мелодий (msx_per/msx_steptb/msx_init/msx_env/msx_headers/msx_stream)
    # осталась только двойная выборка эффекта 3 — одна слитая таблица периодов «шагов»
    txt += _db('msx_step_per', b''.join(struct.pack('<H', per[stp[i]]) for i in range(16)),
               'эффект «шаги»: период = msx_per[msx_steptb[i]], индекс = msx_stepc AND 0x0F')
    txt += _db('msx_kmask', [0x09, 0x12, 0x24], 'биты тона+шума слота 0/1/2 в тени R7')
    txt += """msx_e9a:		DB	0x10, 0x18, 0x20, 0x28, 0xFF	; список периодов эффекта 9 (MSX 0x456F)
				DW	msx_e9a
msx_e9b:		DB	0x60, 0x44, 0x30, 0x38, 0xFF	; вариант B (MSX 0x457A)
				DW	msx_e9b

; ---- переменные драйвера (41 байт) ----
msx_mix:		DS		1			; тень регистра 7 (микшер), как 0xD810 на MSX
msx_stepc:		DS		1			; счётчик шагов (индекс в msx_steptb), как 0xD811
msx_si:			DS		1			; текущий слот эффекта 0..2
msx_play:		DS		1			; 1 = мелодия играет
msx_busy:		DS		1			; 1 = хотя бы один слот эффекта занят (быстрый пропуск тика)
msx_sfx:		DS		12			; 3 слота по 4 байта: id, тиков, параметр_hi, параметр_lo
"""
    txt += '\n; ---- мелодии: готовые потоки ВИ53 (src/msx_tunes_vi53.bin, tools/a8_tunes_msx.py) ----\n'
    with open(VI53, 'rb') as f:
        v = f.read()
    assert len(v) == 847, 'msx_tunes_vi53.bin: ожидалось 847 байт (сначала tools/a8_tunes_msx.py)'
    txt += _db('msx_cat', v, 'каталог + 6 блобов в формате a8_tune_c64 (голос C всегда пуст)')
    txt += _db('msx_catidx', bytes(range(6)), 'байт для DE: адрес msx_hdr_* передаётся в play_audio')
    for i, nm in enumerate(TUNE_NAMES):
        txt += 'msx_hdr_%s:\t\t\tEQU\tmsx_catidx+%d\n' % (nm, i)
    return txt


# ============================================================================
#  Ядро драйвера. Пишется в подмножестве i8080: только jp/call/ret, без jr/djnz/ix/
#  exx/bit/ldir/add hl,hl после установки флагов и т.п. (стережёт tools/check_i8080.py).
# ============================================================================
DRIVER = ("""
; ================= ЗВУК: драйвер MSX-версии Alien 8 на AY Вектора =================
; Мелодии: блокирующие, как на MSX (там проигрыватель — свободный цикл 0x45EA, игра стоит).
;   Один тик = один видеокадр (ei/halt), за кадр отматывается %(passes)d «проходов» MSX.
;   Счётчик длительности 16-битный, остаток проходов переходит в следующий кадр, поэтому
;   суммарный темп совпадает с MSX без накопления ошибки.
;   Ждать конца ОБЯЗАТЕЛЬНО: под `di` в print_sprite Вектор теряет кадровые прерывания
;   (они не защёлкиваются), и мелодия поверх игрового цикла отставала бы.
; Эффекты: тик из объектного цикла. У MSX объектов ровно 56 и тик стоит в цикле по объектам
;   (0x4132), у нас цикл ходит только до a8_nobj (16..48 занятых записей), поэтому недостающие
;   %(ticks)d - a8_nobj тиков добираются на выходе из цикла (msx_sfx_rest) — иначе длительности
;   эффектов (7..31 тик) поплыли бы по комнатам в 3.5 раза.

msx_wr:			; C = регистр AY, B = значение -> ЗЕРКАЛО msx_ayregs (AY на Векторе может не быть;
				;  звучит ВИ53: раз в итерацию зеркало сливает msx_viflush). HL/DE/BC целы.
				push	hl
				ld		a, c
				and		0x0F
				add		a, low msx_ayregs	; зеркало выровнено на 16 (ASSERT): переноса нет
				ld		l, a
				ld		h, high msx_ayregs
				ld		(hl), b
				pop		hl
				ret

msx_snd_init:	; из vec_boot: слоты пусты, мелодии нет, звук молчит
				ld		a, 0xD3					; заготовка «out (порт), a» — порт правит msx_tv_out
				ld		(msx_tv_stub), a
				ld		a, 0xC9					; ret на +2: у i8080 нет out (c)
				ld		(msx_tv_stub + 2), a
				call	msx_tv_mute				; счётчики 1,2 стоят, владельцев нет (0xFF)
				xor		a
				ld		(msx_play), a
				ld		(msx_stepc), a
				ld		(msx_busy), a
				ld		(msx_vhold + 0), a		; отложенных нот нет
				ld		(msx_vhold + 1), a
				ld		(msx_vhold + 2), a
				ld		hl, msx_sfx
				ld		b, 12					; слоты эффектов
msi_l:			ld		(hl), 0
				inc		hl
				dec		b
				jp		nz, msi_l
				ld		a, 0xBF
				ld		(msx_mix), a
				jp		msx_silence				; зеркало: полная тишина (дыра F01E)

; ---------------------------------------------------------------- мелодии
; Мелодии играются из src/msx_tunes_vi53.bin (tools/a8_tunes_msx.py): каталог
; (+0 u16 N=6; далее 6 записей: u16 смещение блоба, u16 длина в кадрах) и блобы в
; формате a8_tune_c64 (Re-Pair; голос C всегда пуст). Real-time пересчёт MSX снят:
; тот же плеер a8_tv, что у заставки (tools/a8_vec.py, fc3c9d9), но два голоса и
; конечная длина: голос A -> счётчик 1 (порт 0x0A), голос B -> счётчик 2 (порт 0x09);
; счётчик 0 — секундомер бюджета di, вектор 0x0038 не подменяем (голос C пуст).
; Играем РОВНО «длину в кадрах» тиков, потом глушим счётчики 1,2 (управляющее слово
; БЕЗ делителя). Запись голоса (шаг 16): +0/+1 pc, +2/+3 start, +4 res, +5 snd,
; +6 depth, +7..+14 стек возвратов (depth <= 4 по построению данных, проверка —
; в tools/a8_tunes_msx.py). Приёмы с заставки: управляющее слово ПЕРЕЗАПУСКАЕТ
; счётчик, поэтому шлём его на смене ноты и на переходе звук->тишина не шлём
; вовсе; тишина = управляющее слово БЕЗ делителя; при возврате из правила кэш snd
; бить в 0xFF, иначе повтор той же ноты после паузы промолчит.

msx_play_tune:	; HL = указатель на байт каталога (msx_catidx): зарядить голоса из блоба
				ld		a, (hl)
				ld		(msx_tunenum), a		; номер мелодии — для TUNE-строки журнала
				ld		l, a
				ld		h, 0
				add		hl, hl
				add		hl, hl					; 4*idx: запись +0/+1 смещение блоба, +2/+3 длина
				ld		de, msx_cat + 2
				add		hl, de					; idx < 6, переноса из младшего байта нет
				ld		c, (hl)					; BC = смещение блоба
				inc		hl
				ld		b, (hl)
				inc		hl
				ld		a, (hl)					; длина в кадрах, младший байт
				inc		hl
				ld		h, (hl)					; старший
				ld		l, a
				ld		a, l
				ld		(msx_tv_rem), a			; i8080: 16-битных ld (nnnn),hl нет — по байтам
				ld		a, h
				ld		(msx_tv_rem + 1), a
				ld		hl, msx_cat
				add		hl, bc					; база блоба; нижний регион — переноса нет
				ld		a, l
				ld		(msx_tv_base), a
				ld		a, h
				ld		(msx_tv_base + 1), a
				; divs = база + 10 + 2nr (nr = слово по +6); база — ЗНАЧЕНИЕ в ячейке,
				; поэтому сначала грузим её в HL, потом прибавляем 6 (как a8_tune_init у заставки,
				; где база была константой a8_tune)
				ld		a, (msx_tv_base)
				ld		l, a
				ld		a, (msx_tv_base + 1)
				ld		h, a
				ld		de, 6
				add		hl, de					; -> &числа правил nr
				ld		c, (hl)
				inc		hl
				ld		b, (hl)					; BC = число правил nr
				ld		a, (msx_tv_base)
				ld		l, a
				ld		a, (msx_tv_base + 1)
				ld		h, a					; HL = база блоба
				add		hl, bc
				add		hl, bc					; база + 2nr
				ld		de, 10
				add		hl, de					; -> таблица делителей
				ld		a, l
				ld		(msx_tv_divs), a
				ld		a, h
				ld		(msx_tv_divs + 1), a
				; голоса: pc = start = база + слово(база + 2*голос); res/snd/depth = 0
				ld		a, (msx_tv_base)
				ld		c, a
				ld		a, (msx_tv_base + 1)
				ld		b, a					; BC = база (и для чтения, и для сложения)
				ld		a, (bc)					; начало голоса A (смещение от базы)
				ld		e, a
				inc		bc
				ld		a, (bc)
				ld		d, a					; DE = смещение
				ld		a, (msx_tv_base)
				ld		c, a
				ld		a, (msx_tv_base + 1)
				ld		b, a					; BC = база (перечитать: bc был сдвинут)
				ld		a, e
				add		a, c
				ld		e, a					; база + смещение, младший байт
				ld		a, d
				adc		a, b					; старший, с переносом (ld флаги не портят)
				ld		d,a					; старший байт АБСОЛЮТНОГО адреса = результат adc (в D лежало смещение)
				ld		hl, msx_tv_v0
				ld		(hl), e
				inc		hl
				ld		(hl), d					; pc
				inc		hl
				ld		(hl), e
				inc		hl
				ld		(hl), d					; start — чтобы 0xFF верхнем уровне начал голос сначала
				xor		a
				ld		(msx_tv_v0 + 4), a		; res = 0: первый тик берёт токен
				ld		(msx_tv_v0 + 5), a		; snd = 0: счётчик 1 молчит
				ld		(msx_tv_v0 + 6), a		; depth = 0
				ld		a, (msx_tv_base)
				ld		c, a
				ld		a, (msx_tv_base + 1)
				ld		b, a
				inc		bc
				inc		bc						; BC = база + 2 (адрес чтения голоса B)
				ld		a, (bc)
				ld		e, a
				inc		bc
				ld		a, (bc)
				ld		d, a					; DE = смещение голоса B
				ld		a, (msx_tv_base)
				ld		c, a
				ld		a, (msx_tv_base + 1)
				ld		b, a					; BC = база (для сложения)
				ld		a, e
				add		a, c
				ld		e, a
				ld		a, d
				adc		a, b
				ld		d,a					; тот же старший байт для голоса B
				ld		hl, msx_tv_v0 + 16
				ld		(hl), e
				inc		hl
				ld		(hl), d
				inc		hl
				ld		(hl), e
				inc		hl
				ld		(hl), d
				xor		a
				ld		(msx_tv_v0 + 16 + 4), a
				ld		(msx_tv_v0 + 16 + 5), a
				ld		(msx_tv_v0 + 16 + 6), a
				call	msx_tv_mute				; заглушить счётчики 1,2 (с эффектов мог остаться тон)
												;  и бросить их владельцев: плеер пишет счётчики
												;  мимо msx_viown/msx_vidiv
				ld		a, 1
				ld		(msx_play), a			; мелодия играет: msx_sfx_start отказывает (как на MSX);
				ret								;   на эту запись вешается TUNE-метка журнала

msx_stop_tune:	xor		a
				ld		(msx_play), a
				ld		(msx_tv_rem), a
				ld		(msx_tv_rem + 1), a
				jp		msx_tv_mute

; тик — ровно один за кадр (зовёт msx_frame). Портит AF,BC,DE,HL.
msx_tv_tick:			ld		hl, msx_tv_rem
				ld		a, (hl)					; младший rem: заём НУЖЕН, но только когда lo==0
				or		a
				jp		nz, mtt_lo			; lo>0: займа нет (в т.ч. lo=1 -> 0)
				dec		(hl)					; lo 0 -> FF
				inc		hl
				dec		(hl)					; заём у hi (rem > 0 до тика, значит hi > 0)
				dec		hl
				jp		mtt_a
mtt_lo:			dec		(hl)					; lo 1 -> 0 — старший НЕ трогаем
mtt_a:			ld		a, (msx_tv_rem)
				ld		b, a
				ld		a, (msx_tv_rem + 1)
				or		b
				push	af						; Z = этот тик последний (длина в кадрах кончилась)
				ld		a, 1
				ld		(msx_tv_c), a			; голос A -> счётчик 1 (порт 0x0A)
				ld		hl, msx_tv_v0
				call	msx_tv
				ld		a, 2
				ld		(msx_tv_c), a			; голос B -> счётчик 2 (порт 0x09)
				ld		hl, msx_tv_v0 + 16
				call	msx_tv
				pop		af
				ret		nz
				xor		a
				ld		(msx_play), a			; «длина в кадрах» сыграна
				jp		msx_tv_mute			; заглушить счётчики 1,2

msx_tv_mute:			ld		a, 0x76					; управляющее слово БЕЗ делителя: счётчик 1 встал
				out		(0x08), a
				ld		a, 0xB6					; ...и счётчик 2
				out		(0x08), a
				ld		a, 0xFF					; счётчики встали — владельцев у них нет: первый же
				ld		(msx_viown + 1), a		;  эффект получит управляющее слово и бой кэша
				ld		(msx_viown + 2), a		;  делителя (иначе нота «совпала бы с кэшем» и промолчала)
				ret

; голос: HL = запись состояния, (msx_tv_c) = номер счётчика 1/2. Портит AF,DE,HL.
msx_tv:					ld		(msx_tv_stp), hl
				ld		a, l
				add		a, 4
				ld		l, a
				ld		a, (hl)					; res
				or		a
				jp		nz, msx_tv_dec
msx_tv_tok:			ld		hl, (msx_tv_stp)
				ld		e, (hl)
				inc		hl
				ld		d, (hl)					; DE = pc
				ld		a, (de)					; токен
				cp		0xFF
				jp		z, msx_tv_ret
				or		a
				jp		p, msx_tv_note		; 0x00..0x7E нота; 0x80..0xFE вызов правила (всегда два байта)
				ld		b, a
				inc		de
				ld		a, (de)					; k = ((b and 0x7F) << 8) | следующий байт
				ld		l, a
				ld		a, b
				and		0x7F
				ld		h, a
				inc		de						; DE = адрес возврата pc+2
				push	hl
				ld		hl, (msx_tv_stp)
				ld		a, l
				add		a, 6
				ld		l, a						; &depth
				inc		(hl)						; глубина <= 4 по построению данных
				ld		a, (hl)
				add		a, a
				ld		b, a
				ld		a, l
				add		a, b
				sub		1						; &слота возврата = база+5+2depth (hl уже = база+6)
				ld		l, a
				ld		(hl), e
				inc		hl
				ld		(hl), d
				pop		hl						; HL = k
				add		hl, hl					; 2k
				ld		de, 8
				add		hl, de					; -> слово(база + 8 + 2k): адрес правила
				ld		a, (msx_tv_base)
				ld		c, a
				ld		a, (msx_tv_base + 1)
				ld		b, a						; BC = база блоба
				add		hl, bc
				ld		e, (hl)
				inc		hl
				ld		d, (hl)					; DE = смещение правила
				ld		l, e
				ld		h, d
				ld		a, (msx_tv_base)
				ld		c, a
				ld		a, (msx_tv_base + 1)
				ld		b, a						; BC = база блоба
				add		hl, bc					; HL = адрес правила
				ex		de, hl					; DE = адрес правила (i8080 EX DE,HL)
				ld		hl, (msx_tv_stp)
				ld		(hl), e
				inc		hl
				ld		(hl), d					; pc = правило, кадр не потрачен — за токеном снова
				jp		msx_tv_tok
msx_tv_dec:			dec		a
				ld		(hl), a					; res--
				ret
msx_tv_ret:			ld		hl, (msx_tv_stp)
				ld		a, l
				add		a, 6
				ld		l, a						; &depth
				ld		a, (hl)
				or		a
				jp		z, msx_tv_top
				add		a, a						; +5+2depth = &слота последнего возврата
				ld		b, a
				ld		a, (hl)
				dec		a
				ld		(hl), a					; depth--
				ld		a, l
				add		a, b
				sub		1						; &слота возврата = база+5+2depth
				ld		l, a
				ld		e, (hl)
				inc		hl
				ld		d, (hl)					; DE = адрес возврата
				ld		hl, (msx_tv_stp)
				ld		(hl), e
				inc		hl
				ld		(hl), d					; pc = адрес возврата
				ld		a, l
				add		a, 4
				ld		l, a						; &snd
				ld		(hl), 0xFF			; при возврате бить кэш: нота после паузы обязана
												; получить своё управляющее слово
				jp		msx_tv_tok
msx_tv_top:			ld		a, l				; верхний уровень: 0xFF = начать голос сначала
				sub		1
				ld		l, a						; &snd
				ld		(hl), 0xFF				; кэш тоже выбит
				ld		a, l
				sub		3
				ld		l, a						; &start (младший байт)
				ld		e, (hl)
				inc		hl
				ld		d, (hl)
				ld		a, l
				sub		3
				ld		l, a						; &pc
				ld		(hl), e
				inc		l
				ld		(hl), d
				jp		msx_tv_tok
msx_tv_note:			ld		b, a				; A = индекс делителя (0x00..0x7E), DE = pc
				inc		de
				ld		a, (de)					; длина в кадрах 1..255
				ld		(msx_tv_len), a
				ld		a, b
				ld		l, a
				ld		h, 0
				add		hl, hl
				ld		a, (msx_tv_divs)		; i8080: 16-битная загрузка из памяти — по байтам
				ld		c, a
				ld		a, (msx_tv_divs + 1)
				ld		b, a
				add		hl, bc					; &делителя
				ld		a, (hl)
				ld		(msx_tv_div), a		; делитель lo -> в ячейку
				inc		hl
				ld		a, (hl)
				ld		(msx_tv_div + 1), a	; делитель hi
				ld		hl, (msx_tv_stp)		; pc += 2: загрузка байта из памяти сбрасывает перенос,
				ld		a, (hl)
				add		a, 2
				ld		e, a						; E = lo+2
				inc		hl
				ld		a, (hl)					; hi
				ld		c, a
				ld		a, e
				sub		2						; заём = (lo+2 < 2) = тот самый перенос
				ld		a, c
				adc		a, 0					; hi + перенос
				ld		(hl), a
				dec		hl
				ld		a, e
				ld		(hl), a					; pc += 2 готов
				inc		hl
				ld		a, l
				add		a, 3
				ld		l, a						; &res
				ld		a, (msx_tv_len)
				sub		1						; кадр взятия ноты уже потрачен (как в decode): res = длина-1
				ld		(hl), a					; res
				inc		hl						; &snd
				ld		a, (msx_tv_div)
				ld		e, a
				ld		a, (msx_tv_div + 1)
				ld		d, a
				or		e						; делитель == 0 -> тишина
				jp		nz, msx_tv_on
				ld		a, (hl)
				or		a
				jp		z, msx_tv_rtn			; и так молчит — порты не трогать
				ld		(hl), 0
				jp		msx_tv_ctrlw			; тишина = управляющее слово БЕЗ делителя (счётчик встаёт)
msx_tv_on:			ld		(hl), 1
				call	msx_tv_ctrlw			; смена ноты: управляющее слово ПЕРЕЗАПУСКАЕТ счётчик
				ld		a, e
				call	msx_tv_out			; делитель: сначала младший байт
				ld		a, d
				jp		msx_tv_out
msx_tv_rtn:			ret
msx_tv_ctrlw:			ld		a, (msx_tv_c)	; управляющее слово счётчика: режим 3 меандр, LSB+MSB
				rrca
				rrca							; 1 -> 0x40, 2 -> 0x80
				and		0xC0
				add		a, 0x36				; 0x76 / 0xB6
				out		(0x08), a
				ret
msx_tv_out:			ld		b, a				; байт делителя в порт счётчика (порт = 0x0B - C)
				ld		a, (msx_tv_c)
				ld		c, a
				ld		a, 0x0B
				sub		c
				ld		(msx_tv_stub + 1), a
				ld		a, b
				jp		msx_tv_stub

msx_frame:		; один видеокадр мелодии: ждём обратного хода, затем один тик обоих голосов
%(wait)s
				call	msx_tv_tick
				ret

msx_wper:		; C = младший регистр тона, DE = период
				ld		b, e
				push	de
				push	bc
				call	msx_wr
				pop		bc
				pop		de
				inc		c
				ld		b, d
				jp		msx_wr

; ---------------------------------------------------------------- эффекты
msx_sfx_tick:	; один вызов MSX 0x43B0: обойти три слота. Зовётся из объектного цикла.
				ld		a, (msx_sfx)
				or		a
				jp		z, mst_1
				xor		a
				ld		(msx_si), a
				call	msx_sfx_run
mst_1:			ld		a, (msx_sfx+4)
				or		a
				jp		z, mst_2
				ld		a, 1
				ld		(msx_si), a
				call	msx_sfx_run
mst_2:			ld		a, (msx_sfx+8)
				or		a
				jp		z, mst_3
				ld		a, 2
				ld		(msx_si), a
				call	msx_sfx_run
mst_3:			ld		a, (msx_sfx)		; все три слота пусты -> снять флаг занятости
				ld		hl, msx_sfx+4
				or		(hl)
				ld		hl, msx_sfx+8
				or		(hl)
				ret		nz
				ld		(msx_busy), a
				ret

msx_sfx_rest:	; выход из объектного цикла: добрать тики до %(ticks)d за итерацию.
				; Цикл по объектам ходит до a8_nobj (16..48 из 56), а у MSX он всегда 56.
				ld		a, (msx_busy)
				or		a
				ret		z
				ld		a, (a8_nobj)
				ld		b, a
				ld		a, %(ticks)d
				sub		b
				ret		z
				ret		c					; занятых записей больше 56 быть не может, но пусть
				ld		b, a
msr_l:			push	bc
				call	msx_sfx_tick
				pop		bc
				dec		b
				jp		nz, msr_l
				ret

msx_sfx_run:	; (msx_si) = слот, слот занят
				ld		a, (msx_si)
				add		a, a
				add		a, a
				ld		l, a
				ld		h, 0
				ld		de, msx_sfx
				add		hl, de				; HL -> слот
				ld		a, (hl)
				cp		6
				ret		z					; id 6: диспетчер MSX ведёт на ret — ни тона, ни декремента
				cp		1
				jp		z, msr_noise
				push	af
				call	msx_tone_on
				jp		msr_cnt
msr_noise:		push	af
				call	msx_noise_on
msr_cnt:		inc		hl
				ld		a, (hl)
				dec		a
				ld		(hl), a
				dec		hl
				jp		nz, msr_go
				pop		af
				jp		msx_sfx_kill
msr_go:			ld		b, a				; B = счётчик после декремента
				pop		af					; A = id эффекта
				cp		1
				jp		z, mse1
				cp		2
				jp		z, mse2
				cp		3
				jp		z, mse3
				cp		4
				jp		z, mse4
				cp		5
				jp		z, mse5
				cp		7
				jp		z, mse7
				cp		8
				jp		z, mse8
				cp		9
				jp		z, mse9
				ret

mse1:			; шум с затуханием: громкость c/2, период шума растёт 1..30
				ld		a, b
				or		a
				rra
				push	bc
				call	msx_setvol
				pop		bc
				ld		a, b
				cpl
				and		0x1F
				ld		b, a
				ld		c, 6
				jp		msx_wr
mse2:			; нисходящий чирп 0x100 + rlca(c)
				ld		a, b
				rlca
				ld		e, a
				ld		d, 1
				call	msx_setper
				ld		a, 0x0F
				jp		msx_setvol
mse3:			; ШАГИ: громкость от координат игрока, нота — из циклической таблицы 16 нот
				ld		a, (graphic_objs_tbl+1)
				or		a
				rra
				ld		c, a
				ld		a, (graphic_objs_tbl+2)
				cpl
				inc		a					; neg
				or		a
				rra
				add		a, c
				rrca
				rrca
				rrca
				rrca
				rrca
				and		7
				add		a, 8
				call	msx_setvol
				ld		a, (msx_stepc)
				and		0x0F
				ld		l, a
				ld		h, 0
				add		hl, hl					; msx_step_per = msx_per[msx_steptb[i]]: таблицы слиты
				ld		de, msx_step_per
				add		hl, de
				ld		e, (hl)
				inc		hl
				ld		d, (hl)
				jp		msx_setper
mse4:			; тон с 8-битным периодом из параметра, громкость затухает
				push	hl
				ld		de, 3
				add		hl, de
				ld		e, (hl)
				ld		d, 0
				push	bc
				call	msx_setper
				pop		bc
				pop		hl
				ld		a, b
				rrca
				and		0x0F
				jp		msx_setvol
mse5:			; пила: период ((c<<2) циклически) ^ 0xA0
				ld		a, b
				rlca
				rlca
				xor		0xA0
				ld		e, a
				ld		d, 0
				call	msx_setper
				ld		a, 0x0F
				jp		msx_setvol
mse7:			; тон с 16-битным периодом из параметра
				push	hl
				ld		de, 2
				add		hl, de
				ld		d, (hl)
				inc		hl
				ld		e, (hl)
				call	msx_setper
				pop		hl
				ld		a, 0x0F
				jp		msx_setvol
mse8:			; тон, фиксированный период 0x0020
				ld		de, 0x0020
				call	msx_setper
				ld		a, 0x0F
				jp		msx_setvol
mse9:			; тон по списку периодов (MSX 0x4581): параметр = указатель на список байт-периодов,
				; 0xFF -> следующее слово задаёт новый адрес списка (у обоих списков — на себя,
				; то есть список зациклен). Здесь (+2) = МЛАДШИЙ байт указателя, (+3) — старший
				; (у эффекта 7 наоборот — так в оригинале).
				ld		de, 2
				add		hl, de				; HL -> слот+2
				ld		e, (hl)
				inc		hl
				ld		d, (hl)				; DE = указатель списка, HL -> слот+3
mse9_l:			ld		a, (de)
				inc		de
				cp		0xFF
				jp		nz, mse9_v
				ld		a, (de)				; 0xFF: следующее слово — новый адрес списка
				inc		de
				ld		b, a
				ld		a, (de)
				ld		d, a
				ld		e, b
				jp		mse9_l
mse9_v:			ld		(hl), d				; параметр := сдвинутый указатель
				dec		hl
				ld		(hl), e
				ld		e, a
				ld		d, 0
				call	msx_setper
				ld		a, 0x0F
				jp		msx_setvol

msx_setper:		; DE = период -> R(2s), R(2s+1)
				ld		a, (msx_si)
				add		a, a
				ld		c, a
				jp		msx_wper
msx_setvol:		; A = значение -> R(8+s)
				ld		b, a
				ld		a, (msx_si)
				add		a, 8
				ld		c, a
				jp		msx_wr

msx_tone_on:	; включить тон канала слота в тени R7 и записать R7 (HL сохраняется)
				push	hl
				call	msx_slotbit
				cpl
				jp		msx_mixand
msx_noise_on:	push	hl
				call	msx_slotbit
				rlca
				rlca
				rlca
				and		0x38
				cpl
msx_mixand:		ld		c, a
				ld		a, (msx_mix)
				and		c
				ld		(msx_mix), a
				ld		b, a
				ld		c, 7
				call	msx_wr
				pop		hl
				ret
msx_slotbit:	; A = 1/2/4 по номеру слота (как MSX 0x443A: A' = слот+1, тройка заменяется четвёркой)
				ld		a, (msx_si)
				inc		a
				cp		3
				ret		nz
				ld		a, 4
				ret

msx_sfx_kill:	; HL -> слот, A = id: освободить, погасить громкость, поднять биты в тени.
				; R7 НЕ пишется — ровно как MSX 0x4402 (иначе лишняя запись в журнале).
				push	af						; id — для отложенной ноты (msx_vhkill)
				ld		(hl), 0
				xor		a
				call	msx_setvol
				ld		a, (msx_si)
				ld		l, a
				ld		h, 0
				ld		de, msx_kmask
				add		hl, de
				ld		a, (hl)
				ld		c, a
				ld		a, (msx_mix)
				or		c
				ld		(msx_mix), a
				pop		af
				jp		msx_vhkill				; отложенная нота: эффект кончился — слили ли его?

msx_sfx_start:	; A = id, B = тиков, DE = параметр (hi:lo), C = слот
				push	af
				ld		a, (msx_play)
				or		a
				jp		nz, mss_no			; пока играет мелодия, эффектов нет (на MSX игра стоит)
				call	msx_vhnew			; новый эффект в слоте: метка отложенной ноты сброшена
				ld		a, c
				add		a, a
				add		a, a
				ld		l, a
				ld		h, 0
				push	de
				ld		de, msx_sfx
				add		hl, de
				pop		de
				pop		af
				ld		(hl), a
				inc		hl
				ld		(hl), b
				inc		hl
				ld		(hl), d
				inc		hl
				ld		(hl), e
				ld		a, 1
				ld		(msx_busy), a
				ret
mss_no:			pop		af
				ret

""")


WAIT_VEC = ('\t\t\t\tei\t\t\t\t\t\t\t; кадровое прерывание Вектора не защёлкивается:\n'
            '\t\t\t\thalt\t\t\t\t\t\t;   ждать можно ТОЛЬКО ei/halt')
WAIT_LOCKSTEP = ('\t\t\t\t; цель lockstep: прерываний нет вовсе, кадр не ждём\n'
                 '\t\t\t\t; (темп на этой цели не судят, а halt повесил бы прогон навсегда)')


def driver(target):
    return DRIVER % {'passes': MSX_PASSES, 'ticks': MSX_TICKS,
                     'wait': WAIT_VEC if target == 'vec' else WAIT_LOCKSTEP}





# ============================================================================
#  Точки входа, которые видит игровой код. Имена ZX сохранены — сайты вызова не
#  трогаются, кроме пяти, где одна ZX-процедура на MSX разошлась по разным
#  адресатам (они перечислены в apply). Соответствие установлено построчной
#  сверкой всех 33 ZX-сайтов с 27 адресами движка MSX:
#  ~/projects/alien8-research/msx/SFX_SITES.md.
#  Этот текст вставляется ДО трансляции Z80 -> i8080, поэтому (ix+d) здесь законны.
# ============================================================================
GAME_HOOKS = """
; ---- звук из игрового кода: имена ZX сохранены, внутри — эффекты и мелодии MSX ----
; Три опорные формулы, по которым проверена вся таблица: эффект 7 берёт период из
; ~((ix+1)+(ix+2)+(ix+3)) (ZX audio_B654), эффект 4 — из ~(ix+3) (ZX audio_B63C),
; эффект 3 «шаги» считает громкость из координат игрока ровно как ZX loc_B6E6.

audio_B62C:
        ; прыжок (MSX 0x6034: ld (ix+11),8 : push bc : ld hl,0x4541 : call 0x439D : pop bc)
        ; -> эффект 5, слот 1 / канал B, 31 тик, период ((c<<2) & 0xFF) ^ 0xA0
        ld de, 0
        ld a, 5
        ld b, 0x1F
        ld c, 1
        jp msx_sfx_start
        ; End of function audio_B62C

audio_B63C:
        ; MSX 0x4506: эффект 4, слот 1 / канал B, 31 тик, 8-битный период ~(ix+3)
        ld a, (ix+3)
audio_B63F:
        ; короткий вход: A уже загружен вызывателем (MSX 0x4509)
        cpl
        ld e, a
        ld d, 0
        ld a, 4
        ld b, 0x1F
        ld c, 1
        jp msx_sfx_start
        ; End of function audio_B63C

audio_B64A:
        ; MSX 0x4A93 ... : на ZX здесь (ix+1), на MSX обе строки (B64A и B64F) зовут
        ; ОДИН вход 0x44E8 с суммой координат — воспроизводим MSX, а не ZX
        jp audio_B654
audio_B64F:
        jp audio_B654

audio_B654:
        ; MSX 0x44E8 — эталонная формула: эффект 7, слот 1 / канал B, 7 тиков,
        ; период = ~((ix+1)+(ix+2)+(ix+3)). Шаг 2.2 (по образцу ixrest): нативно —
        ; hl=(z80_ix), три байта подряд суммируются, z80_ix НЕ двигается (экономия
        ; на il_ix_lda/il_ix_add: 1338 т/итер в тяжёлых комнатах -> ~70).
        ; HL вызывателю не нужен: на всех сайтах он сразу перезаписывается или не
        ; читается, а msx_sfx_start считает своё; флаги после cpl не читаются.
        ld hl, (z80_ix)
        inc hl
        ld a, (hl)      ; (ix+1)
        inc hl
        add a, (hl)     ; +(ix+2)
        inc hl
        add a, (hl)     ; +(ix+3)
        cpl
        ld e, a
        ld d, 0
audio_msx_e7:
        ; общий хвост: DE = период (16 бит), эффект 7
        ld a, 7
        ld b, 7
        ld c, 1
        jp msx_sfx_start
        ; End of function audio_B654

audio_msx_e7hl:
        ; вход MSX 0x44F5: период УЖЕ в HL (у ZX этому соответствуют sub_B5EE/sub_B604
        ; и два сайта toggle_FE_bit4_x16)
        ld e, l
        ld d, h
        jr audio_msx_e7

sub_B5EE:
        ; искры распада (MSX 0x54CF через общий хвост 0x54C3): эффект 7,
        ; период = (~((ix+0) >>> 3)) AND 0xE0 — нисходящая гамма по номеру кадра спрайта
        ld a, (ix+0)
        rrca
        rrca
        rrca
        cpl
        and 0xE0
        ld l, a
        ld h, 0
        jr audio_msx_e7hl
        ; End of function sub_B5EE

sub_B604:
        ; MSX слил этот звук с предыдущим: 0x5A8E jp 0x54C3 — тот же хвост
        jp sub_B5EE
        ; End of function sub_B604

sub_B619:
        ; MSX 0x447C: эффект 2, слот 0 / канал A, 15 тиков, нисходящий чирп 0x100 + 2c
        ld de, 0
        ld a, 2
        ld b, 0x0F
        ld c, 0
        jp msx_sfx_start
        ; End of function sub_B619

sub_B676:
        ; MSX 0x445E: эффект 1 «шум», слот 0 / канал A, 31 тик,
        ; громкость 15->0, период шума 1..30
        ld de, 0
        ld a, 1
        ld b, 0x1F
        ld c, 0
        jp msx_sfx_start
        ; End of function sub_B676

audio_msx_e9a:
        ; MSX 0x4B5A и 0x515A (дескриптор 0x456B): эффект 9, слот 1, 7 тиков,
        ; период по зацикленному списку 10 18 20 28
        ld d, low msx_e9a
        ld e, high msx_e9a
        jr audio_msx_e9
audio_msx_e9b:
        ; MSX 0x4BB8 (дескриптор 0x4576): список 60 44 30 38
        ld d, low msx_e9b
        ld e, high msx_e9b
audio_msx_e9:
        ld a, 9
        ld b, 7
        ld c, 1
        jp msx_sfx_start

loc_B6C0:
        ; MSX 0x4B5A — эффект 9 со списком 10 18 20 28 (проверки (ix+0) AND 1 у MSX нет)
        jp audio_msx_e9a

audio_B6CE:
        ; шаги (MSX 0x6062 -> 0x4493): проверку «нечётный кадр» оригинал ZX держит в теле,
        ; на MSX она вынесена в сайт 0x605B — эффект тот же, сохраняем ZX-структуру
        ld a, (ix+0)
        and 1
        ret nz
loc_B6D4:
        ; вход мимо проверки (ZX-сайт 6301)
        ; -> эффект 3, слот 2 / канал C, 23 тика: нота из таблицы 16 нот по msx_stepc AND 0x0F,
        ; громкость 8..15 из координат игрока (graphic_objs_tbl+1/+2)
        ld hl, msx_stepc
        inc (hl)
        ld de, 0
        ld a, 3
        ld b, 0x17
        ld c, 2
        jp msx_sfx_start
        ; End of function audio_B6CE

toggle_FE_bit4_x16:
        ; подбор/сброс предмета (upd_3F, MSX 0x5B98) и лишняя жизнь (upd_0C, MSX 0x5D13):
        ; эффект 7 с ПОСТОЯННЫМ периодом 0x0040
        ld hl, 0x0040
        jp audio_msx_e7hl

toggle_FE_bit4_x32:
        ; MSX 0x4555: эффект 8, слот 0 / канал A, 7 тиков, фиксированный период 0x0020
        ld de, 0
        ld a, 8
        ld b, 7
        ld c, 0
        jp msx_sfx_start

toggle_FE_bit4_x24:
        ; пауза (audio_CE22): на MSX 0x6B4B и 0x6B63 — мелодия «блип» 0x477E
audio_msx_blip:
        ld de, msx_hdr_blip
        jp play_audio
        ; End of function toggle_FE_bit4_x16

audio_msx_ladder:
        ; ЗВУК ВНЕ ДВИЖКА (MSX 0x50F5..0x5117): восемь нисходящих ступеней на канале A,
        ; период (B-1)*16, громкость 15, пауза между ступенями. У MSX паузой служит
        ; перерисовка (0x41CC) — у нас это меняло бы состояние игры, поэтому пустой цикл.
        xor a
        ld (msx_si), a                          ; слот 0 -> канал A
        call msx_tone_on
        ld b, 8
aml_l:  ld a, b
        dec a
        rlca
        rlca
        rlca
        rlca
        ld e, a
        ld d, 0
        push bc
        call msx_setper
        ld a, 0x0F
        call msx_setvol
        ld de, 0x0400
aml_d:  dec de
        ld a, d
        or e
        jr nz, aml_d
        pop bc
        djnz aml_l
        xor a
        call msx_setvol                         ; гасим канал A
        ret

; ---- проигрыватели мелодий: имена ZX, тела MSX (проигрыватель блокирующий) ----
play_audio_wait_key:
        ld hl, audio_played
        ld a, (hl)
        and a
        ret nz
        set 0, (hl)
        ; End of function play_audio_wait_key

play_audio_until_keypress:
        ; MSX 0x45B6 (A := 1): играть, прерываясь ЛЮБОЙ клавишей
        xor a
        call read_key
        ret nz                                  ; клавиша уже нажата — не играем (как ZX)
        ex de, hl
        call msx_play_tune
pauk_l:
        call msx_frame
        ld a, (msx_play)
        or a
        jp z, pauk_r
        xor a
        call read_key
        jp z, pauk_l
        jp msx_stop_tune
pauk_r:
        ret
        ; End of function play_audio_until_keypress

play_audio:
        ; MSX 0x45BA (A := 0): играть до конца. Ждать ОБЯЗАТЕЛЬНО: на MSX проигрыватель
        ; блокирующий, а под `di` в print_sprite Вектор теряет кадровые прерывания.
        ex de, hl
        call msx_play_tune
pa_l:
        call msx_frame
        ld a, (msx_play)
        or a
        jp nz, pa_l
        ret
        ; End of function play_audio
"""


def apply(src):
    """Вырезать ZX-звук и вставить крючки MSX. Возвращает (src, отчёт по вырезанному)."""
    rep = {}

    def cut(pattern, name, repl='', flags=re.S):
        nonlocal src
        m = re.search(pattern, src, flags)
        assert m, 'a8_sound_ay: не найдено — ' + name
        rep[name] = len(m.group(0))
        src = src[:m.start()] + repl + src[m.end():]

    def site(old, new, name):
        nonlocal src
        assert src.count(old) == 1, 'a8_sound_ay: сайт не уникален — ' + name
        src = src.replace(old, new, 1)
        rep['сайт: ' + name] = 0

    # --- 1. сайты, где одна ZX-процедура на MSX разошлась по разным адресатам ---
    site("        ld hl, byte_B6A9\n        call audio_B690\n",
         "        call audio_msx_e9a   ; MSX 0x4B5A: эффект 9, список 10 18 20 28\n",
         'upd_66..: эффект 9, список A')
    # на цели vec a8_vec.glue уже перенесла число 0xB6AD в метку byte_B6A9+4
    cut(r'        ld hl, (?:0xB6AD|byte_B6A9\+4)\n        call audio_B690\n',
        'upd_6E..: эффект 9, список B',
        "        call audio_msx_e9b   ; MSX 0x4BB8: эффект 9, список 60 44 30 38\n")
    site("        jr nz, loc_B00B\n        call sub_B5EE\n",
         "        jr nz, loc_B00B\n        call audio_msx_ladder   ; MSX 0x50F5: лесенка на канале A\n",
         'фанфара: ручная лесенка вместо эффекта')
    site("        call toggle_FE_bit4_x16\n        inc (ix+17)\n",
         "        ; MSX: звука здесь НЕТ (0x4CD2 идёт из ld (ix+10),a прямо в inc (ix+11));\n"
         "        ; доказательство — SFX_SITES.md §5. Единственный такой случай из 33.\n"
         "        inc (ix+17)\n",
         'upd_50: на MSX звука нет')
    site("        call a8_setmode\na8_ctl_done:\n",
         "        call a8_setmode\n"
         "        call audio_msx_blip   ; MSX 0x5905: смена настройки в меню -> мелодия «блип»\n"
         "a8_ctl_done:\n",
         'меню: блип при смене настройки')

    # --- 2. весь ZX-путь звука одним куском: мелодии, проигрыватель на бипере, freq_tbl,
    #        процедуры audio_B*/sub_B*/toggle_FE_* -> крючки на движок MSX ---
    cut(r'start_game_tune:\n.*?; End of function toggle_FE_bit4\n', 'ZX-путь звука',
        ';\n; Мелодии: данные из MSX-версии, имена ZX = адреса заголовков\n;\n'
        'start_game_tune:\t\tEQU\tmsx_hdr_start_game\n'
        'obj_5C_tune:\t\t\tEQU\tmsx_hdr_obj_5C\n'
        'game_over_tune:\t\t\tEQU\tmsx_hdr_game_over\n'
        'game_complete_tune:\t\tEQU\tmsx_hdr_game_complete\n'
        'menu_tune:\t\t\t\tEQU\tmsx_hdr_menu\n'
        + GAME_HOOKS +
        '\n; __A8_SOUND_DRIVER__ (ядро драйвера и данные подставляются ПОСЛЕ трансляции)\n')

    # --- 3. тик эффектов: конец игровой итерации — глушение AY (MSX 0x41A3, точка слияния
    #        обеих ветвей конца кадра: с панелью и без) ---
    site("loc_A72E:\n        call audio_CE22\n",
         "loc_A72E:\n        call msx_frame_off   ; MSX 0x41A3: глушение AY в конце игрового кадра\n"
         "        call audio_CE22\n",
         'глушение AY в конце итерации')

    # --- 4. инициализация звука: MSX 0x40AA (глушение + тень R7 := 0xBF) — та же точка
    #        слияния START/start_menu, что и у ZX loc_A650 ---
    site("loc_A650:\n        call build_lookup_tbls\n",
         "loc_A650:\n        call msx_snd_init   ; MSX 0x40AA: глушение AY и тень R7 := 0xBF\n"
         "        call build_lookup_tbls\n",
         'инициализация звука при старте')

    return src, rep


_VI53_STATE = """
        ORG 0x7F88              ; состояние плеера: 120 Б добивки до плоскости 0 (там переменные кончаются)
msx_tv_stub: DS 3                ; «out (порт),a / ret» — у i8080 нет out (c)
msx_tv_c: DS 1                    ; номер счётчика текущего голоса (1 или 2)
msx_tv_len: DS 1                  ; длина ноты в кадрах
msx_tv_div: DS 2                  ; делитель текущего такта ноты
msx_tv_stp: DS 2                  ; HL = запись голоса на время msx_tv
msx_tv_base: DS 2                 ; адрес текущего блоба (внутри msx_cat)
msx_tv_divs: DS 2                 ; адрес таблицы делителей (считается в msx_play_tune)
msx_tv_rem: DS 2                  ; сколько тиков (кадров) осталось до глушения
msx_tunenum: DS 1                 ; номер мелодии в каталоге (для TUNE-строки журнала)
msx_tv_v0: DS 16                  ; голос A -> счётчик 1: pc(2), start(2), res, snd, depth, стек 4 слова
msx_tv_v1: DS 16                  ; голос B -> счётчик 2: та же запись
        ASSERT $ <= 0x7FB8        ; занято 48 Б; остаток добивки — под зеркало регистров (msx_viflush)
"""


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


def emit(src, target):
    """ПОСЛЕ трансляции: подставить ядро драйвера и данные на место маркера;
    состояние плеера — в добивку 0x7F88 (перед SAVEBIN, как делает splash_layout)."""
    mark = '; __A8_SOUND_DRIVER__ (ядро драйвера и данные подставляются ПОСЛЕ трансляции)'
    assert src.count(mark) == 1, 'a8_sound_ay: маркер драйвера'
    if target != 'vec':
        # lockstep: раскладки Вектора нет (0x7F88 там — середина кода, 0xF0xx — zxvram), всё
        # идёт сразу за данными драйвера, без ORG
        flat = '\n'.join(l for l in _VI53_STATE.split('\n')
                          if not re.match(r'\s+(ORG|ASSERT) ', l))
        return src.replace(mark, driver(target) + VI_LOW + data_block() + VI_CODE + flat
                           + '        ALIGN 64                ; 40 Б ячеек слива — в одной странице\n'
                           + VI_STATE + _VI_ASSERTS, 1)
    src = src.replace(mark, driver(target) + VI_LOW + data_block(), 1)
    # конец хвоста спрайтов (0xE000..): за ним до таблиц 0xF100 — дыра под код слива
    tail = '        ASSERT $ <= 0xf100   ; хвост спрайтов не должен налезть на таблицы сдвига\n'
    if src.count(tail) != 1:
        raise SystemExit('a8_sound_ay: конец хвоста спрайтов не найден')
    src = src.replace(tail, 'a8_spr_top:     equ $   ; конец хвоста спрайтов: дальше код слива AY -> ВИ53\n'
                      + tail, 1)
    blk = (_VI53_STATE
           + '        ORG 0x7FC0              ; слив AY -> ВИ53: зеркало регистров и ячейки (добивка)\n'
           + VI_STATE + _VI_ASSERTS
           + '        ASSERT $ <= 0x8000        ; добивка кончается плоскостью 0\n'
           + '        ORG a8_spr_top          ; код слива AY -> ВИ53: дыра за хвостом спрайтов\n'
           + VI_CODE
           + '        ASSERT $ <= 0xF100        ; слив AY -> ВИ53 не должен налезть на таблицы сдвига\n')
    src, n = re.subn(r'^        SAVEBIN [^\n]*$', lambda m: blk + m.group(0) + '\n',
                     src, count=1, flags=re.M)
    if n != 1:
        raise SystemExit('a8_sound_ay: строка SAVEBIN не найдена')
    return src
