#!/usr/bin/env python3
"""Листинг ASxxxx (tcdev, Alien 8 v0.9a1) -> исходник для sjasmplus.

    python3 tools/a8_lst2asm.py <lst> <out.asm>

Правила перевода синтаксиса ASxxxx -> sjasmplus:
    #выражение      -> выражение      (непосредственный операнд)
    N(ix)           -> (ix+N)         (индексная адресация)
    .db/.dw/.ds     -> DB/DW/DS
    .ascii 'текст'  -> DB "текст"
    .org N          -> ORG N
    .area/.hd64     -> выбрасываются
Флаги условий (NZ, Z, NC, C, PO, PE, P, M) приводятся к нижнему регистру.

Попутно ведётся собственный счётчик адреса и сверяется с адресом в листинге —
это ловит любую директиву, размер которой переведён неверно.
"""
import re
import sys
from a8_lst import parse, strip_comment, split_label

# ---- длины инструкций Z80 для собственного счётчика адреса --------------
FLAGS = {'nz', 'z', 'nc', 'c', 'po', 'pe', 'p', 'm'}


def conv_operand(op):
    """ASxxxx -> sjasmplus для одного операнда."""
    op = op.strip()
    # N(ix) / N(iy) -> (ix+N); tcdev печатает смещение БЕЗ ЗНАКА, поэтому
    # значения 0x80..0xFF на самом деле отрицательные
    m = re.fullmatch(r'(-?(?:0x[0-9A-Fa-f]+|\d+))\((ix|iy)\)', op)
    if m:
        n = int(m.group(1), 0)
        if n > 127:
            n -= 256
        return f'({m.group(2)}{n:+d})'
    # '#' — признак непосредственного операнда в ASxxxx, в том числе внутри
    # выражения (#font-#0x100)
    return op.replace('#', '')


def conv_insn(mnem, args):
    parts = []
    for a in args.split(',') if args else []:
        a = a.strip()
        if a.lower() in FLAGS and len(parts) == 0 and mnem in ('jp', 'jr', 'call', 'ret'):
            parts.append(a.lower())
        else:
            parts.append(conv_operand(a))
    return mnem + (' ' + ', '.join(parts) if parts else '')


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    src, dst = sys.argv[1], sys.argv[2]
    lines = parse(src)
    out = []
    out.append('; Alien 8 (ZX Spectrum, Ultimate 1985)')
    out.append('; Автоперевод листинга tcdev v0.9a1 (ASxxxx) в синтаксис sjasmplus.')
    out.append('; Сделано tools/a8_lst2asm.py — руками не править.')
    out.append('        DEVICE ZXSPECTRUM48')
    out.append('')
    pc = None
    mism = []
    prev_addr = None      # адрес предыдущей строки с байтами
    prev_cont = False     # у предыдущей строки стоял '+'
    for ln in lines:
        body = ln.body
        lab, rest = split_label(body)
        code = strip_comment(rest).strip()
        comment = rest[len(strip_comment(rest)):].strip()

        emit = None
        size = 0
        if code:
            tok = code.split(None, 1)
            d = tok[0]
            args = tok[1].strip() if len(tok) > 1 else ''
            if d == '.org':
                pc = int(args, 0)
                emit = f'        ORG {args}'
            elif d == '.area' or d == '.hd64':
                emit = None
            elif d == '.db':
                vals = [v.strip() for v in args.split(',')]
                size = len(vals)
                emit = '        DB ' + ', '.join(vals)
            elif d == '.dw':
                vals = [v.strip() for v in args.split(',')]
                size = 2 * len(vals)
                emit = '        DW ' + ', '.join(vals)
            elif d == '.ds':
                size = int(args, 0)
                emit = f'        DS {args}'
            elif d == '.ascii':
                s = args.strip()
                q = s[0]
                assert s[-1] == q, (ln.lineno, s)
                text = s[1:-1]
                assert q not in text, (ln.lineno, s)
                size = len(text)
                esc = text.replace('\\', '\\\\').replace('"', '\\"')
                emit = f'        DB "{esc}"'
            elif d.startswith('.'):
                raise ValueError(f'{ln.lineno}: неизвестная директива {code!r}')
            else:
                emit = '        ' + conv_insn(d, args)
                size = None  # длину инструкции берём из колонки байт листинга

        # сверка адреса: у строк-продолжений многострочной директивы адрес
        # повторяет адрес её начала (колонка байт при этом может быть пустой),
        # поэтому сверяем только первую строку директивы
        if code:
            is_cont = ln.addr == prev_addr
            if pc is not None and ln.bytecol is not None and not is_cont:
                if ln.addr != pc and not code.startswith('.org'):
                    mism.append((ln.lineno, ln.addr, pc, ln.raw[:70]))
                    pc = ln.addr  # пересинхронизация, чтобы увидеть все расхождения
            prev_addr = ln.addr
        prev_cont = ln.cont

        if lab:
            out.append(f'{lab}:')
        if emit is not None:
            if comment:
                emit += '   ' + comment
            out.append(emit)
        elif comment and not lab:
            out.append('        ' + comment)

        if pc is not None:
            if size is None:
                size = len(ln.bytecol) if ln.bytecol else 0
                # инструкции всегда умещаются в колонку (<=4 байта)
                assert not ln.cont, (ln.lineno, ln.raw)
            pc += size

    if len(sys.argv) > 3:
        out.append('')
        out.append(f'        SAVEBIN "{sys.argv[3]}", 0x4000, 0xC000')
    with open(dst, 'w') as f:
        f.write('\n'.join(out) + '\n')
    print(f'{dst}: {len(out)} строк, расхождений адреса {len(mism)}')
    for m in mism[:20]:
        print(f'  строка {m[0]}: листинг {m[1]:04X}, счёт {m[2]:04X} | {m[3]}')
    return 1 if mism else 0


if __name__ == '__main__':
    sys.exit(main())
