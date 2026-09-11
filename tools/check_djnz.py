#!/usr/bin/env python3
"""Гейт: после `djnz` нельзя читать флаги, выставленные ТЕЛОМ цикла.

У Z80 `djnz` меняет только B — флаги от последней инструкции тела доживают до
выхода из цикла. На i8080 djnz разворачивается в `dec b / jp nz`, и `dec b`
выставляет Z/S/P по счётчику. Значит любой `jp z`/`jr c`/`ret nz`... сразу за
циклом получает мусор — тихо, без единого предупреждения ассемблера.

Так и случилось в Alien 8: `sub_AD66` считает OR всех байт инвентаря
(`xor a / .loop: or (hl) / inc hl / djnz .loop / jp z, game_over`). После
рекомпиляции Z всегда равен 1 (цикл выходит по B==0), и игра уходила в
GAME OVER на первой же итерации главного цикла.

  python3 tools/check_djnz.py build/alien8_8080.asm [ещё...]
"""
import re
import sys

# инструкции, ЗАПИСЫВАЮЩИЕ флаги (после них мусор от dec b уже неважен)
F_W = re.compile(r'^(add|adc|sub|sbc|and|or|xor|cp|inc|dec|rlca|rrca|rla|rra|scf|ccf|neg|daa)\b'
                 r'|^pop\s+af\b', re.I)
# инструкции, ЧИТАЮЩИЕ флаги
F_R = re.compile(r'^(jp|jr|ret|call)\s+(nz|z|nc|c|po|pe|p|m)\b|^(adc|sbc|rla|rra)\b', re.I)
STOP = re.compile(r'^(jp|jr|ret|call)\b', re.I)


def body(line):
    return re.sub(r'^[A-Za-z_.@][\w.@]*:\s*', '', line.split(';')[0].strip())


def main():
    hits = 0
    for path in sys.argv[1:]:
        lines = open(path, encoding='latin-1').read().split('\n')
        for i, raw in enumerate(lines):
            t = body(raw)
            # развёрнутый djnz: `dec b` + `jp nz,метка`
            if not re.fullmatch(r'(?i)dec\s+b', t):
                continue
            nxt = body(lines[i + 1]) if i + 1 < len(lines) else ''
            if not re.match(r'(?i)^jp\s+nz\s*,', nxt):
                continue
            for j in range(i + 2, min(i + 12, len(lines))):
                s = body(lines[j])
                if not s or s.lower().startswith('db'):
                    continue
                if F_R.match(s):
                    hits += 1
                    print("  %s:%d: djnz портит флаги, а через %d команд их читают: %s"
                          % (path, i + 1, j - i - 1, s))
                    break
                if F_W.match(s) or STOP.match(s):
                    break
    print("check_djnz: чтений флагов после djnz %d" % hits)
    return 1 if hits else 0


if __name__ == '__main__':
    sys.exit(main())
