#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шаг B (часть 1): msx_wr пишет в зеркало msx_ayregs вместо портов AY;
msx_wlist удаляется; msx_silence глушит зеркалом; msx_frame_off = flush + silence;
msx_play_tune при старте сбрасывает владельцев/кэши счётчиков 1,2; msx_snd_init
заряжает msx_vistub. Врезка по номерам строк, атомарно. Номера — по ee34cd4.
ПОРЯДОК замен: снизу вверх (иначе номера съезжают)."""
P = 'tools/a8_sound_ay.py'
lines = open(P, encoding='utf-8').read().split('\n')  # 0-based

def chk(n, prefix):  # n = 1-based
    assert lines[n - 1].startswith(prefix), (n, prefix, lines[n - 1][:60])

def find(prefix):  # единственный якорь по тексту — порядок с splice_B2 не важен
    idx = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    assert len(idx) == 1, (prefix, idx)
    return idx[0]

# ---- ассерты границ (номера по ee34cd4; frame_off — динамический якорь) ----
chk(78, "    txt += _db('msx_stop'")
chk(121, 'msx_wr:')
chk(126, '\t\t\t\tret')
chk(128, 'msx_wlist:')
chk(139, '\t\t\t\tjp\t\tmsx_wlist')
chk(145, '\t\t\t\tld\t\t(msx_tv_stub + 2), a')
chk(158, 'msx_silence:')
chk(159, '\t\t\t\tjp\t\tmsx_wlist')
chk(268, '\t\t\t\tld\t\t(msx_play), a')
chk(269, '\t\t\t\tret')
FO_AT = find('msx_frame_off:')
assert lines[FO_AT + 4].startswith('\t\t\t\tjp\t\tmsx_silence'), lines[FO_AT + 4]

WR = """msx_wr:			; C = регистр AY, B = значение. HL/DE/BC целы.
				push	hl
				ld		a, c
				and		0x0F
				add		a, low msx_ayregs	; зеркало выровнено на 16: переноса в старший нет
				ld		l, a
				ld		h, high msx_ayregs
				ld		(hl), b
				pop		hl
				ret""".split('\n')

SIL = """msx_silence:	; полная тишина AY: микшер выключен, громкости 0 (пишем прямо в зеркало;
				;  список msx_stop и обход msx_wlist сняты за ненадобностью)
				ld		a, 0xFF					; в R7 ноль = включено: FF = всё выключено
				ld		(msx_ayregs + 7), a
				xor		a
				ld		(msx_ayregs + 8), a
				ld		(msx_ayregs + 9), a
				ld		(msx_ayregs + 10), a
				ret""".split('\n')

INIT = """				ld		a, 0xD3					; та же заглушка «out (порт), a» для msx_viemit
				ld		(msx_vistub), a
				ld		a, 0xC9
				ld		(msx_vistub + 2), a""".split('\n')

PLAY = """				ld		a, 0xFF					; плеер пишет счётчики 1,2 мимо msx_viown/
				ld		(msx_viown + 1), a		;  msx_vidiv — сбросим владельцев и кэши,
				ld		(msx_vidiv + 3), a		;  иначе первая же нота после мелодии
				ld		(msx_vidiv + 4), a		;  «совпадёт с кэшем» и промолчит
				ld		(msx_viown + 2), a""".split('\n')

FO = """msx_frame_off:	; конец игровой итерации: слить зеркало в счётчики 1,2 и заглушить AY
				;  (MSX 0x41A6). Во время мелодии счётчики у неё — flush не трогает.
				ld		a, (msx_play)
				or		a
				call	z, msx_viflush
				jp		msx_silence""".split('\n')

# снизу вверх
lines[FO_AT:FO_AT + 5] = FO
lines[268:268] = PLAY
lines[157:159] = SIL
lines[145:145] = INIT
lines[127:139] = []
lines[120:126] = WR
lines[77:78] = []

open(P, 'w', encoding='utf-8').write('\n'.join(lines))
print('splice B1 ok: wr->зеркало, wlist удалён, silence=зеркало, frame_off=flush, play_tune=сброс владельцев')
