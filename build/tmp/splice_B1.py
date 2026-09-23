#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шаг B (часть 1), ПЕРЕПИСАНО после сверки с KL (kl_sound_ay.py:172-456, PORT_RECIPE §16/§20).
Правки нижнего региона в tools/a8_sound_ay.py (DRIVER и data_block):
  * msx_wr пишет в зеркало msx_ayregs[C&0x0F] вместо портов AY 0x15/0x14;
  * msx_wlist и таблица msx_stop сняты (msx_silence теперь пишет зеркало, живёт в дыре F01E);
  * msx_snd_init: счётчики 1,2 глушит и владельцев сбрасывает msx_tv_mute, vhold чистится,
    хвост `msx_silence: ld hl,msx_stop / jp msx_wlist` -> `jp msx_silence`;
  * msx_play_tune: вместо двух голых управляющих слов — call msx_tv_mute;
  * msx_tv_mute дополнительно бросает msx_viown[1],[2] = 0xFF (счётчики встали — владельцев нет,
    следующий эффект обязан получить управляющее слово и бой кэша делителя);
  * msx_sfx_kill сохраняет id и хвостом уходит в msx_vhkill (отложенная нота KL, §20);
  * msx_sfx_start сбрасывает msx_vhold[слот] (call msx_vhnew);
  * msx_frame_off снят отсюда — он в дыре F01E (splice_B2) вместе со сливом.
Якоря — ТЕКСТОВЫЕ (строка целиком, единственная), номера строк не используются.
Порядок с splice_B2 любой, каждый — ОДИН раз."""
P = 'tools/a8_sound_ay.py'
src = open(P, encoding='utf-8').read()


def rep(old, new, what):
    global src
    n = src.count(old)
    assert n == 1, (what, n)
    src = src.replace(old, new, 1)


# 1. таблица «полная тишина» больше не нужна: msx_silence пишет зеркало напрямую
rep("    txt += _db('msx_stop', d[O_STOP:O_STOP + 9], 'список PSG «полная тишина»')\n", '',
    'msx_stop')

# 2+3. msx_wr -> зеркало; msx_wlist снят
rep("""msx_wr:			; C = регистр AY, B = значение. HL/DE/BC целы.
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
""", """msx_wr:			; C = регистр AY, B = значение -> ЗЕРКАЛО msx_ayregs (AY на Векторе может не быть;
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
""", 'msx_wr/msx_wlist')

# 4. msx_snd_init: заглушка msx_tv_stub общая с msx_viemit (msx_vistub EQU msx_tv_stub);
#    счётчики 1,2 встают, владельцы 0xFF (msx_tv_mute); отложенных нот нет
rep("""				xor		a
				ld		(msx_play), a
				ld		(msx_stepc), a
				ld		(msx_busy), a
				ld		hl, msx_sfx
""", """				call	msx_tv_mute				; счётчики 1,2 стоят, владельцев нет (0xFF)
				xor		a
				ld		(msx_play), a
				ld		(msx_stepc), a
				ld		(msx_busy), a
				ld		(msx_vhold + 0), a		; отложенных нот нет
				ld		(msx_vhold + 1), a
				ld		(msx_vhold + 2), a
				ld		hl, msx_sfx
""", 'msx_snd_init')
rep("""msx_silence:	ld		hl, msx_stop
				jp		msx_wlist
""", """				jp		msx_silence				; зеркало: полная тишина (дыра F01E)
""", 'msx_silence')

# 5. msx_play_tune: голые управляющие слова -> msx_tv_mute (заодно бросает владельцев)
rep("""				ld		a, 0x76					; заглушить счётчики 1,2: с эффектов мог остаться тон
				out		(0x08), a
				ld		a, 0xB6
				out		(0x08), a
				ld		a, 1
""", """				call	msx_tv_mute				; заглушить счётчики 1,2 (с эффектов мог остаться тон)
												;  и бросить их владельцев: плеер пишет счётчики
												;  мимо msx_viown/msx_vidiv
				ld		a, 1
""", 'msx_play_tune')

# 6. msx_tv_mute: + сброс владельцев
rep("""msx_tv_mute:			ld		a, 0x76					; управляющее слово БЕЗ делителя: счётчик 1 встал
				out		(0x08), a
				ld		a, 0xB6					; ...и счётчик 2
				out		(0x08), a
				ret
""", """msx_tv_mute:			ld		a, 0x76					; управляющее слово БЕЗ делителя: счётчик 1 встал
				out		(0x08), a
				ld		a, 0xB6					; ...и счётчик 2
				out		(0x08), a
				ld		a, 0xFF					; счётчики встали — владельцев у них нет: первый же
				ld		(msx_viown + 1), a		;  эффект получит управляющее слово и бой кэша
				ld		(msx_viown + 2), a		;  делителя (иначе нота «совпала бы с кэшем» и промолчала)
				ret
""", 'msx_tv_mute')

# 7. msx_sfx_kill: сохранить id (A) и уйти в msx_vhkill
rep("""msx_sfx_kill:	; HL -> слот: освободить, погасить громкость, поднять биты в тени.
				; R7 НЕ пишется — ровно как MSX 0x4402 (иначе лишняя запись в журнале).
				ld		(hl), 0
""", """msx_sfx_kill:	; HL -> слот, A = id: освободить, погасить громкость, поднять биты в тени.
				; R7 НЕ пишется — ровно как MSX 0x4402 (иначе лишняя запись в журнале).
				push	af						; id — для отложенной ноты (msx_vhkill)
				ld		(hl), 0
""", 'msx_sfx_kill: вход')
rep("""				ld		a, (msx_mix)
				or		c
				ld		(msx_mix), a
				ret

msx_sfx_start:""", """				ld		a, (msx_mix)
				or		c
				ld		(msx_mix), a
				pop		af
				jp		msx_vhkill				; отложенная нота: эффект кончился — слили ли его?

msx_sfx_start:""", 'msx_sfx_kill: выход')

# 8. msx_sfx_start: новый эффект в слоте — метка vhold сброшена
rep("""				jp		nz, mss_no			; пока играет мелодия, эффектов нет (на MSX игра стоит)
				ld		a, c
""", """				jp		nz, mss_no			; пока играет мелодия, эффектов нет (на MSX игра стоит)
				call	msx_vhnew			; новый эффект в слоте: метка отложенной ноты сброшена
				ld		a, c
""", 'msx_sfx_start')

# 9. msx_frame_off уезжает в дыру F01E (splice_B2), здесь его нет
rep("""msx_frame_off:	; конец игровой итерации: полное глушение AY (MSX 0x41A6). Мелодию не трогаем.
				ld		a, (msx_play)
				or		a
				ret		nz
				jp		msx_silence
""", '', 'msx_frame_off')

open(P, 'w', encoding='utf-8').write(src)
print('splice B1 ok: wr->зеркало, wlist/stop сняты, snd_init/play_tune -> msx_tv_mute (+viown), '
      'sfx_kill -> msx_vhkill, sfx_start -> msx_vhnew, frame_off уехал в дыру')
