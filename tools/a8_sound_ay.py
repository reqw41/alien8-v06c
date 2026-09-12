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

HERE = os.path.dirname(os.path.abspath(__file__))
TUNES = os.path.join(HERE, '..', 'src', 'msx_tunes.bin')

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
    txt = '\n; ---- данные звука (извлечены из картриджа MSX, src/msx_tunes.bin) ----\n'
    txt += _db('msx_per', d[O_PERIODS:O_PERIODS + 128],
               'период по номеру ноты 0..63 (0..7 — слова таблицы команд MSX: их пишет заглушка с громкостью 0)')
    txt += _db('msx_steptb', d[O_STEPS:O_STEPS + 16], 'ноты эффекта «шаги», индекс = msx_stepc AND 0x0F')
    txt += _db('msx_init', d[O_INIT:O_INIT + 13], 'список PSG перед мелодией')
    txt += _db('msx_stop', d[O_STOP:O_STOP + 9], 'список PSG «полная тишина»')
    txt += _db('msx_env', d[O_ENV:O_ENV + 3], 'R13 := 0 (форма огибающей)')
    txt += _db('msx_kmask', [0x09, 0x12, 0x24], 'биты тона+шума слота 0/1/2 в тени R7')
    for i, nm in enumerate(TUNE_NAMES):
        w = d[O_HEADERS + 6 * i: O_HEADERS + 6 * i + 6]
        offs = [(w[2 * k] | (w[2 * k + 1] << 8)) for k in range(3)]
        for o in offs:
            assert 0 <= o < 445, 'заголовок %s: смещение %d вне пула потоков' % (nm, o)
        txt += 'msx_hdr_%s:\tDW\t%s\t; каналы C, B, A\n' % (
            nm, ', '.join('msx_stream+%d' % o for o in offs))
    txt += _db('msx_stream', d[O_STREAMS:O_STREAMS + 445], 'потоки нот всех шести мелодий (адреса MSX 0x4784..0x4940)')
    txt += """msx_e9a:		DB	0x10, 0x18, 0x20, 0x28, 0xFF	; список периодов эффекта 9 (MSX 0x456F)
				DW	msx_e9a
msx_e9b:		DB	0x60, 0x44, 0x30, 0x38, 0xFF	; вариант B (MSX 0x457A)
				DW	msx_e9b

; ---- переменные драйвера (41 байт) ----
msx_mix:		DS		1			; тень регистра 7 (микшер), как 0xD810 на MSX
msx_stepc:		DS		1			; счётчик шагов (индекс в msx_steptb), как 0xD811
msx_si:			DS		1			; текущий слот эффекта 0..2
msx_ci:			DS		1			; текущий канал мелодии 0..2 (0 -> AY C, 1 -> B, 2 -> A)
msx_rem:		DS		1			; сколько «проходов» MSX осталось отмотать в этом кадре
msx_play:		DS		1			; 1 = мелодия играет
msx_end:		DS		1			; 1 = в потоке встретилась команда END
msx_busy:		DS		1			; 1 = хотя бы один слот эффекта занят (быстрый пропуск тика)
msx_sfx:		DS		12			; 3 слота по 4 байта: id, тиков, параметр_hi, параметр_lo
msx_ch:			DS		21			; 3 канала по 7: ptr(2), dur(2), режим громкости(1), начало потока(2)
"""
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

msx_wr:			; C = регистр AY, B = значение. HL/DE/BC целы.
				ld		a, c
				out		(0x15), a			; номер регистра
				ld		a, b
				out		(0x14), a			; данные
				ret

msx_wlist:		; HL = список пар (регистр, значение), терминатор 0xFF
				ld		a, (hl)
				inc		hl
				cp		0xFF
				ret		z
				ld		c, a
				ld		b, (hl)
				inc		hl
				push	hl
				call	msx_wr
				pop		hl
				jp		msx_wlist

msx_snd_init:	; из vec_boot: слоты пусты, мелодии нет, звук молчит
				xor		a
				ld		(msx_play), a
				ld		(msx_end), a
				ld		(msx_stepc), a
				ld		(msx_busy), a
				ld		hl, msx_sfx
				ld		b, 12 + 21			; слоты эффектов и каналы мелодии
msi_l:			ld		(hl), 0
				inc		hl
				dec		b
				jp		nz, msi_l
				ld		a, 0xBF
				ld		(msx_mix), a
msx_silence:	ld		hl, msx_stop
				jp		msx_wlist

; ---------------------------------------------------------------- мелодии
msx_play_tune:	; HL = заголовок мелодии (3 слова). Как MSX 0x45BB: прогнать список инициализации
				; PSG и зарядить три канала. Режим громкости (+4) НЕ обнуляется — дефект
				; оригинала воспроизведён дословно (все шесть потоков начинаются командой режима).
				xor		a
				ld		(msx_end), a
				ld		(msx_play), a
				push	hl
				ld		hl, msx_init
				call	msx_wlist
				pop		hl
				ld		de, msx_ch
				ld		b, 3
mpt_l:			ld		c, (hl)
				inc		hl
				ld		a, (hl)
				inc		hl
				push	hl
				ld		h, a
				ld		l, c				; HL = начало потока канала
				ld		a, l
				ld		(de), a				; +0 ptr_lo
				inc		de
				ld		a, h
				ld		(de), a				; +1 ptr_hi
				inc		de
				xor		a
				ld		(de), a				; +2 dur_lo = 0 -> первый же проход делает выборку
				inc		de
				ld		(de), a				; +3 dur_hi
				inc		de
				inc		de					; +4 режим громкости — как на MSX, не трогаем
				ld		a, l
				ld		(de), a				; +5 начало потока (для команды LOOP)
				inc		de
				ld		a, h
				ld		(de), a				; +6
				inc		de
				pop		hl
				dec		b
				jp		nz, mpt_l
				ld		a, 1
				ld		(msx_play), a
				ret

msx_stop_tune:	xor		a
				ld		(msx_play), a
				ld		(msx_end), a
				jp		msx_silence

msx_frame:		; один видеокадр мелодии: ждём обратного хода и отматываем проходы
				ei							; кадровое прерывание Вектора не защёлкивается:
				halt						;   ждать можно ТОЛЬКО ei/halt
msx_mtick:		ld		a, (msx_play)
				or		a
				ret		z
				xor		a
				ld		(msx_ci), a
				ld		hl, msx_ch
				ld		b, 3
mt_ch:			push	bc
				push	hl
				call	msx_chan
				pop		hl
				pop		bc
				ld		a, (msx_end)
				or		a
				jp		nz, mt_done			; END: остальные каналы в этом проходе не обслуживаются
				ld		de, 7
				add		hl, de
				ld		a, (msx_ci)
				inc		a
				ld		(msx_ci), a
				dec		b
				jp		nz, mt_ch
				ret
mt_done:		xor		a					; список остановки уже записал обработчик END
				ld		(msx_play), a
				ld		(msx_end), a
				ret

msx_chan:		; HL -> структура канала, (msx_ci) = индекс. Отмотать %(passes)d проходов MSX.
				ld		a, %(passes)d
				ld		(msx_rem), a
mc_loop:		ld		d, h
				ld		e, l
				inc		de
				inc		de					; DE -> dur_lo
				ld		a, (de)
				ld		b, a				; B = dur_lo
				inc		de
				ld		a, (de)				; A = dur_hi
				dec		de
				ld		c, a				; C = dur_hi
				or		b
				jp		z, mc_fetch
				ld		a, c
				or		a
				jp		nz, mc_big			; длительность >= 256 > остатка проходов
				ld		a, (msx_rem)
				cp		b
				jp		c, mc_part			; остаток меньше длительности
				sub		b					; остаток >= длительности: dur -> 0, проходы тратим
				ld		(msx_rem), a
				xor		a
				ld		(de), a				; dur_lo = 0 (dur_hi уже 0)
				ld		a, (msx_rem)
				or		a
				ret		z
				jp		mc_loop
mc_part:		ld		c, b				; C = dur_lo
				ld		a, (msx_rem)
				ld		b, a
				ld		a, c
				sub		b
				ld		(de), a				; dur_lo -= остаток
				xor		a
				ld		(msx_rem), a
				ret
mc_big:			ld		a, (msx_rem)
				ld		b, a
				ld		a, (de)
				sub		b
				ld		(de), a
				jp		nc, mc_big2
				inc		de
				ld		a, (de)
				dec		a
				ld		(de), a
mc_big2:		xor		a
				ld		(msx_rem), a
				ret
mc_fetch:		push	hl
				call	msx_fetch
				pop		hl
				ld		a, (msx_end)
				or		a
				ret		nz
				ld		a, (msx_rem)		; выборка тоже занимает один проход
				dec		a
				ld		(msx_rem), a
				ret		z
				jp		mc_loop

msx_fetch:		; HL -> структура канала: читать события, пока не установится длительность
mf_loop:		ld		e, (hl)
				inc		hl
				ld		d, (hl)
				dec		hl					; DE = указатель потока
				ld		a, (de)
				inc		de
				ld		(hl), e
				inc		hl
				ld		(hl), d
				dec		hl					; указатель сдвинут
				cp		8
				jp		nc, mf_note
				or		a
				jp		z, mf_mode
				cp		4
				jp		z, mf_rest
				cp		6
				jp		z, mf_loopc
				cp		7
				jp		z, mf_end
mf_mode:		; команды 0,1,2,3,5 — только меняют режим громкости, время не тратят
				push	hl
				ld		de, 4
				add		hl, de
				ld		(hl), a
				pop		hl
				jp		mf_loop
mf_loopc:		; команда 6: вернуться на начало потока
				push	hl
				ld		de, 5
				add		hl, de
				ld		e, (hl)
				inc		hl
				ld		d, (hl)
				pop		hl
				ld		(hl), e
				inc		hl
				ld		(hl), d
				dec		hl
				jp		mf_loop
mf_end:			; команда 7: полная тишина и выход из проигрывателя (MSX 0x473C)
				ld		a, 1
				ld		(msx_end), a
				jp		msx_silence
mf_rest:		; команда 4 (MSX 0x4723): режим 4, громкость по режиму, затем явный ноль,
				; пауза 1024 прохода
				push	hl
				inc		hl
				inc		hl
				ld		(hl), 0				; dur_lo
				inc		hl
				ld		(hl), 4				; dur_hi -> 0x0400 = 1024 прохода
				inc		hl
				ld		(hl), 4				; режим := 4
				pop		hl
				push	hl
				call	msx_volmode
				pop		hl
				xor		a
				jp		msx_setvolm			; поверх режима — явный ноль
mf_note:		; A = байт ноты: биты 0-5 номер, 6-7 множитель длительности
				ld		b, a
				push	hl					; указатель структуры канала
				rlca
				rlca
				and		3
				inc		a
				rlca
				rlca						; (множитель+1)*4 = старший байт длительности (1024..4096)
				inc		hl
				inc		hl
				ld		(hl), 0				; dur_lo
				inc		hl
				ld		(hl), a				; dur_hi
				ld		a, b
				and		0x3F
				ld		l, a
				ld		h, 0
				add		hl, hl
				ld		de, msx_per
				add		hl, de
				ld		e, (hl)
				inc		hl
				ld		d, (hl)				; DE = период
				ld		a, (msx_ci)
				add		a, a
				ld		c, a
				ld		a, 4
				sub		c
				ld		c, a				; регистр тона: канал 0 -> R4, 1 -> R2, 2 -> R0
				call	msx_wper
				pop		hl
				jp		msx_volmode

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

msx_volmode:	; HL -> структура канала: применить режим громкости (+4). Таблица MSX 0x466F.
				push	hl
				ld		de, 4
				add		hl, de
				ld		a, (hl)
				pop		hl
				or		a
				jp		z, msx_setvolm		; режим 0 -> громкость 0
				cp		1
				jp		z, mvm_7
				cp		2
				jp		z, mvm_f
				cp		5
				jp		nc, msx_setvolm		; режим 5 в данных не встречается — считаем молчанием
				ld		a, 0x10				; режимы 3 и 4 — огибающая
				call	msx_setvolm
				ld		hl, msx_env
				jp		msx_wlist
mvm_7:			ld		a, 7				; у MSX Alien 8 режим 1 = громкость 7 (у Knight Lore 9)
				jp		msx_setvolm
mvm_f:			ld		a, 0x0F
msx_setvolm:	; A = значение -> регистр громкости канала мелодии (0 -> R10, 1 -> R9, 2 -> R8)
				ld		b, a
				ld		a, (msx_ci)
				ld		c, a
				ld		a, 10
				sub		c
				ld		c, a
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
				ld		de, msx_steptb
				add		hl, de
				ld		a, (hl)
				ld		l, a
				ld		h, 0
				add		hl, hl
				ld		de, msx_per
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

msx_sfx_kill:	; HL -> слот: освободить, погасить громкость, поднять биты в тени.
				; R7 НЕ пишется — ровно как MSX 0x4402 (иначе лишняя запись в журнале).
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
				ret

msx_sfx_start:	; A = id, B = тиков, DE = параметр (hi:lo), C = слот
				push	af
				ld		a, (msx_play)
				or		a
				jp		nz, mss_no			; пока играет мелодия, эффектов нет (на MSX игра стоит)
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

msx_frame_off:	; конец игровой итерации: полное глушение AY (MSX 0x41A6). Мелодию не трогаем.
				ld		a, (msx_play)
				or		a
				ret		nz
				jp		msx_silence
""") % {'passes': MSX_PASSES, 'ticks': MSX_TICKS}
