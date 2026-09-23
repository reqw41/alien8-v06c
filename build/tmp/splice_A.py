#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Задача 2, шаг A: мелодии — плеер блоба msx_tunes_vi53.bin вместо real-time MSX.
Врезка по номерам строк (атомарная: ассерты на границы, при ошибке файл не пишется)."""
import io, sys

P = 'tools/a8_sound_ay.py'
lines = open(P, encoding='utf-8').read().split('\n')  # 0-based

def chk(n, prefix):  # n = 1-based
    assert lines[n - 1].startswith(prefix), (n, prefix, lines[n - 1][:60])

def splice(start, end, new):  # 1-based inclusive
    if isinstance(new, str):
        new = new.split('\n') if new != '' else []
    lines[start - 1:end] = list(new)

# ---- ассерты границ (оригинальная нумерация) ----
chk(23, 'import os'); chk(24, 'import re'); chk(27, 'TUNES = os.path.join')
chk(68, "    txt = '"); chk(69, "    txt += _db('msx_per'"); chk(83, "    txt += _db('msx_stream'")
chk(84, '    txt += """msx_e9a:')
chk(93, 'msx_ci:'); chk(94, 'msx_rem:'); chk(96, 'msx_end:'); chk(99, 'msx_ch:')
chk(100, '"""'); chk(101, '    return txt')
chk(144, '\t\t\t\tld\t\t(msx_end), a'); chk(148, '\t\t\t\tld\t\tb, 12 + 21')
chk(158, '; ----'); chk(159, 'msx_play_tune:'); chk(206, '\t\t\t\tjp\t\tmsx_silence')
chk(208, 'msx_frame:'); chk(394, '\t\t\t\tjp\t\tmsx_volmode'); chk(395, '')
chk(407, 'msx_volmode:'); chk(436, ''); chk(437, '; ----')
chk(571, '\t\t\t\tld\t\ta, (msx_stepc)'); chk(585, '\t\t\t\tld\t\td, (hl)')
chk(586, '\t\t\t\tjp\t\tmsx_setper')
chk(1082, 'def emit'); chk(1086, '    return src.replace(mark')

TUNE_SECTION = """; ---------------------------------------------------------------- мелодии
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
				; divs = база + 10 + 2nr (nr = слово по +6), как a8_tune_init у заставки
				ld		hl, msx_tv_base + 6
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
				ld		a, 0x76					; заглушить счётчики 1,2: с эффектов мог остаться тон
				out		(0x08), a
				ld		a, 0xB6
				out		(0x08), a
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
				dec		(hl)
				jp		nz, mtt_a
				inc		hl
				dec		(hl)					; заём из младшего (rem > 0 до тика)
				dec		hl
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
				jp		msx_tv_stub"""

FRAME_NEW = """msx_frame:		; один видеокадр мелодии: ждём обратного хода, затем один тик обоих голосов
%(wait)s
				call	msx_tv_tick
				ret"""

MSE3_NEW = """				ld		a, (msx_stepc)
				and		0x0F
				ld		l, a
				ld		h, 0
				add		hl, hl					; msx_step_per = msx_per[msx_steptb[i]]: таблицы слиты
				ld		de, msx_step_per
				add		hl, de
				ld		e, (hl)
				inc		hl
				ld		d, (hl)"""

DATABLOCK_NEW = """    per = [d[O_PERIODS + 2 * i] | (d[O_PERIODS + 2 * i + 1] << 8) for i in range(64)]
    stp = d[O_STEPS:O_STEPS + 16]
    txt = '\\n; ---- данные звука (извлечены из картриджа MSX, src/msx_tunes.bin) ----\\n'
    # real-time проигрыватель мелодий MSX снят (мелодии — готовые потоки ВИ53, см. ниже);
    # от данных мелодий (msx_per/msx_steptb/msx_init/msx_env/msx_headers/msx_stream)
    # осталась только двойная выборка эффекта 3 — одна слитая таблица периодов «шагов»
    txt += _db('msx_step_per', b''.join(struct.pack('<H', per[stp[i]]) for i in range(16)),
               'эффект «шаги»: период = msx_per[msx_steptb[i]], индекс = msx_stepc AND 0x0F')
    txt += _db('msx_stop', d[O_STOP:O_STOP + 9], 'список PSG «полная тишина»')
    txt += _db('msx_kmask', [0x09, 0x12, 0x24], 'биты тона+шума слота 0/1/2 в тени R7')"""

RETURN_NEW = '''"""
    txt += '\\n; ---- мелодии: готовые потоки ВИ53 (src/msx_tunes_vi53.bin, tools/a8_tunes_msx.py) ----\\n'
    with open(VI53, 'rb') as f:
        v = f.read()
    assert len(v) == 847, 'msx_tunes_vi53.bin: ожидалось 847 байт (сначала tools/a8_tunes_msx.py)'
    txt += _db('msx_cat', v, 'каталог + 6 блобов в формате a8_tune_c64 (голос C всегда пуст)')
    txt += _db('msx_catidx', bytes(range(6)), 'байт для DE: адрес msx_hdr_* передаётся в play_audio')
    for i, nm in enumerate(TUNE_NAMES):
        txt += 'msx_hdr_%s:\\t\\t\\tEQU\\tmsx_catidx+%d\\n' % (nm, i)
    return txt'''

EMIT_NEW = '''_VI53_STATE = """
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


def emit(src, target):
    """ПОСЛЕ трансляции: подставить ядро драйвера и данные на место маркера;
    состояние плеера — в добивку 0x7F88 (перед SAVEBIN, как делает splash_layout)."""
    mark = '; __A8_SOUND_DRIVER__ (ядро драйвера и данные подставляются ПОСЛЕ трансляции)'
    assert src.count(mark) == 1, 'a8_sound_ay: маркер драйвера'
    src = src.replace(mark, driver(target) + data_block(), 1)
    src, n = re.subn(r'^        SAVEBIN [^\\n]*$', lambda m: _VI53_STATE + m.group(0) + '\\n',
                     src, count=1, flags=re.M)
    if n != 1:
        raise SystemExit('a8_sound_ay: строка SAVEBIN не найдена')
    return src'''

# ---- врезки снизу вверх ----
splice(1082, 1086, EMIT_NEW)
splice(571, 585, MSE3_NEW)
splice(407, 436, '')                      # msx_volmode..msx_setvolm — только проигрывателю мелодий
splice(208, 394, FRAME_NEW)               # msx_mtick/msx_chan/msx_fetch/msx_note — real-time пересчёт снят
splice(158, 206, TUNE_SECTION)
splice(148, 148, '\t\t\t\tld\t\tb, 12\t\t\t\t\t; слоты эффектов')
splice(144, 144, '')                      # msx_end больше нет
splice(100, 101, RETURN_NEW)
splice(99, 99, ''); splice(96, 96, ''); splice(94, 94, ''); splice(93, 93, '')  # msx_ch/msx_end/msx_rem/msx_ci
splice(68, 83, DATABLOCK_NEW)
lines.insert(27, "VI53 = os.path.join(HERE, '..', 'src', 'msx_tunes_vi53.bin')")
lines.insert(24, 'import struct')

open(P, 'w', encoding='utf-8').write('\n'.join(lines))
print('OK: a8_sound_ay.py, %d строк' % len(lines))
