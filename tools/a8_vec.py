# -*- coding: utf-8 -*-
"""Склейка Alien 8 с Вектором-06Ц (цель `vec`): загрузчик, прерывание, палитра, клавиатура,
нативный столбцовый буфер, экран. Делается по §2–4, §7 и §12 рецепта Knight Lore
(~/projects/knightlore-v06c/docs/PORT_RECIPE.md); отличия Alien 8 — в docs/PORT_RECIPE.md.

ЭТАП 4 (эта версия): картинка ч/б, одна плоскость. Заливка, блит и update_screen — ПРОСТЫЕ
байтовые циклы: стековые версии (§12) вводятся этапом 5, и байтовая сборка служит им эталоном
картинки. Звук снят (out (0xFE) убраны) — звук MSX тоже этап 5.

РАСКЛАДКА ПАМЯТИ:
    0x0000-0x0037  загрузчик (di, SP, jp vec_boot)
    0x0038-0x003F  RST 38h -> vec_isr (кадровое прерывание Вектора)
    0x0040-0x009F  scratch эмуляции i8080 + матрица клавиатуры + палитра
    0x00A0-0x00FF  хелперы ldir
    0x0100-0x7EFF  НИЖНИЙ регион: код и данные игры
    0x7F00-0x7FFF  стек (SP = 0x8000, растёт вниз; он же временный `ld sp` в update_sprite_loop)
    0x8000-0x9FFF  ПЛОСКОСТЬ 0 — экран
    0xA000-0xBFFF  ПЛОСКОСТЬ 1 — vidbuf, столбцовый (адрес = база + столбец*256 + 32 + Y)
    0xC000-0xC7FF  защитная зона (вылет печати за столбец 31) + zxaram (мусорное ОЗУ атрибутов)
    0xC800-0xCF87  переменные игры (0x788 = 1928 Б)
    0xD000-0xF0FF  ВЕРХНИЙ регион кода (граница страницы: цепочки print_sprite патчатся по lo-байту)
    0xF100-0xF1FF  reverse_bits_table
    0xF200-0xFFFF  таблицы сдвига (print_sprite адресует страницу константой `or 0xF0`)
"""
import os
import re
import a8_native_logic

A8_STACK   = 0x8000     # SP растёт вниз; главный и временный стек — от одного адреса
A8_VIDBUF  = 0xA000     # плоскость 1
A8_GUARD   = 0xC000     # защитная зона спиллов, там же мусорные атрибуты ZX
A8_VARS    = 0xC800
A8_UPPER   = 0xD000     # верхний регион (кратен странице)
A8_TABLES  = 0xF100
A8_SPR     = 0xE000     # хвост массива спрайтов: верхний регион за блоком Вектора
# Разрез массива спрайтов: с этой метки хвост уезжает в верхний регион (спрайты адресуются
# через sprite_tbl, разрез произволен). Двигать при любом изменении размера кода — судья
# ASSERT'ы нижнего региона (0x7F00) и хвоста спрайтов (0xF100).
A8_SPLIT   = os.environ.get('A8_SPLIT', 'spr_2F')

# ---------------------------------------------------------------------------
# Заголовок: загрузчик, вектор прерывания, scratch.
# ---------------------------------------------------------------------------
VEC_HEADER = """
; ---- Вектор-06Ц: загрузчик (.r0m грузится с 0x0000, PC=0) ----
				ORG		0x0000
				di
				ld		sp, %(stack)#06x
				jp		vec_boot
				ORG		0x0038
				jp		vec_isr				; RST 38h — кадровое прерывание Вектора
; ---- scratch эмуляции i8080 + состояние блока Вектора ----
				ORG		0x0040
vec_kbmat:		DS		8			; матрица клавиатуры Вектора (active-high), заполняет vec_scan
vec_zxrows:		DB		0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF	; 8 рядов ZX (active-low), строит vec_zxbuild
									; 0xFF согласовано с vec_kbmat = 0 и vec_kbchg = 0 (ранний выход)
vec_kbchg:		DS		1			; != 0, если матрица изменилась с прошлого кадра
vec_palreq:		DS		1			; 1 = загрузить «чёрные» записи палитры в ближайшем VBlank
vec_pal:		DS		16			; палитра (индекс = p0<<3|p1<<2|p2<<1|p3)
vec_tmp:		DS		2
z80_ix:			DS		2
z80_iy:			DS		2
z80_af_alt:		DS		2
z80_bc_alt:		DS		2
z80_de_alt:		DS		2
z80_hl_alt:		DS		2
il_tmp:			DS		2
il_tmp2:		DS		2
il_a:			DS		2
il_f:			DS		2			; компактные IX-хелперы: сохранённый AF
il_outstub:		DS		3
a8_seed:		DS		1
a8_blk_off:		DS		2			; upd_42/43: смещения (ix+d), в оригинале патчились в код
a8_visit_bit:	DS		1			; build_screen_objects: номер бита SET n,(HL) (был опкодом)
a8_lines:		DS		1			; print_sprite: высота окна (для оценки бюджета di)
a8_shpg:		DS		1			; print_sprite: страница таблицы сдвига (0 = выровненный путь)
;__PACE_BEG__
pace_el:		DS		1			; ограничитель темпа: кадров с начала итерации (ISR инкрементит, насыщение 255)
pace_acc:		DS		1			; ограничитель темпа: аккумулятор Брезенхэма (дробная часть периода, 1/256 кадра)
;__PACE_END__
__A8_NATIVE_SCRATCH__				ASSERT $ <= 0x00A0
				ORG		0x00A0		; хелперы ldir
"""

# ---------------------------------------------------------------------------
# Блок Вектора: boot, ISR, палитра, клавиатура, бюджет di, экран.
# ---------------------------------------------------------------------------
VEC_TAIL = """
; ===================== БЛОК ВЕКТОРА =====================
vec_boot:		ld		a, 0x88				; 8255: порт A выход (скролл/ряд клавиатуры), порт B выход (бордюр/режим)
				out		(0x00), a
				xor		a
				out		(0x02), a			; бордюр чёрный, режим 256
				ld		a, 0xFF
				out		(0x03), a			; скролл
				ld		a, 0x30				; ВИ53 счётчик 0: режим 0, оба байта — секундомер кадра для vec_di_budget.
				out		(0x08), a			; ПОРТЫ ВИ53 НА ВЕКТОРЕ ПЕРЕСТАВЛЕНЫ: управление 0x08, счётчик 0 — 0x0B
				ld		a, 7
				call	vec_set_pal			; белая палитра (меню)
				ei								; палитру защёлкивает цвет под лучом -> грузим её в VBlank из ISR
vb_wait:		ld		a, (vec_palreq)
				or		a
				jp		nz, vb_wait
				ld		hl, 0x8000			; очистить плоскость 0 (экран)
				ld		bc, 0x2000
vb_clr:			ld		(hl), 0
				inc		hl
				dec		bc
				ld		a, b
				or		c
				jp		nz, vb_clr
				jp		START

; ---- кадровое прерывание: перезарядка секундомера, палитра, клавиатура ----
vec_isr:		push	af
				ld		a, 0xFF				; секундомер кадра (ВИ53 счётчик 0) <- 0xFFFF, вниз на 1.5 МГц
				out		(0x0B), a
				out		(0x0B), a
				push	bc
				push	de
				push	hl
;__PACE_BEG__
				ld		hl, pace_el			; ограничитель темпа: кадров с начала итерации
				inc		(hl)
				jp		nz, vi_pace
				dec		(hl)				; насыщение на 255 (длинная пауза не должна переполнять счётчик)
vi_pace:
;__PACE_END__
				; Записи палитры 15..8 (точка экрана есть) грузятся КАЖДЫЙ кадр: запись защёлкивается
				; цветом под лучом, и одиночная загрузка «по запросу» может частично промахнуться мимо
				; обратного хода. Записи 7..0 (точки нет) — по запросу vec_palreq.
				ld		hl, vec_pal + 15
				ld		e, 0x0F
vb_pal:			ld		a, e
				out		(0x02), a			; индекс = цвет бордюра (луч в обратном ходе)
				ld		a, (hl)
				dec		hl
				out		(0x0C), a
				out		(0x0C), a
				out		(0x0C), a
				out		(0x0C), a
				dec		e
				ld		a, e
				cp		8
				jp		nc, vb_pal
				ld		a, (vec_palreq)
				or		a
				jp		z, vb_pal_done
vb_pal2:		ld		a, e
				out		(0x02), a
				ld		a, (hl)
				dec		hl
				out		(0x0C), a
				out		(0x0C), a
				out		(0x0C), a
				out		(0x0C), a
				dec		e
				jp		p, vb_pal2
				xor		a
				ld		(vec_palreq), a
vb_pal_done:	xor		a
				out		(0x02), a			; бордюр чёрный
				call	vec_scan
				call	vec_zxbuild
				pop		hl
				pop		de
				pop		bc
				pop		af
				ei
				ret

; ---- палитра: A = атрибут комнаты (биты 0..2 = чернила) -> vec_pal + запрос загрузки ----
; Ч/б, одна плоскость: цвет зависит только от p0 (0x8000). Индексы 8..15 = цвет комнаты,
; 0..7 = чёрный. Портит A, BC, HL.
vec_set_pal:	and		7
				ld		c, a
				ld		b, 0
				ld		hl, vec_zxcol
				add		hl, bc
				ld		c, (hl)				; цвет %BBGGGRRR
				ld		hl, vec_pal
				ld		b, 8
vsp_0:			ld		(hl), 0				; 0..7 — фона нет
				inc		hl
				dec		b
				jp		nz, vsp_0
				ld		b, 8
vsp_1:			ld		(hl), c				; 8..15 — цвет комнаты
				inc		hl
				dec		b
				jp		nz, vsp_1
				ld		a, 1
				ld		(vec_palreq), a
				ret
vec_zxcol:		DB		0xFF, 0xC0, 0x07, 0xC7, 0x38, 0xF8, 0x3F, 0xFF	; ZX 0..7: (чёрный->белый) синий красный пурпурный зелёный голубой жёлтый белый

; ---- БЮДЖЕТ di-БЛОКА (§12 рецепта) ----------------------------------------------------------
; Кадровое прерывание Вектора НЕ защёлкивается: если обратный ход пришёлся на di, кадр теряется.
; Секундомер — счётчик 0 ВИ53 (режим 0, ISR перезаряжает 0xFFFF на границе кадра). Здесь читаем
; остаток и, если блок до конца кадра не помещается, ждём прерывания (ei/halt).
; Кадр = 29952 тика (1.5 МГц = 2 такта CPU), порог 0x8D00.
; Вход: DE = оценка длительности блока в тиках. Портит A, HL, флаги; BC/DE целы.
; Вызывать ТОЛЬКО при разрешённых прерываниях (иначе halt навсегда).
vec_di_budget:	xor		a
				out		(0x08), a			; команда защёлки счётчика 0
				in		a, (0x0B)
				ld		l, a
				in		a, (0x0B)
				ld		h, a				; HL = остаток кадра в тиках
				ld		a, l
				sub		e
				ld		a, h
				sbc		a, d
				jp		c, vdb_wait			; ушли в минус — точно не успеваем
				cp		0x8D
				jp		nc, vdb_ok
vdb_wait:		ei
				halt
vdb_ok:			ret

;__PACE_BEG__
; ---- ОГРАНИЧИТЕЛЬ ТЕМПА (потолок скорости игры, §19 рецепта Knight Lore) --------------------
; Итерация главного цикла не может быть короче PACE_INT + PACE_FRC/256 кадров. Дробность даёт
; Брезенхэм: каждую итерацию pace_acc += PACE_FRC, перенос -> лишний кадр. Узор шагов регулярный,
; пачек не бывает. Счётчик кадров pace_el ведёт ISR; здесь ждём, пока он не дорастёт до шага,
; и обнуляем. Ожидание — ТОЛЬКО ei/halt: прерывание Вектора не защёлкивается, под di кадр теряется.
; В тяжёлой комнате (итерация длиннее шага) ожидания нет вообще, темп не трогаем.
; Счётчик 0 ВИ53 НЕ трогается: это секундомер бюджета di (vec_di_budget).
; Вызывается из onscreen_loop (вершина итерации главного цикла), где A, B, HL и флаги мертвы:
; дальше `ld ix, graphic_objs_tbl`, `ld sp`, `ld hl, ret_from_tbl_jp`, `ld a, (ix+24)`,
; `ld bc, upd_sprite_jmp_tbl` — все три регистра переписываются до первого чтения.
vec_pace:		ld		a, (pace_acc)
				add		a, PACE_FRC			; дробная часть периода (1/256 кадра)
				ld		(pace_acc), a
				ld		a, PACE_INT
				adc		a, 0				; A = шаг этой итерации в кадрах
				ld		b, a
				ld		hl, pace_el
vp_e:			ld		a, b
				sub		(hl)				; шаг - прошло кадров
				jp		z, vp_done
				jp		c, vp_done			; прошло больше шага (тяжёлая комната) — не ждём
vp_h:			ei							; halt только при разрешённых прерываниях
				halt
				jp		vp_e
vp_done:		ld		(hl), 0				; отсчёт с этого кадра (сразу после обратного хода)
				ret
;__PACE_END__

; ---- оценка пиксельного цикла print_sprite (§12: модель строки по слотам шины) ---------------
; выровненный путь  52*w + 84 такта  = 26w + 42 тика на строку
; сдвинутый путь   124*w - 36 тактов = 62w - 18 тиков на строку
; Ширину берём из уже записанного патча отката столбца (loc_D10F+1 = w-1), высоту — из a8_lines,
; путь — из a8_shpg (0 = выровненный). Сохраняет ВСЕ регистры: в A8 к моменту вызова в H лежит
; страница таблицы сдвига, в BC — адрес в буфере, в DE — указатель на данные спрайта.
a8_ps_budget:	push	hl
				push	de
				push	bc
				push	af
				ld		a, (a8_shpg)
				or		a
				ld		de, 42				; выровненный: строка = 42 + 26w
				ld		hl, 26
				jp		z, apb_w0
				ld		de, 0xFFEE			; сдвинутый: строка = -18 + 62w
				ld		hl, 62
apb_w0:			ld		a, (loc_D10F+1)		; w-1
				inc		a
				ld		b, a
apb_w:			ld		a, e
				add		a, l
				ld		e, a
				ld		a, d
				adc		a, h
				ld		d, a
				dec		b
				jp		nz, apb_w
				ld		b, d				; BC = тиков на строку
				ld		c, e
				ld		hl, 0
				ld		a, (a8_lines)
				or		a
				jp		z, apb_done
apb_h:			add		hl, bc
				dec		a
				jp		nz, apb_h
apb_done:		ld		a, h
				add		a, 2				; +512 тиков: заголовок блока, возврат SP, ei
				ld		d, a
				ld		e, l
				call	vec_di_budget
				pop		af
				pop		bc
				pop		de
				pop		hl
				ret

; ---- клавиатура: скан матрицы Вектора -> vec_kbmat (active-high) ----
; Цикл развёрнут: непосредственная маска ряда дешевле счётчика и заодно копится отличие от
; прошлого кадра (vec_kbchg) — по нему vec_zxbuild решает, надо ли пересчитывать ряды ZX.
; Ряд 1 Вектора не опрашивается: в vec_kbzx все его восемь записей 0xFF.
; Портит A, BC, HL, флаги.
vec_scan:		ld		a, 0x8A				; порт B на вход
				out		(0x00), a
				ld		hl, vec_kbmat
				ld		b, 0				; накопитель отличий
				ld		a, 0xFE				; ряд 0
				out		(0x03), a
				in		a, (0x02)
				cpl
				ld		c, a
				xor		(hl)
				or		b
				ld		b, a
				ld		(hl), c
				inc		hl
				inc		hl					; ряд 1 не отображён ни на одну клавишу ZX
				ld		a, 0xFB				; ряд 2
				out		(0x03), a
				in		a, (0x02)
				cpl
				ld		c, a
				xor		(hl)
				or		b
				ld		b, a
				ld		(hl), c
				inc		hl
				ld		a, 0xF7				; ряд 3
				out		(0x03), a
				in		a, (0x02)
				cpl
				ld		c, a
				xor		(hl)
				or		b
				ld		b, a
				ld		(hl), c
				inc		hl
				ld		a, 0xEF				; ряд 4
				out		(0x03), a
				in		a, (0x02)
				cpl
				ld		c, a
				xor		(hl)
				or		b
				ld		b, a
				ld		(hl), c
				inc		hl
				ld		a, 0xDF				; ряд 5
				out		(0x03), a
				in		a, (0x02)
				cpl
				ld		c, a
				xor		(hl)
				or		b
				ld		b, a
				ld		(hl), c
				inc		hl
				ld		a, 0xBF				; ряд 6
				out		(0x03), a
				in		a, (0x02)
				cpl
				ld		c, a
				xor		(hl)
				or		b
				ld		b, a
				ld		(hl), c
				inc		hl
				ld		a, 0x7F				; ряд 7
				out		(0x03), a
				in		a, (0x02)
				cpl
				ld		c, a
				xor		(hl)
				or		b
				ld		b, a
				ld		(hl), c
				ld		a, 0x88
				out		(0x00), a
				ld		a, b
				ld		(vec_kbchg), a
				ld		a, 0xFF
				out		(0x03), a			; вернуть скролл
				xor		a
				out		(0x02), a			; вернуть бордюр/режим
				ret

; ---- vec_kbmat -> vec_zxrows (8 байт рядов ZX, бит = 0 если клавиша нажата) ----
; Раз в кадр из ISR; read_key потом только сводит готовые байты. Если матрица не менялась —
; выход сразу (полный обход ~900 тактов против 22).
vec_zxbuild:	ld		a, (vec_kbchg)
				or		a
				ret		z
				ld		hl, vec_zxrows
				ld		a, 0xFF
				ld		b, 8
zb_clr:			ld		(hl), a
				inc		hl
				dec		b
				jp		nz, zb_clr
				ld		hl, vec_kbmat
				ld		de, vec_kbzx
				ld		b, 8
zb_row:			ld		a, (hl)
				or		a
				jp		nz, zb_bits
				ld		a, e				; ряд пуст: пропустить 8 записей
				add		a, 8
				ld		e, a
				ld		a, d				; перенос обязателен: таблица может лечь через границу страницы
				adc		a, 0
				ld		d, a
				jp		zb_next
zb_bits:		ld		c, a
zb_bit:			ld		a, c
				rra
				ld		c, a
				jp		nc, zb_skip
				ld		a, (de)				; запись: биты 7-5 = ряд ZX, биты 4-0 = маска (0 = нажато)
				push	hl
				push	bc
				ld		c, a
				and		0x1F
				ld		b, a
				ld		a, c
				rlca
				rlca
				rlca
				and		7
				ld		hl, vec_zxrows
				add		a, l
				ld		l, a
				ld		a, b
				and		(hl)
				ld		(hl), a
				pop		bc
				pop		hl
zb_skip:		inc		de
				ld		a, c
				or		a
				jp		nz, zb_bit
				dec		de					; добрать до конца восьмёрки (таблица ALIGN 8); декремент
				ld		a, e				; обязателен: при нажатом бите 7 «or 7 : inc de» проскочило бы
				or		7					; целую восьмёрку и все следующие ряды читались бы из чужих записей
				ld		e, a
				inc		de
zb_next:		inc		hl
				dec		b
				jp		nz, zb_row
				; стрелки ряда 0 Вектора -> Z / X / A / Q прямо в рядах ZX
				ld		a, (vec_kbmat+0)
				ld		c, a
				ld		de, vec_arrzx
				ld		b, 4
zb_ar:			ld		a, (de)
				and		c
				inc		de
				ld		a, (de)				; младший байт адреса ряда ZX (ldax/inx флаги не трогают)
				inc		de
				jp		z, zb_arn
				ld		l, a
				ld		h, high vec_zxrows
				ld		a, (de)
				and		(hl)
				ld		(hl), a
zb_arn:			inc		de
				dec		b
				jp		nz, zb_ar
				jp		vec_rpbuild			; ряды готовы — пересчитать готовые ответы read_key
vec_arrzx:		DB		0x10, low (vec_zxrows+0), 0xFD	; влево  -> Z (ряд ZX 0, бит 1)
				DB		0x40, low (vec_zxrows+0), 0xFB	; вправо -> X (ряд ZX 0, бит 2)
				DB		0x20, low (vec_zxrows+1), 0xFE	; вверх  -> A (ряд ZX 1, бит 0)
				DB		0x80, low (vec_zxrows+2), 0xFE	; вниз   -> Q (ряд ZX 2, бит 0)

; ---- готовые ответы read_key по маскам, которыми игра реально пользуется ----
; Значение = cpl(AND выбранных рядов) and 0x1F, то есть всегда <= 0x1F; 0xFF означает
; «маска не считана» и отправляет read_key на общий цикл (ответ остаётся верным, просто медленным).
; У Alien 8 check_user_input пользуется теми же семью масками, что и Knight Lore:
;   0xFE 0x7F 0x7E 0xBD 0xDB 0xE7 0x99; ещё четыре — меню, «любая клавиша» и пауза.
vec_rpbuild:	ld		a, (vec_zxrows+0)
				ld		b, a
				cpl
				and		0x1F
				ld		(vec_rptab+0xFE), a
				ld		a, (vec_zxrows+7)
				ld		c, a
				cpl
				and		0x1F
				ld		(vec_rptab+0x7F), a
				ld		a, b
				and		c
				ld		b, a				; ряд0 & ряд7
				cpl
				and		0x1F
				ld		(vec_rptab+0x7E), a
				ld		a, (vec_zxrows+1)
				ld		c, a
				cpl
				and		0x1F
				ld		(vec_rptab+0xFD), a
				ld		a, (vec_zxrows+6)
				and		c
				ld		c, a				; ряд1 & ряд6
				cpl
				and		0x1F
				ld		(vec_rptab+0xBD), a
				ld		a, (vec_zxrows+2)
				ld		d, a
				cpl
				and		0x1F
				ld		(vec_rptab+0xFB), a
				ld		a, (vec_zxrows+5)
				and		d
				ld		d, a				; ряд2 & ряд5
				cpl
				and		0x1F
				ld		(vec_rptab+0xDB), a
				ld		a, c
				and		d
				ld		e, a				; ряды 1,2,5,6
				cpl
				and		0x1F
				ld		(vec_rptab+0x99), a
				ld		a, (vec_zxrows+3)
				ld		c, a
				cpl
				and		0x1F
				ld		(vec_rptab+0xF7), a
				ld		a, (vec_zxrows+4)
				ld		d, a
				cpl
				and		0x1F
				ld		(vec_rptab+0xEF), a
				ld		a, c
				and		d
				ld		c, a				; ряд3 & ряд4
				cpl
				and		0x1F
				ld		(vec_rptab+0xE7), a
				ld		a, b
				and		c
				and		e
				cpl
				and		0x1F
				ld		(vec_rptab+0x00), a
				ret

				ALIGN 8
vec_kbzx:		__VEC_KBZX__
; ---- таблица ZX-ряд -> клавиши Вектора: 8 рядов x 5 записей (ячейка vec_kbmat, маска) ----
; ZX ряды: 0 SHIFT Z X C V | 1 A S D F G | 2 Q W E R T | 3 1 2 3 4 5 | 4 0 9 8 7 6 | 5 P O I U Y | 6 ENTER L K J H | 7 SPACE SYM M N B
; Вектор: ряд4 @ABCDEFG(биты 0..7) ряд5 HIJKLMNO ряд6 PQRSTUVW ряд7 XYZ[\\]^ПРБ ряд2 0-7 ряд3 8=бит0 9=бит1 ряд0 ВК=бит2
vec_zxmap:		DB	vec_kbmat+7,0x00, vec_kbmat+7,0x04, vec_kbmat+7,0x01, vec_kbmat+4,0x08, vec_kbmat+6,0x40	; SHIFT(нет) Z X C V
				DB	vec_kbmat+4,0x02, vec_kbmat+6,0x08, vec_kbmat+4,0x10, vec_kbmat+4,0x40, vec_kbmat+4,0x80	; A S D F G
				DB	vec_kbmat+6,0x02, vec_kbmat+6,0x80, vec_kbmat+4,0x20, vec_kbmat+6,0x04, vec_kbmat+6,0x10	; Q W E R T
				DB	vec_kbmat+2,0x02, vec_kbmat+2,0x04, vec_kbmat+2,0x08, vec_kbmat+2,0x10, vec_kbmat+2,0x20	; 1 2 3 4 5
				DB	vec_kbmat+2,0x01, vec_kbmat+3,0x02, vec_kbmat+3,0x01, vec_kbmat+2,0x80, vec_kbmat+2,0x40	; 0 9 8 7 6
				DB	vec_kbmat+6,0x01, vec_kbmat+5,0x80, vec_kbmat+5,0x02, vec_kbmat+6,0x20, vec_kbmat+7,0x02	; P O I U Y
				DB	vec_kbmat+0,0x04, vec_kbmat+5,0x10, vec_kbmat+5,0x08, vec_kbmat+5,0x04, vec_kbmat+5,0x01	; ENTER L K J H
				DB	vec_kbmat+7,0x80, vec_kbmat+7,0x10, vec_kbmat+5,0x20, vec_kbmat+5,0x40, vec_kbmat+4,0x04	; SPACE SYM(\\) M N B

; ===================== ЭКРАН (нативный столбцовый буфер) =====================
; Буфер — плоскость 1 (0xA000-0xBFFF), в раскладке экрана Вектора:
;   адрес = база + (X/8)*256 + (32 + Y), Y растёт ВВЕРХ (0 = низ поля). Экран = буфер - 0x2000.
; Строки 0..31 и 224..255 каждого столбца лежат вне картинки.

calc_screen_buffer_addr:	; BC = (B = Y, C = X в пикселях) -> BC = адрес в буфере. HL цел, A портится.
				ld		a, c
				rrca
				rrca
				rrca
				and		0x1F
				add		a, high vidbuf
				ld		c, a
				ld		a, b
				add		a, 32
				ld		b, c
				ld		c, a
				ret

BC_to_Attr_In_DE:			; BC = (B = Y, C = X) -> DE = адрес в плоскости 0 (экран). HL цел.
				ld		a, c
				rrca
				rrca
				rrca
				and		0x1F
				add		a, 0x80
				ld		d, a
				ld		a, b
				add		a, 32
				ld		e, a
				ret

; ---- заливка окна: HL = буфер, B = ширина (столбцов), C = строк, A = значение ----
; Нулевой размер — выход (иначе 256 столбцов затирают память). Окно вне буфера — пустая
; операция: по этим адресам игра пишет АТРИБУТЫ ZX (colour_panel, colour_something),
; в ч/б их писать некуда. Вылет за столбец 31 обрезается: за ним чужая память.
; СТЕКОВАЯ ЗАЛИВКА (§12 рецепта KL): столбец буфера сплошной, поэтому SP наводится на конец
; окна и push кладёт 2 байта за 11 тактов — 5.5 такта/байт против 27 у байтового цикла.
; Число push на столбец известно на входе, поэтому цепочка из 16 push развёрнута целиком,
; а вход в неё и хвост нечётной высоты считаются ОДИН раз на вызов патчем иммедиатов.
; SP уходит в картинку => весь блок под di (иначе ISR положит свои регистры в буфер),
; стек игры на это время — в fw_sp.
; Байтовым циклом (без di) остаются два случая:
;   - окно выше цепочки (строк > 32);
;   - конец окна переваливает за конец страницы: у байтового цикла inc l заворачивается внутри
;     столбца, а SP ушёл бы в соседний столбец. (Сейчас не встречается: строки буфера 32..223.)
fill_window:
				inc		b
				dec		b
				ret		z
				inc		c
				dec		c
				ret		z
				push	af
				ld		d, a				; D = значение заливки
				ld		e, a				; оба байта пары
				ld		a, h
				cp		high vidbuf
				jp		c, fw_ret			; ниже буфера — это адрес атрибута ZX, писать некуда
				cp		high vidbuf + 32
				jp		nc, fw_ret			; выше буфера
				ld		a, c
				cp		33
				jp		nc, fw_slow			; окно выше цепочки
				ld		a, l
				ld		(fw_lo+1), a		; нижняя строка окна (хвост нечётной высоты)
				add		a, c
				jp		c, fw_slow			; конец окна за страницей — SP ушёл бы в чужой столбец
				ld		(fw_end+1), a		; конец окна = SP на входе в столбец
				ld		a, h
				ld		(fw_pg+1), a		; страница первого столбца
				ld		a, c
				or		a
				rra							; A = число push, CY = нечётная высота
				ld		c, a				; высота дальше не нужна
				ld		hl, fw_next
				jp		nc, fw_ev
				ld		hl, fw_lo
fw_ev:			ld		(fw_odd+1), hl		; хвост столбца: нижний байт или пропуск
				ld		hl, fw_pend			; блок цепочки — 1 байт (push de)
				ld		a, l
				sub		c
				ld		l, a
				ld		a, h
				sbc		a, 0
				ld		h, a
				ld		(fw_ent+1), hl		; вход в цепочку = конец минус число push
				ld		hl, 0
				add		hl, sp
				ld		(fw_sp), hl			; стек игры
				ld		c, b				; C = столбцов (B занят страницей столбца)
				push	de					; бюджет кадра: 256 тиков ВИ53 на столбец.
				ld		d, c				; Факт по слотам шины: столбец = 4h+56 тиков,
				ld		e, 0				; при h <= 32 (условие быстрого пути) это <= 184 < 256
				call	vec_di_budget
				pop		de
				di
fw_pg:			ld		b, 0				; патч: страница столбца
fw_col:			ld		h, b
fw_end:			ld		l, 0				; патч: конец окна
				ld		sp, hl				; push пойдёт вниз по столбцу
fw_ent:			jp		fw_pend				; патч: вход в цепочку
__A8_FW_CHAIN__
fw_pend:
fw_odd:			jp		fw_next				; патч: fw_next или fw_lo
fw_lo:			ld		l, 0				; патч: нижняя строка окна
				ld		h, b
				ld		(hl), d
fw_next:		inc		b
				ld		a, b
				cp		high vidbuf + 32	; за столбцом 31 — стоп
				jp		z, fw_done
				dec		c
				jp		nz, fw_col
fw_done:		ld		hl, (fw_sp)
				ld		sp, hl
				ei
fw_ret:			pop		af
				ret
fw_sp:			DS		2					; стек игры на время захвата SP

; окно выше 32 строк (или с концом за страницей): прежний байтовый цикл, SP не трогаем
fw_slow:		ld		e, l				; E = первая строка окна
fw_scol:		ld		l, e
				push	bc
				ld		b, c				; строк в столбце
fw_srow:		ld		(hl), d
				inc		l
				dec		b
				jp		nz, fw_srow
				pop		bc
				inc		h
				ld		a, h
				cp		high vidbuf + 32	; за столбцом 31 — стоп
				jp		z, fw_ret
				dec		b
				jp		nz, fw_scol
				jp		fw_ret

; ---- блит буфер -> экран: HL = буфер, DE = экран, B = строк, C = ширина (столбцов) ----
; СТЕКОВЫЙ БЛИТ (§12 рецепта KL): SP наводится на начало окна в столбце буфера, pop забирает
; 2 байта за 10 тактов, приёмник адресуется через HL — 17 тактов на байт против 39 у байтового
; цикла. Число pop на столбец известно на входе, поэтому цепочка из 16 блоков развёрнута целиком,
; а вход в неё считается ОДИН раз на вызов: вход = конец − 5*N (блок цепочки 5 байт, НЕ 1 —
; «конец − N» разъезжает картинку). SP уходит в картинку => блок под di, стек игры в bts_sp.
; Смещения окна в буфере (L) и на экране (E) патчатся ПОРОЗНЬ: у всех вызовов они совпадают
; (calc_screen_buffer_addr и BC_to_Attr_In_DE считаются от одного BC), но зависимости нет.
; Байтовым циклом без di остаются окна выше 32 строк и окна, чей конец переваливает за конец
; страницы буфера (у байтового цикла inc l заворачивается внутри столбца, у SP — нет).
blit_to_screen:
				inc		b
				dec		b
				ret		z
				inc		c
				dec		c
				ret		z
				ld		a, h
				cp		high vidbuf
				ret		c
				cp		high vidbuf + 32
				ret		nc
				ld		a, b
				cp		33
				jp		nc, bts_slow		; окно выше цепочки
				ld		a, l
				add		a, b
				jp		c, bts_slow			; конец окна за страницей — SP ушёл бы в чужой столбец
				ld		a, l
				ld		(bts_off+1), a		; смещение окна в столбце буфера
				ld		a, e
				ld		(bts_soff+1), a		; смещение окна в столбце экрана
				ld		a, h
				ld		(bts_pg+1), a		; страница буфера
				sub		d
				ld		(bts_dif+1), a		; страница экрана = страница буфера минус это
				ld		a, b
				or		a
				rra							; A = число pop, CY = нечётная высота
				ld		b, a
				ld		hl, bts_next
				jp		nc, bts_ev
				ld		hl, bts_lo
bts_ev:			ld		(bts_odd+1), hl		; хвост столбца: последний байт или пропуск
				ld		a, b				; блок цепочки — 5 байт, считаем 5*pop
				add		a, a
				add		a, a
				add		a, b
				ld		b, a
				ld		hl, bts_pend
				ld		a, l
				sub		b
				ld		l, a
				ld		a, h
				sbc		a, 0
				ld		h, a
				ld		(bts_go+1), hl		; вход в цепочку = конец минус 5*число pop
				ld		hl, 0
				add		hl, sp
				ld		(bts_sp), hl		; стек игры
				ld		h, c				; бюджет кадра: 512 тиков ВИ53 на столбец.
				ld		l, 0				; Факт по слотам шины: столбец = 11h+64 тика,
				add		hl, hl				; при h <= 32 (условие быстрого пути) это <= 416 < 512
				ex		de, hl
				call	vec_di_budget
				di
bts_pg:			ld		b, 0				; патч: страница буфера
bts_col:		ld		h, b
bts_off:		ld		l, 0				; патч: смещение окна в буфере
				ld		sp, hl				; SP = источник, pop идёт вверх по столбцу
				ld		a, b
bts_dif:		sub		0x20				; патч: буфер -> экран
				ld		h, a
bts_soff:		ld		l, 0				; патч: смещение окна на экране
bts_go:			jp		bts_pend			; патч: вход в цепочку
__A8_BTS_CHAIN__
bts_pend:
bts_odd:		jp		bts_next			; патч: bts_next или bts_lo
bts_lo:			pop		de					; нечётная высота: последний байт (D не нужен)
				ld		(hl), e
bts_next:		inc		b
				ld		a, b
				cp		high vidbuf + 32	; за столбцом 31 — стоп
				jp		z, bts_done
				dec		c
				jp		nz, bts_col
bts_done:		ld		hl, (bts_sp)
				ld		sp, hl
				ei
				ret
bts_sp:			DS		2					; стек игры на время захвата SP

; окно выше 32 строк (или с концом за страницей): прежний байтовый цикл, SP не трогаем
bts_slow:
bts_scol:		push	bc
				push	hl
				push	de
bts_srow:		ld		a, (hl)
				ld		(de), a
				inc		l
				inc		e
				dec		b
				jp		nz, bts_srow
				pop		de
				pop		hl
				pop		bc
				inc		h
				inc		d
				ld		a, h
				cp		high vidbuf + 32	; за столбцом 31 — стоп
				ret		z
				dec		c
				jp		nz, bts_scol
				ret

; ---- весь буфер (строки 32..223 всех 32 столбцов) -> плоскость 0 ----
; СТЕКОВАЯ ВЕРСИЯ, столбец за столбцом: SP = начало окна в столбце буфера, pop забирает 2 байта
; за 10 тактов, приёмник — через HL: 34 такта на 2 байта против 78 у байтового цикла (17 против
; 39 на байт). Буфер НЕ обнуляется: оригинал Alien 8 (0xCE8B) просто копирует ldir'ом, в отличие
; от Knight Lore, где update_screen заодно чистил буфер.
; SP уходит в картинку => столбец идёт под di, стек игры — в us_sp, бюджет — на столбец.
update_screen:	ld		hl, 0
				add		hl, sp
				ld		(us_sp), hl			; стек игры на время захвата SP
				ld		c, high vidbuf		; C = страница столбца буфера
us_col:			ld		a, c
				ld		(us_src+1), a
				sub		0x20				; буфер -> экран
				ld		(us_dst+1), a		; страница плоскости 0
				ld		de, 2432			; бюджет столбца в тиках ВИ53 (факт по distat_vec: 2274,
											; разброса нет — столбец всегда полный, 192 байта)
				call	vec_di_budget
				di
us_src:			ld		h, 0				; патч: страница буфера
				ld		l, 32
				ld		sp, hl				; SP = источник, pop идёт вверх по окну
us_dst:			ld		h, 0				; патч: страница экрана
				ld		l, 32				; HL = приёмник
				ld		b, 12				; 12 * 8 * 2 = 192 строки
us_row:
__A8_US_CHAIN__
				dec		b
				jp		nz, us_row
				ld		hl, (us_sp)
				ld		sp, hl
				ei
				inc		c
				ld		a, c
				cp		high vidbuf + 32	; за столбцом 31 — стоп
				jp		nz, us_col
				ret
us_sp:			DS		2					; стек игры на время захвата SP

; ---- read_key: A = маска рядов ZX -> A = cpl(AND рядов) and 0x1F, как в оригинале ----
; Ряды ZX готовит ISR (vec_zxbuild) раз в кадр, ответы для живых масок посчитаны вперёд
; (vec_rpbuild): чтение таблицы 70 тактов против ~500 у общего цикла.
read_key:		push	hl
				ld		l, a
				ld		h, high vec_rptab
				ld		a, (hl)
				inc		a
				jp		z, rk_slow
				dec		a
				pop		hl
				ret
rk_slow:		ld		a, l
				pop		hl
				push	hl
				push	bc
				push	de
				ld		c, a
				ld		hl, vec_zxrows
				ld		b, 8
				ld		d, 0xFF
rk_row:			ld		a, c
				rra
				ld		c, a
				jp		c, rk_next
				ld		a, d
				and		(hl)
				ld		d, a
rk_next:		inc		hl
				dec		b
				jp		nz, rk_row
				ld		a, d
				cpl
				and		0x1F
				pop		de
				pop		bc
				pop		hl
				ret
; End of function read_key

				ALIGN 256
vec_rptab:		DS		256, 0xFF			; готовые ответы read_key; 0xFF = «не считано»
				ASSERT $ <= 0xe000	; блок Вектора не должен налезть на хвост спрайтов
"""


def _sub(src, pat, repl, name, count=1, flags=re.M):
    src, n = re.subn(pat, lambda m: repl, src, count=count, flags=flags)
    assert n == count, "a8_vec: не найдено (%s): %d" % (name, n)
    return src


def _kbzx_table(tail):
    """vec_kbzx: 64 байта (ряд Вектора*8 + бит) -> (ряд ZX<<5 | маска 5 бит), строится из vec_zxmap."""
    kbzx = [0xFF] * 64
    rows = re.findall(r'DB\t((?:vec_kbmat\+\d,0x[0-9A-Fa-f]{2},?[ \t]*){5})', tail)
    assert len(rows) == 8, "vec_zxmap: ожидалось 8 рядов, найдено %d" % len(rows)
    for zr, line in enumerate(rows):
        for zb, (vr, mask) in enumerate(re.findall(r'vec_kbmat\+(\d),0x([0-9A-Fa-f]{2})', line)):
            m = int(mask, 16)
            if m == 0:
                continue
            vb = m.bit_length() - 1
            assert m == 1 << vb, (vr, mask)
            kbzx[int(vr) * 8 + vb] = (zr << 5) | (0x1F & ~(1 << zb))
    return "DB\t" + ", ".join("0x%02X" % b for b in kbzx) + "\t; (ряд Вектора*8+бит) -> ряд ZX<<5 | маска"


def _linear_to_col(n):
    """Константа vidbuf+N: линейная раскладка ZX (row*32+col) -> столбцовая (col*256 + 32 + row)."""
    row, col = divmod(n, 32)
    return col * 256 + 32 + row


def glue(src):
    """Правки исходника ZX под Вектор. Вызывается ДО трансляции в i8080."""
    # ---------------- раскладка ----------------
    src = _sub(src, r'^        ORG 0x4000\nzxvram:\n        DS 0x1800\n',
               "zxvram:         equ zxaram - 0x1700   ; база для calc_attrib_addr; сам битмап на Векторе не нужен\n",
               'zxvram')
    src = _sub(src, r'^        ORG 0x5800\nzxaram:',
               "        ORG %#06x   ; мусорное ОЗУ атрибутов ZX в защитной зоне\nzxaram:" % (A8_GUARD,), 'zxaram')
    src = _sub(src, r'^        ORG 0x5B00\nseed_1:',
               "        ORG %#06x\nseed_1:" % A8_VARS, 'переменные')
    # конец блока переменных (бывший адрес font) — ограничитель «конец таблицы объектов»
    src = _sub(src, r'^        ORG 0x6288\nfont:',
               "a8_vars_end:\n        ASSERT $ <= %#06x   ; переменные не должны налезть на верхний регион\n"
               "        ORG 0x0100   ; НИЖНИЙ регион: код и данные игры\nfont:" % A8_UPPER, 'код')
    n_end = src.count("ld bc, font") + src.count("ld hl, font\n")
    assert n_end == 2, n_end
    src = src.replace("ld bc, font", "ld bc, a8_vars_end")
    src = src.replace("ld hl, font\n", "ld hl, a8_vars_end\n")
    src = a8_native_logic.presub(src)
    # буфер: плоскость 1; за ним — верхний регион кода
    src = _sub(src, r'^        ORG 0xD200\nvidbuf:\n        DS 0x1800\n',
               "vidbuf:         equ %#06x   ; ПЛОСКОСТЬ 1 (столбцовый буфер)\n"
               "        ASSERT $ <= %#06x   ; нижний регион не должен дорасти до стека\n"
               "        ORG %#06x   ; ВЕРХНИЙ регион кода\n" % (A8_VIDBUF, A8_STACK - 0x100, A8_UPPER),
               'vidbuf')
    # стек: `ld sp,0xF100` (главный он же временный в update_sprite_loop)
    assert src.count("ld sp, 0xF100") == 1
    src = src.replace("ld sp, 0xF100", "ld sp, %#06x" % A8_STACK)

    # хвост массива спрайтов — в верхний регион (нижний не влезает в 0x0100..0x7F00)
    src = _sub(src, r'^%s:\n' % A8_SPLIT,
               "a8_low_resume:  equ $   ; сюда вернётся нижний регион\n"
               "        ORG %#06x   ; ВЕРХНИЙ регион: хвост массива спрайтов\n%s:\n" % (A8_SPR, A8_SPLIT),
               'разрез спрайтов')
    src = _sub(src, r'^START:\n',
               "        ASSERT $ <= %#06x   ; хвост спрайтов не должен налезть на таблицы сдвига\n"
               "        ORG a8_low_resume   ; назад в нижний регион\nSTART:\n" % A8_TABLES,
               'возврат в нижний регион')

    # ---------------- КОД, ЛЕЖАЩИЙ В ДАННЫХ (как в цели lockstep) ----------------
    old = "        DB 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0xAF, 0x32, 0x1E, 0x5B, 0xDD, 0xE5, 0xFD, 0xE5\n"
    assert src.count(old) == 1, 'пролог в objects_to_draw'
    src = src.replace(old,
        "        DB 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        "a8_cdo_prolog:   ; пролог calc_display_order_and_render лежал в буфере как данные\n"
        "        xor a\n        ld (rendered_objs_cnt), a\n        push ix\n        push iy\n", 1)
    assert src.count("call objects_to_draw+0x40") == 1
    src = src.replace("call objects_to_draw+0x40", "call a8_cdo_prolog", 1)

    # ---------------- АДРЕСА, ЗАПИСАННЫЕ ЧИСЛОМ ----------------
    for num, sym, cnt in (('0x5C08', 'other_objs_here', 2),
                          ('0x5B36', 'unk_5B36', 1),
                          ('0x5B3A', 'unk_5B3A', 2),
                          ('0x5B40', 'unk_5B40', 1),
                          ('0x5B41', 'byte_5B41', 1),
                          ('0x7827', 'sprite_tbl', 1),
                          ('0xB6AD', 'byte_B6A9+4', 1),
                          ('0xB108', 'sub_B0E7+0x21', 1)):
        pat = re.compile(r'(?m)^(        ld (?:hl|de|bc|iy|ix), )' + num + r'\b')
        src, n = pat.subn(lambda m: m.group(1) + sym, src)
        assert n == cnt, (num, n, cnt)

    # ---------------- ЖЕЛЕЗО ZX ----------------
    # бипер и бордюр: звук этапа 5 (MSX -> AY/ВИ53), пока молчим
    src = _sub(src, r'^        out \(0xFE\), a\n', "", 'out (0xFE)', count=5)
    # Kempston: джойстика нет
    src = _sub(src, r'^        in a, \(0x1F\)\n', "        ld a, 0   ; Kempston: джойстика нет\n", 'kempston')
    # старый read_key (ULA) — долой, новый в блоке Вектора
    src = _sub(src, r'^read_key:\n.*?; End of function read_key\n', "", 'read_key', flags=re.M|re.S)
    # очистка «экрана ZX» -> плоскость 0
    src = _sub(src, r'^        ld hl, zxvram\n        ld bc, 0x1800\n',
               "        ld hl, 0x8000   ; Вектор: плоскость 0 целиком\n        ld bc, 0x2000\n", 'clear_scrn')

    # ---------------- ЭКРАН: старые процедуры долой ----------------
    src = _sub(src, r'^calc_screen_buffer_addr:\n.*?; End of function calc_screen_buffer_addr\n', "",
               'старый calc_screen_buffer_addr', flags=re.M|re.S)
    src = _sub(src, r'^BC_to_Attr_In_DE:\n.*?; End of function BC_to_Attr_In_DE\n', "",
               'старый BC_to_Attr_In_DE', flags=re.M|re.S)
    src = _sub(src, r'^update_screen:\n.*?; End of function update_screen\n', "",
               'старый update_screen', flags=re.M|re.S)
    src = _sub(src, r'^blit_to_screen:\n.*?; End of function blit_to_screen\n', "",
               'старый blit_to_screen', flags=re.M|re.S)
    src = _sub(src, r'^fill_window:\n.*?        djnz loc_BF95\n        ret\n', "",
               'старый fill_window', flags=re.M|re.S)
    # очистка буфера: только строки 32..223 всех 32 столбцов
    src = _sub(src, r'^clear_scrn_buffer:\n        ld bc, 0x1800\n        ld hl, vidbuf\n        ld e, 0\n        jr fill_mem\n',
               "clear_scrn_buffer:   ; столбцовый буфер: строки 32..223 всех 32 столбцов\n"
               "        ld hl, vidbuf+32\n        ld b, 32\n"
               "csb_col:\n        ld c, 192\n        xor a\n"
               "csb_r:\n        ld (hl), a\n        inc l\n        dec c\n        jr nz, csb_r\n"
               "        inc h\n        ld l, 32\n        djnz csb_col\n        ret\n", 'clear_scrn_buffer')
    # константы vidbuf+N: линейная раскладка -> столбцовая
    src, nconv = re.subn(r'vidbuf\+0x([0-9A-Fa-f]+)',
                         lambda m: "vidbuf+0x%X" % _linear_to_col(int(m.group(1), 16)), src)
    assert nconv == 7, nconv
    # sub_AD66: мигающая рамка счётчика «LIGHT YEARS» инвертирует 8 байт буфера с шагом +32
    # (в ЛИНЕЙНОЙ раскладке ZX это следующая строка того же столбца). В столбцовом буфере шаг
    # строки = +1 в младшем байте. Без правки семь из восьми байт ложились мимо окна блита,
    # оставались в буфере и всплывали на update_screen двумя штрихами у правого края
    # (на ZX их прятал атрибут: чернила = фон, §10 рецепта KL).
    src = _sub(src, r'^        ld b, 8\n        ld de, 0x20[^\n]*\nloc_AD8B:\n        ld a, \(hl\)\n'
                    r'        cpl\n        ld \(hl\), a\n        add hl, de\n',
               "        ld b, 8\n"
               "loc_AD8B:\n        ld a, (hl)\n        cpl\n        ld (hl), a\n"
               "        inc l   ; столбцовый буфер: следующая строка (в ZX было +32)\n",
               'sub_AD66: шаг строки в буфере')

    # print_8x8: строка ниже = dec l, следующий символ = +0x108
    src = _sub(src, r'^        push bc\n        ld bc, 0xFFE0\n        add hl, bc\n        pop bc\n'
                    r'        djnz loc_BC03\n        pop de\n        ld bc, 0x101\n',
               "        dec l   ; столбцовый буфер: строка ниже\n"
               "        djnz loc_BC03\n        pop de\n"
               "        ld bc, 0x108   ; следующий символ: +столбец, назад на 8 строк\n", 'print_8x8', flags=re.M|re.S)

    # ---------------- print_sprite под столбцовый буфер ----------------
    i = src.index("\nprint_sprite:\n") + 1
    j = src.index("; =============== S U B R O U T I N E ===", i)
    ps = src[i:j]
    # шаг вправо: +256 вместо +1
    n_inc = ps.count("        inc bc\n")
    assert n_inc == 9, n_inc      # 4 в выровненной цепочке + 5 в сдвинутой
    ps = ps.replace("        inc bc\n", "        inc b\n")
    # переход на строку выше: откат столбца на w-1 и +1 к строке
    old_adv = ("loc_D10E:\n        ld a, c\nloc_D10F:\n        add a, 0\n        ld c, a\n"
               "        ld a, b\n        adc a, 0\n        ld b, a\n")
    assert old_adv in ps, 'print_sprite: переход строки'
    ps = ps.replace(old_adv,
        "loc_D10E:\n        ld a, b\nloc_D10F:\n        sub 0   ; патч: откат столбца на w-1\n"
        "        ld b, a\n        inc c\n", 1)
    # патч отката: было 0x22 - (w+1) для линейной строки в 32 байта
    old_pat = "        ld a, b\n        cpl\n        add a, 0x22   ; '\"'\n        ld (loc_D10F+1), a\n"
    assert old_pat in ps, 'print_sprite: расчёт патча строки'
    ps = ps.replace(old_pat,
        "        ld a, b\n        dec a   ; столбцовый буфер: откат столбца на w-1\n        ld (loc_D10F+1), a\n", 1)
    # страница таблицы сдвига -> ещё и в ячейку (по ней a8_ps_budget узнаёт путь)
    old_shp = "        or 0xF0   ; 'ð'\n        ld h, a\n"
    assert old_shp in ps, 'print_sprite: страница таблицы сдвига'
    ps = ps.replace(old_shp, "        or 0xF0   ; 'ð'\n        ld h, a\n        ld (a8_shpg), a\n", 1)
    old_al = "loc_D07E:\n        ld a, (de)\n"
    assert old_al in ps, 'print_sprite: выровненный путь'
    ps = ps.replace(old_al,
        "loc_D07E:\n        ld (a8_shpg), a   ; сюда пришли по jr z: A = 0 (выровненный путь)\n"
        "        ld a, (de)\n", 1)
    src = src[:i] + ps + src[j:]
    return src


def glue_i8080(src):
    """Правки, нужные только после трансляции в i8080 (нет ex af,af', jr стал jp)."""
    # счётчик строк: у i8080 нет теневого A. C — младший байт адреса в буфере, то есть номер
    # строки, и он и так растёт на строку: сравниваем его со «строкой за последней».
    src = _sub(src, r'^loc_D0B9:\n        ex af, af\'\n        ld a, \(bc\)\n',
               "loc_D0B9:\n        ld a, (bc)\n", 'print_sprite: голова цикла', flags=re.M|re.S)
    src = _sub(src, r'^        ex af, af\'\n        dec a\n        jp nz, loc_D0B9\n',
               "        ld a, c\nps_end:\n        cp 0   ; патч заголовка: строка за последней (32+Y+h)\n"
               "        jp nz, loc_D0B9\n", 'print_sprite: хвост цикла', flags=re.M|re.S)
    # вход в цепочку: у i8080 `jr` стал `jp nn`, патчится младший байт адреса
    src = _sub(src, r'^        neg\n        add a, 0x50   ; \'P\'\n',
               "        neg\n        add a, 0x50   ; 'P'\n"
               "        add a, low (loc_D0BB+3)   ; i8080: jp — младший байт адреса входа\n",
               'print_sprite: вход сдвинутой цепочки', flags=re.M|re.S)
    src = _sub(src, r'^        neg\n        sub 6\n        jr loc_D04B\n',
               "        neg\n        sub 6\n"
               "        add a, low (loc_D0BB+3)   ; i8080: jp — младший байт входа\n"
               "        jr loc_D04B\n", 'print_sprite: вход выровненной цепочки', flags=re.M|re.S)
    # высота окна, конец цикла, бюджет кадра и di вокруг захвата SP
    src = _sub(src, r'^        call calc_screen_buffer_addr\n        ld a, \(ix\+25\)[^\n]*\n        ld \(tmp_SP\), sp\n',
               "        call calc_screen_buffer_addr\n"
               "        ld a, (ix+25)   ; высота окна\n"
               "        ld (a8_lines), a   ; её читает a8_ps_budget\n"
               "        add a, c\n"
               "        ld (ps_end+1), a   ; строка за последней: конец пиксельного цикла\n"
               "        call a8_ps_budget   ; хватит ли остатка кадра на пиксельный цикл под di\n"
               "        di   ; SP уходит в данные спрайта — прерывание испортило бы их\n"
               "        ld (tmp_SP), sp\n", 'print_sprite: бюджет и di')
    src = _sub(src, r'^        ld sp, \(tmp_SP\)\n        ret\n',
               "        ld sp, (tmp_SP)\n        ei\n        ret\n", 'print_sprite: ei')
    # цепочки должны лежать в ОДНОЙ странице: патчится только младший байт `jp`
    # ---- цепочки пиксельного цикла -> НАЧАЛО ВЕРХНЕГО РЕГИОНА ----
    # Вход в цепочку патчится ТОЛЬКО младшим байтом `jp` (loc_D0BB+1), поэтому обе цепочки
    # обязаны лежать в одной странице. Начало верхнего региона кратно 256 по построению —
    # ALIGN на месте съел бы до 255 байт нижнего региона, которых нет.
    beg = "        jr loc_D04B\n"
    assert src.count(beg) == 1, 'print_sprite: начало выровненной цепочки'
    a = src.index(beg) + len(beg)
    end = "        ld sp, (tmp_SP)\n        ei\n        ret\n"
    assert src.count(end) == 1, 'print_sprite: конец пиксельного цикла'
    b = src.index(end, a) + len(end)
    chain = ("; ---- цепочки print_sprite: начало верхнего региона = граница страницы ----\n"
             "pixel_chain_aligned:   ; выровненная цепочка (своей метки в оригинале нет — иначе профиль\n"
             "               ; относит её такты к предыдущей метке, то есть к a8_vars_end)\n"
             + src[a:b]
             + "        ASSERT high (loc_D0BB) == high (loc_D10E)   ; обе цепочки в одной странице\n"
             + "__A8_HELPERS__\n")
    src = src[:a] + src[b:]
    src = _sub(src, r'^        ORG 0x[0-9A-Fa-f]+   ; ВЕРХНИЙ регион кода\n',
               "        ORG %#06x   ; ВЕРХНИЙ регион кода\n" % A8_UPPER + chain, 'перенос цепочек')
    return src


def hooks(src):
    """Крючки Вектора в логике игры: палитра комнаты и белое меню."""
    # палитра комнаты ставится ВМЕСТЕ с картинкой: первый показ новой комнаты — этот update_screen
    src = _sub(src, r'^loc_A724:\n        xor a\n        ld \(render_status_info\), a\n        call update_screen\n',
               "loc_A724:\n        xor a\n        ld (render_status_info), a\n        call update_screen\n"
               "        ld a, (curr_room_attrib)   ; палитра комнаты — вместе с картинкой\n"
               "        call vec_set_pal\n", 'палитра комнаты')
    src = _sub(src, r'^do_menu_selection:\n',
               "do_menu_selection:\n        ld a, 7   ; меню белое\n        call vec_set_pal\n", 'палитра меню')
    return src


def header():
    return VEC_HEADER % {'stack': A8_STACK}


def tail():
    t = VEC_TAIL
    t = t.replace("__VEC_KBZX__", _kbzx_table(t), 1)
    # цепочки развёрнутых стековых операций (§12): вход считается по высоте окна, см. fill_window
    t = _sub(t, r'^__A8_FW_CHAIN__\n', "fw_ch:\n" + "\t\t\t\tpush\tde\n" * 16, 'цепочка fw')
    t = _sub(t, r'^__A8_US_CHAIN__\n',
             "\t\t\t\tpop\t\tde\n\t\t\t\tld\t\t(hl), e\n\t\t\t\tinc\t\tl\n"
             "\t\t\t\tld\t\t(hl), d\n\t\t\t\tinc\t\tl\n" * 8, 'цепочка us')
    t = _sub(t, r'^__A8_BTS_CHAIN__\n',
             "bts_ch:\n" + "\t\t\t\tpop\t\tde\n\t\t\t\tld\t\t(hl), e\n\t\t\t\tinc\t\tl\n"
             "\t\t\t\tld\t\t(hl), d\n\t\t\t\tinc\t\tl\n" * 16, 'цепочка bts')
    return t
