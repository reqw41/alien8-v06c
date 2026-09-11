#!/usr/bin/env python3
"""Разбор листинга ASxxxx (tcdev Alien 8) — общая часть для эталона байт и конвертера.

Формат строки листинга:
    СЕГМЕНТ:AAAA<пробел><11 символов колонки байт><'+' или пробел><тело>
Колонка байт содержит до 4 байт; '+' означает «байты этой директивы продолжаются
на следующих строках». Адрес в строке — адрес НАЧАЛА директивы, поэтому у
многострочных .db он повторяется, а поток байт идёт подряд.
"""
import re

LINE = re.compile(r'^([A-Z0-9]+):([0-9A-F]{4})(.*)$')


class Line:
    __slots__ = ('seg', 'addr', 'bytecol', 'cont', 'body', 'lineno', 'raw')

    def __init__(self, seg, addr, bytecol, cont, body, lineno, raw):
        self.seg = seg
        self.addr = addr
        self.bytecol = bytecol   # список int или None (для '??')
        self.cont = cont         # True, если стоит '+'
        self.body = body         # текст после колонки байт
        self.lineno = lineno
        self.raw = raw


def parse(path):
    out = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for i, raw in enumerate(f, 1):
            raw = raw.rstrip('\n').rstrip()
            m = LINE.match(raw)
            if not m:
                if raw.strip():
                    raise ValueError(f'{path}:{i}: не разобрана строка: {raw!r}')
                continue
            seg, addr, rest = m.group(1), int(m.group(2), 16), m.group(3)
            col = rest[1:12]
            cont = rest[12:13] == '+'
            body = rest[13:]
            if col.strip() == '' :
                bc = []
            elif '?' in col:
                bc = None
            else:
                bc = [int(x, 16) for x in col.split()]
            out.append(Line(seg, addr, bc, cont, body, i, raw))
    return out


def strip_comment(body):
    """Убрать комментарий ';', не трогая ';' внутри строковых литералов."""
    q = None
    for i, ch in enumerate(body):
        if q:
            if ch == q:
                q = None
        elif ch in "'\"":
            q = ch
        elif ch == ';':
            return body[:i]
    return body


LABEL = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):')


def split_label(body):
    """Вернуть (метка|None, остаток без ведущих пробелов)."""
    b = body
    m = LABEL.match(b.lstrip())
    if m and not b.lstrip().startswith(';'):
        lab = m.group(1)
        rest = b.lstrip()[m.end():]
        return lab, rest.strip()
    return None, b.strip()
