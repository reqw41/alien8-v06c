#!/usr/bin/env python3
"""a8_z80_to_8080.py — рекомпиляция Alien 8 (Z80 -> i8080) на уровне исходника, синтаксис sjasmplus.

Ядро (split_line/expand/_ixiy/_exx/_classify_exx/_bit/_resset/_shift/_ldir/_adcsbc_hl/translate)
взято ДОСЛОВНО из knightlore-v06c/tools/kl_z80_to_8080.py (оно же из kvalley-v06c) — оно общее
для всех трёх портов. Специфика Alien 8 — только в склейке (a8_*).

    python3 tools/a8_z80_to_8080.py <in.asm> <out.asm> [--target lockstep]
"""
import sys, re, os
import a8_native_logic
import a8_native_flip
import a8_sound_ay
sys.path.insert(0, __import__('os').path.dirname(__file__))


# scratch cell names (defined as MAP fields appended to the work area)
SCRATCH = ['z80_ix', 'z80_iy', 'z80_af_alt', 'z80_bc_alt', 'z80_de_alt',
           'z80_hl_alt', 'il_tmp', 'il_tmp2', 'il_a']
SCRATCH_DEFS = "\n".join(f"{n}:\t# 2" for n in SCRATCH) + "\nil_outstub:\t# 3"


def split_line(line):
    """Return (label, body, comment). label includes trailing ':' if present."""
    # comment
    comment = ''
    # find ';' not inside quotes (rare in this source); simple split is fine
    if ';' in line:
        i = line.index(';')
        comment = line[i:]
        line = line[:i]
    # label: leading token at col 0 ending with ':' (or a bare label at col0)
    label = ''
    m = re.match(r'^([A-Za-z_@?.][\w@?.$]*:)\s*(.*)$', line)
    if m:
        label = m.group(1)
        body = m.group(2)
    else:
        body = line.strip() if line.strip() else ''
        if line and not line[0].isspace():
            # bare label at col0 without colon (Sjasm MAP fields use this) -> leave as-is
            return (line.rstrip(), '', comment)
    return (label, body.strip(), comment)


def operands(body):
    """mnemonic, [op1, op2]"""
    parts = body.split(None, 1)
    mn = parts[0].lower()
    ops = [x.strip() for x in parts[1].split(',')] if len(parts) > 1 else []
    return mn, ops


def reg8(r):
    """normalize an 8-bit register token; (ix+d)/(iy+d) handled separately."""
    return r.strip().lower()


# ----- IX/IY effective-address helper: HL = ix/iy + disp -----
def _idx_addr(idxcell, disp):
    """Build effective address (idx+disp) into HL, clobbering A ONLY (caller saves
    A+flags via push af where needed). disp is symbolic; the assembler splits it into
    low/high bytes (handles negative via two's complement masks). HL is overwritten;
    caller must have saved the original HL (il_tmp2)."""
    out = [f"ld hl,({idxcell})"]
    d = disp.strip()
    if d and d not in ('0', '+0'):
        d = d.lstrip('+')
        out += ["ld a,l", f"add a,({d})&255", "ld l,a",
                "ld a,h", f"adc a,(({d})>>8)&255", "ld h,a"]
    return out


def expand(mn, ops, idxinfo):
    """Return list of i8080 asm lines (no label/comment) for a Z80-only instruction,
    or None if not Z80-only (pass through)."""
    # --- JR / DJNZ ---
    if mn == 'jr':
        if len(ops) == 1:
            return [f"jp {ops[0]}"]
        cc = ops[0].lower()
        return [f"jp {cc},{ops[1]}"]
    if mn == 'djnz':
        return ["dec b", f"jp nz,{ops[0]}"]
    # --- EXX / EX AF,AF' ---
    # exx approach-B: a PRE-PASS (_classify_exx) retags provably paired-temporary
    # exx into exxo (opening) / exxc (closing) -> a 3-byte push/pop instead of the
    # 33-byte per-pair RAM swap. Order is mirrored (LIFO): push bc/de/hl ... pop
    # hl/de/bc, so the two OTHER pairs and all flags are preserved. Only the main
    # bank is touched; the z80_*_alt cells are NOT written (safe iff the alt-bank
    # residue is dead - guaranteed by the classifier's rules, see _classify_exx).
    if mn == 'exxo':
        return ["push bc", "push de", "push hl"]
    if mn == 'exxc':
        return ["pop hl", "pop de", "pop bc"]
    if mn == 'exx':
        return _exx()
    if mn == 'ex' and ops and ops[0].lower() == 'af' and ops[1].replace(' ', '').lower() == "af'":
        return _exaf()
    # --- IX/IY (detected via idxinfo: (cell, regtoken/None)) ---
    if idxinfo is not None:
        return _ixiy_compact(mn, ops, idxinfo) if _IX_COMPACT else _ixiy(mn, ops, idxinfo)
    # --- Z80-only LD A,I / LD A,R (ED 57 / ED 5F) ---
    # The i8080 has no I/R register AND no ED prefix: passed through verbatim, the
    # ED byte is an UNDOCUMENTED 3-byte CALL on the 8080, so `ld a,i` (ED 57) plus
    # the following opcode byte become `CALL <next>57h` -> a wild jump into random
    # code (here momiaDecide7's ld a,i CALLed into lanzaCuchillo, corrupting MapaRAM
    # with 0x14 solid cells). KV uses `ld a,i` once (momiaDecide7, "valor aleatorio"):
    # on the MSX the BIOS runs IM 1 and never writes I, so I stays 0 (Z80 reset) ->
    # the "random" read is always 0. Emit A=0 via MVI A (LD A,n leaves flags intact,
    # matching Z80 ld a,i which preserves CY - the very next op is RRA and needs it).
    if mn == 'ld' and len(ops) == 2 and ops[0].lower() == 'a' \
            and ops[1].lower() in ('i', 'r'):
        return [f"ld a, 0\t; Z80 'ld a,{ops[1].lower()}' -> I/R=0 on MSX "
                "(no I/R reg on i8080; MVI preserves flags)"]
    # --- Z80-only 16-bit memory loads: ld bc/de,(nn) and ld (nn),bc/de ---
    # (i8080 has LHLD/SHLD for HL only; ED 4B/5B/43/53 are Z80-only opcodes that
    #  would execute as garbage on the vanilla i8080 Vector -> wrong BC/DE.)
    if mn == 'ld':
        r = _ld16(ops)
        if r is not None:
            return r
        # ld (nn),sp / ld sp,(nn): ED 73 / ED 7B — Z80-only. Через HL (HL сохраняется через
        # стек; SP корректируется на 2 за push). Флаги портятся (Z80 их не трогает) — в KL
        # оба сайта в print_sprite, где следом ex de,hl / ret: флаги не читаются.
        if len(ops) == 2 and ops[1].strip().lower() == 'sp' and ops[0].strip().startswith('('):
            nn = ops[0].strip()[1:-1]
            return ["push hl", "ld hl,2", "add hl,sp", f"ld ({nn}),hl", "pop hl"]
        if len(ops) == 2 and ops[0].strip().lower() == 'sp' and ops[1].strip().startswith('('):
            nn = ops[1].strip()[1:-1]
            return [f"ld hl,({nn})", "ld sp,hl"]
        return None
    # --- CB: bit/res/set/shifts on registers ---
    if mn == 'bit':
        return _bit(ops[0], ops[1])
    if mn in ('res', 'set'):
        return _resset(mn, ops[0], ops[1])
    if mn in _SHIFTS:
        return _shift(mn, ops[0])
    # --- ED block / 16-bit / misc ---
    if mn == 'ldir':
        return _ldir(+1)
    if mn == 'lddr':
        return _ldir(-1)
    if mn == 'ldi':
        return _ldi(+1)
    if mn == 'ldd':
        return _ldi(-1)
    if mn in ('adc', 'sbc') and len(ops) == 2 and ops[0].lower() == 'hl':
        return _adcsbc_hl(mn, ops[1])
    if mn == 'neg':
        return ["cpl", "inc a"]
    if mn == 'im':
        # i8080 has no IM; but the MSX C-BIOS interrupt dispatch requires IM 1.
        # Pass the real Z80 opcode through for openMSX(Z80) validation. On the
        # vanilla Vector-06C target the interrupt setup is replaced (RST 7), so
        # this line is stripped/adapted there.
        return [f"im {ops[0]}\t; keep for MSX C-BIOS (IM 1); replace on Vector"]
    if mn in ('reti', 'retn'):
        return ["ret"]
    if mn == 'out' and ops and ops[0].lower() == '(c)':
        return _out_c(ops[1])
    if mn == 'in' and len(ops) == 2 and ops[1].lower() == '(c)':
        return _in_c(ops[0])
    return None


def _ld16(ops):
    """Translate Z80-only 16-bit memory loads to i8080 via HL (preserving HL and
    flags). Returns None for i8080-native ld forms (pass through unchanged)."""
    if len(ops) != 2:
        return None
    dst, src = ops[0].strip(), ops[1].strip()
    dl, sl = dst.lower(), src.lower()
    mem = lambda t: t.startswith('(') and t.endswith(')')
    # ld bc,(nn) / ld de,(nn)  -> LHLD then move to rp
    if dl in ('bc', 'de') and mem(src):
        nn = src[1:-1].strip()
        hi, lo = dl[0], dl[1]
        return ["push hl", f"ld hl,({nn})", f"ld {hi},h", f"ld {lo},l", "pop hl"]
    # ld (nn),bc / ld (nn),de  -> move rp to HL then SHLD
    if sl in ('bc', 'de') and mem(dst):
        nn = dst[1:-1].strip()
        hi, lo = sl[0], sl[1]
        return ["push hl", f"ld h,{hi}", f"ld l,{lo}", f"ld ({nn}),hl", "pop hl"]
    return None


def _exx():
    out = []
    for rp, cell in (('bc', 'z80_bc_alt'), ('de', 'z80_de_alt'), ('hl', 'z80_hl_alt')):
        out += _swap_rp(rp, cell)
    return out


def _swap_rp(rp, cell):
    # Compact stack-based swap of a register pair with its alt RAM cell.
    # Semantics identical to exx per-pair: rp <-> (cell). No flag/A effects
    # (push/pop/ld/mov/xthl leave flags untouched). Only HL is used as scratch
    # and is always restored, so the OTHER two pairs are preserved.
    if rp == 'hl':
        # HL <-> (cell): 5 insns / 9 bytes (was 6 / 18).
        return ["push hl", f"ld hl,({cell})", "ex (sp),hl",
                f"ld ({cell}),hl", "pop hl"]
    hi, lo = rp[0], rp[1]
    # BC/DE <-> (cell): 8 insns / 12 bytes (was 10 / 22), HL preserved.
    return ["push hl", f"ld hl,({cell})", f"push {rp}",
            f"ld {lo},l", f"ld {hi},h", "pop hl",
            f"ld ({cell}),hl", "pop hl"]


def _exaf():
    return ["ld (il_tmp2),hl", "push af", "pop hl", "ld (il_tmp),hl",
            "ld hl,(z80_af_alt)", "push hl", "pop af", "ld hl,(il_tmp)",
            "ld (z80_af_alt),hl", "ld hl,(il_tmp2)"]


# ---------------------------------------------------------------------------
# EXX approach-B: paired-temporary exx -> push/pop (6 bytes/pair vs 66).
# ---------------------------------------------------------------------------
# The default exx expansion (_swap_rp x3) swaps each register pair with a RAM
# cell (z80_bc/de/hl_alt) = 33 bytes/exx. When a matched `exx ... exx` pair is
# used purely as "give me scratch registers" (the alt bank is FRESH scratch, not
# carrying data between pairs), the whole swap is unnecessary: the opening exx
# can just `push bc/de/hl` (preserve the main bank on the stack) and the closing
# exx `pop hl/de/bc` (restore it) = 3 bytes each, 6 bytes/pair vs 66.
#
# A pre-pass classifies the ROLE of every standalone `exx` and retags the safe
# ones to `exxo`/`exxc`; the rest stay `exx` (RAM swap). A pair (open i, its very
# next exx j) is a SAFE temporary iff ALL hold in the body between them:
#   1. no label (a jump-in target) and no branch leaving the pair
#      (jr/jp/djnz/ret/rst/reti/retn). call/ldir/lddr are stack-balanced and act
#      as a write-barrier (a subroutine defines its outputs) -> allowed.
#   2. no alt register b/c/d/e/h/l is READ before it is WRITTEN. A read-before-
#      write means the alt reg carries a value produced by a PRIOR exx pair =
#      long-lived data (e.g. an alt-bank loop counter, or a caller-passed alt
#      pointer) -> the swap must stay so the value is read from the RAM cell.
#   3. the body's observable effect is a MEMORY write (its purpose is to poke
#      memory using the alt bank as scratch). If the sole effect is loading an
#      alt REGISTER (e.g. setVDPWrite: `ld c,a` sets the VDP data port that a
#      later `exx / out(c),a / exx` consumes), push/pop would NOT reproduce that
#      alt-register residue -> exclude, keep the swap.
# Rules 1-3 are LOCAL and sound for the observable memory effect; the z80 logic
# gate is the backstop for any cross-routine alt residue.

_R8 = ('b', 'c', 'd', 'e', 'h', 'l')
_RP = {'bc': ('b', 'c'), 'de': ('d', 'e'), 'hl': ('h', 'l')}


def _tok_regs(tok):
    """Return (regset, is_mem) for an operand token: which of b/c/d/e/h/l it
    references and whether it is a memory reference via a register pair."""
    t = tok.strip().lower()
    if t in _RP:
        return set(_RP[t]), False
    if t in _R8:
        return {t}, False
    if t.startswith('(') and t.endswith(')'):
        inner = t[1:-1].strip().lower()
        if inner == 'hl':
            return {'h', 'l'}, True
        if inner in ('bc', 'de'):
            return set(_RP[inner]), True
        return set(), True          # (nn) immediate address
    return set(), False


def _exx_regs(mn, ops):
    """Effect of one instruction on the tracked 8-bit regs.
    Returns (reads, writes, mem_write, is_branch, ok). ok=False => unparseable
    (caller must treat the pair as unsafe)."""
    if mn in ('jr', 'jp', 'djnz', 'ret', 'rst', 'reti', 'retn'):
        return set(), set(), False, True, True
    if mn in ('call', 'ldir', 'lddr'):
        # stack-balanced; treat as a write-barrier for all tracked regs so a
        # subsequent (hl)/reg read is not flagged read-before-write.
        return set(), set(_R8), mn in ('ldir', 'lddr'), False, True
    if mn == 'ld' and len(ops) == 2:
        reads, _ = _tok_regs(ops[1])
        writes, mem_write = set(), False
        dl = ops[0].strip().lower()
        if dl in _RP:
            writes |= set(_RP[dl])
        elif dl in _R8:
            writes.add(dl)
        elif dl.startswith('(') and dl.endswith(')'):
            r, _m = _tok_regs(ops[0])
            reads |= r               # addr regs are READ to form the pointer
            mem_write = True
        return reads, writes, mem_write, False, True
    if mn in ('inc', 'dec') and len(ops) == 1:
        t = ops[0].strip().lower()
        if t in _RP:
            return set(_RP[t]), set(_RP[t]), False, False, True
        if t in _R8:
            return {t}, {t}, False, False, True
        if t == '(hl)':
            return {'h', 'l'}, set(), True, False, True
        return set(), set(), False, False, False
    if mn == 'push' and ops:
        t = ops[0].strip().lower()
        if t in _RP:
            return set(_RP[t]), set(), False, False, True
        if t == 'af':
            return set(), set(), False, False, True
        return set(), set(), False, False, False
    if mn == 'pop' and ops:
        t = ops[0].strip().lower()
        if t in _RP:
            return set(), set(_RP[t]), False, False, True
        if t == 'af':
            return set(), set(), False, False, True
        return set(), set(), False, False, False
    if mn in ('add', 'adc') and len(ops) == 2 and ops[0].strip().lower() == 'hl':
        r, _ = _tok_regs(ops[1])
        return {'h', 'l'} | r, {'h', 'l'}, False, False, True
    if mn == 'ex' and len(ops) == 2:
        s = set()
        for t in (ops[0].strip().lower(), ops[1].strip().lower()):
            if t in _RP:
                s |= set(_RP[t])
            elif t != '(sp)':
                return set(), set(), False, False, False
        return s, s, False, False, True
    if mn in ('add', 'adc', 'sub', 'sbc', 'and', 'or', 'xor', 'cp') and ops:
        r, _ = _tok_regs(ops[-1])    # `op a,x` or `op x`; A is untracked
        return r, set(), False, False, True
    if mn in ('rra', 'rla', 'rrca', 'rlca', 'cpl', 'scf', 'ccf', 'daa', 'neg',
              'nop', 'ei', 'di', 'halt') and not ops:
        return set(), set(), False, False, True
    if mn in ('add', 'adc', 'sub', 'sbc', 'and', 'or', 'xor', 'cp') and not ops:
        return set(), set(), False, False, True
    return set(), set(), False, False, False   # unknown -> unsafe


def _classify_exx(src):
    """Retag provably paired-temporary `exx` into `exxo`/`exxc`. Returns
    (new_src, n_pairs_converted). Long-lived exx are left untouched."""
    lines = src.split('\n')
    exx_idx = []
    for i, l in enumerate(lines):
        lbl, body, _ = split_line(l)
        if not lbl and body.strip().lower() == 'exx':
            exx_idx.append(i)
    roles = {}
    conv = 0
    k = 0
    while k + 1 < len(exx_idx):
        oi, ci = exx_idx[k], exx_idx[k + 1]
        written, membw, safe = set(), False, True
        for j in range(oi + 1, ci):
            lbl, body, _ = split_line(lines[j])
            if lbl:                      # label = possible jump-in target
                safe = False
                break
            if not body:
                continue
            mn, ops = operands(body)
            reads, writes, mw, branch, ok = _exx_regs(mn, ops)
            if not ok or branch:
                safe = False
                break
            if reads - written:          # read-before-write of an alt reg
                safe = False
                break
            written |= writes
            membw = membw or mw
        if safe and membw:
            roles[oi], roles[ci] = 'exxo', 'exxc'
            conv += 1
            k += 2
        else:
            k += 1
    for i, newmn in roles.items():
        line = lines[i]
        indent = line[:len(line) - len(line.lstrip())]
        _, _, cmt = split_line(line)
        lines[i] = indent + newmn + (('\t' + cmt) if cmt else '')
    return '\n'.join(lines), conv


def _bit(n, reg):
    mask = f"1<<{n}"
    if reg == 'a':
        return ["ld (il_a),a", f"and {mask}", "ld a,(il_a)"]
    if reg in ('(hl)',):
        return ["ld (il_a),a", "ld a,(hl)", f"and {mask}", "ld a,(il_a)"]
    return ["ld (il_a),a", f"ld a,{reg}", f"and {mask}", "ld a,(il_a)"]


def _resset(op, n, reg):
    # Sjasm computes the mask constant. RES/SET must preserve ALL flags (Z80 does).
    alu = f"and (~(1<<{n}))&255" if op == 'res' else f"or 1<<{n}"
    if reg == 'a':
        return ["push af", alu, "ld (il_a),a", "pop af", "ld a,(il_a)"]
    if reg == '(hl)':
        return ["push af", "ld a,(hl)", alu, "ld (hl),a", "pop af"]
    return ["push af", f"ld a,{reg}", alu, f"ld {reg},a", "pop af"]


def _shift_body(op):
    if op == 'sla':
        return ["add a,a"]
    if op == 'sll':
        return ["add a,a", "or 1"]
    if op == 'rlc':
        return ["rlca"]
    if op == 'rrc':
        return ["rrca"]
    if op == 'rl':
        return ["rla"]
    if op == 'rr':
        return ["rra"]
    if op == 'srl':
        return ["or a", "rra"]
    if op == 'sra':
        return ["ld (il_tmp),a", "add a,a", "ld a,(il_tmp)", "rra"]
    raise AssertionError('транслятор не знает сдвига %r' % op)


# Сдвиги группы CB. Один список на все формы: регистр (_shift), (hl) (_shift) и ЯЧЕЙКА
# (ix+d)/(iy+d) (_shift_cell). Раньше формы по (ix+d) не разбирались вовсе — см. _shift_cell.
_SHIFTS = ('sla', 'sra', 'srl', 'sll', 'rl', 'rr', 'rlc', 'rrc')


def _shift_cell(op):
    """Сдвиг ЯЧЕЙКИ, на которую УЖЕ показывает HL; A сохранён в il_a, старый HL — в il_tmp2.

    Контракт ровно как у Z80 `sla/srl/... (ix+d)`: сдвигается ячейка, A НЕ МЕНЯЕТСЯ,
    флаги — от результата сдвига. Восстановление A и HL флагов не трогает: на i8080
    `ld (hl),a` (MOV M,A), `ld a,(nn)` (LDA) и `ld hl,(nn)` (LHLD) флагов не меняют,
    поэтому S/Z/P/CY, выставленные телом сдвига, доживают до вызывателя.

    Единственное отличие от Z80 — у `srl`/`sra` (тело `or a : rra`): перенос верный,
    а S/Z/P остаются от ДО-сдвигового значения. То же самое транслятор делает и для
    регистровых форм (_shift), то есть отличие не новое и не специфичное для (ix+d).
    """
    return ["ld a,(hl)"] + _shift_body(op) + ["ld (hl),a", "ld a,(il_a)", "ld hl,(il_tmp2)"]


def _shift(op, reg):
    body = _shift_body(op)
    if reg == 'a':
        return body
    if reg == '(hl)':
        return ["ld (il_a),a", "ld a,(hl)", *body, "ld (hl),a", "ld a,(il_a)"]
    return ["ld (il_a),a", f"ld a,{reg}", *body, f"ld {reg},a", "ld a,(il_a)"]


_LD_UID = [0]


def _uniq(stem):
    _LD_UID[0] += 1
    return f".il_{stem}{_LD_UID[0]}"


def _ldir(step):
    # Deflation: fold the 8-instruction inline copy loop into a shared subroutine
    # (vec_ldir_fwd for ldir/+1, vec_ldir_bwd for lddr/-1). Params already in the
    # right regs (HL=src, DE=dst, BC=count). Semantics identical: copies BC bytes,
    # leaves BC=0 and HL/DE past the range, Z set (from the final `or c`). call/ret
    # touch only the stack + PC, so flags/regs on return match the inline form.
    return ["call vec_ldir_fwd" if step > 0 else "call vec_ldir_bwd"]


def _ldi(step):
    s = "inc" if step > 0 else "dec"
    return ["ld a,(hl)", "ld (de),a", f"{s} hl", f"{s} de", "dec bc"]


# Shared ldir/lddr copy loops (deflation): each Z80 ldir/lddr becomes a single
# `call` to one of these instead of an 8-instruction inline expansion. Injected in
# a code region just before the MAP block, so they exist for BOTH targets (the
# `call` is emitted target-independently by _ldir). All-i8080 (passes through
# translate untouched). vec_ldir_fwd = ldir (inc), vec_ldir_bwd = lddr (dec).
#
# STACK-SAFE: a plain call/ret would leave the return address on the stack DURING
# the copy. KV's boot variable-fill (`ld (hl),0` + ldir over GameStatus..+0x6FF)
# has the stack sitting INSIDE that range on MSX (SP=stackTop 0xE700, fill hits
# 0xE6FE/FF = the pushed return slot) -> the fill zeroes the return address ->
# ret to 0x0000 -> reboot loop. The inline loop never touched the stack, so it was
# immune. Fix: at entry stash the return address in il_tmp2 (a scratch cell OUTSIDE
# any fill region on both targets: MSX 0xF00E, Vector 0xDFCE) and pop it off the
# stack, so the copy can never clobber it; at exit restore it and jump back while
# leaving HL/DE/BC exactly as ldir does (HL/DE past range, BC=0). il_tmp2 is saved/
# restored by BOTH ISRs (vec_isr + tickMainISR), so an interrupt mid-copy (or a
# nested ldir inside tickMain) preserves the stashed return address.
_LDIR_LOOP_FWD = ("\tld\ta,(hl)\n\tld\t(de),a\n\tinc\thl\n\tinc\tde\n"
                  "\tdec\tbc\n\tld\ta,b\n\tor\tc\n\tjp\tnz,{lp}\n")
_LDIR_LOOP_BWD = ("\tld\ta,(hl)\n\tld\t(de),a\n\tdec\thl\n\tdec\tde\n"
                  "\tdec\tbc\n\tld\ta,b\n\tor\tc\n\tjp\tnz,{lp}\n")


def _ldir_helper(name, loop_tmpl):
    lp = name + "_lp"
    return (
        f"{name}:\n"
        "\tex\t(sp),hl\n\tld\t(il_tmp2),hl\n\tpop\thl\n"   # stash ret addr, restore HL=src
        f"{lp}:\n" + loop_tmpl.format(lp=lp) +
        "\tpush\thl\n\tld\thl,(il_tmp2)\n\tex\t(sp),hl\n\tret\n")  # restore ret, keep final HL


_LDIR_HELPERS = (
    "\n; ===== ldir/lddr deflation: shared stack-safe copy loops (call, not inline) =====\n"
    "; Copy BC bytes (HL)->(DE); on return BC=0, HL/DE past the range. Return addr is\n"
    "; kept in il_tmp2 (not on the stack) so a fill whose dest overlaps SP is safe.\n"
    + _ldir_helper("vec_ldir_fwd", _LDIR_LOOP_FWD)
    + _ldir_helper("vec_ldir_bwd", _LDIR_LOOP_BWD)
)


def _adcsbc_hl(op, rp):
    # Value and carry come from the byte-wise adc/sbc chain. Z must reflect the FULL
    # 16-bit result (Z80 semantics) - KV branches on it (e.g. `sbc hl,bc / ret nz`
    # trap X-coincidence check). A naive chain leaves Z = (high byte == 0), so a
    # difference of 1..255 would read as "equal". Fix-up: when the high byte is 0,
    # recompute Z from L; restore carry via SCF (STC touches ONLY CY on 8080).
    # Clobbers A (Z80 clobbers only F); S reflects L's bit7 in the fix-up path -
    # fine for KV (only z/nz/c/nc used after 16-bit adc/sbc).
    rp = rp.lower()
    hi, lo = rp[0], rp[1]
    a = 'adc' if op == 'adc' else 'sbc'
    done = _uniq('AS16')
    cset = _uniq('AS16C')
    return ["ld a,l", f"{a} a,{lo}", "ld l,a",
            "ld a,h", f"{a} a,{hi}", "ld h,a",
            f"jp nz,{done}",                 # high!=0: Z=0 and C already correct
            f"jp c,{cset}",
            "ld a,l", "or a",                # C was 0: Z=(L==0), C stays 0
            f"jp {done}",
            f"{cset}:", "ld a,l", "or a", "scf",   # C was 1: fix Z, then restore C
            f"{done}:"]


# MSX fixed I/O ports for OUT (C),r / IN r,(C): the only out(c) sites are PSG (port
# A0/A1 via C). On MSX the value of C at these sites is the PSG register port. We
# keep C-as-port via a self-modified OUT (rare, 3 sites).
def _guniq(stem):
    _LD_UID[0] += 1
    return f"IL_{stem}{_LD_UID[0]}"          # GLOBAL label (self-mod target)


def _out_c(reg):
    pre = [] if reg == 'a' else [f"ld a,{reg}"]
    # i8080 has no variable-port OUT. The code lives in ROM (cartridge), so we
    # cannot self-modify it. Build an `out (port),a ; ret` stub in RAM (il_outstub)
    # and CALL it. Interrupt-safe: the ISR wrapper preserves il_a, and out(c) is
    # not used on any nested-interrupt path (updateSound uses BIOS PSG calls).
    return pre + ["ld (il_a),a", "ld a,c", "ld (il_outstub+1),a",
                  "ld a,0D3h", "ld (il_outstub),a",
                  "ld a,0C9h", "ld (il_outstub+2),a",
                  "ld a,(il_a)", "call il_outstub"]


def _in_c(reg):
    lbl = _guniq("INC")
    seq = ["ld a,c", f"ld ({lbl}+1),a", f"{lbl}:", "in a,(0)"]
    if reg != 'a':
        seq += [f"ld {reg},a"]
    return seq


def _ixiy(mn, ops, idxinfo):
    cell, _ = idxinfo
    full = (mn + ' ' + ','.join(ops)).lower()

    # push/pop ix
    if mn == 'push':
        return ["ld (il_tmp),hl", f"ld hl,({cell})", "push hl", "ld hl,(il_tmp)"]
    if mn == 'pop':
        return ["ld (il_tmp),hl", "pop hl", f"ld ({cell}),hl", "ld hl,(il_tmp)"]
    # ld ix,nn
    if mn == 'ld' and ops[0].lower() in ('ix', 'iy'):
        nn = ops[1]
        return ["ld (il_tmp),hl", f"ld hl,{nn}", f"ld ({cell}),hl", "ld hl,(il_tmp)"]
    # ld ix,(nn) / ld (nn),ix
    if mn == 'ld' and ops[0].lower() in ('ix', 'iy') and ops[1].startswith('('):
        nn = ops[1][1:-1]
        return [f"ld hl,({nn})", f"ld ({cell}),hl"]
    if mn == 'ld' and ops[1].lower() in ('ix', 'iy') and ops[0].startswith('('):
        nn = ops[0][1:-1]
        return ["ld (il_tmp),hl", f"ld hl,({cell})", f"ld ({nn}),hl", "ld hl,(il_tmp)"]
    # inc/dec ix
    if mn in ('inc', 'dec') and ops[0].lower() in ('ix', 'iy'):
        s = 'inc' if mn == 'inc' else 'dec'
        return ["ld (il_tmp),hl", f"ld hl,({cell})", f"{s} hl", f"ld ({cell}),hl", "ld hl,(il_tmp)"]
    # add ix,rp
    if mn == 'add' and ops[0].lower() in ('ix', 'iy'):
        rp = ops[1].lower()
        rp = cell if rp in ('ix', 'iy') else rp
        if rp == cell:
            return ["ld (il_tmp),hl", f"ld hl,({cell})", "add hl,hl", f"ld ({cell}),hl", "ld hl,(il_tmp)"]
        return ["ld (il_tmp),hl", f"ld hl,({cell})", f"add hl,{rp}", f"ld ({cell}),hl", "ld hl,(il_tmp)"]
    # jp (ix)
    if mn == 'jp' and ops[0].lower() in ('(ix)', '(iy)'):
        return [f"ld hl,({cell})", "jp (hl)"]
    # (ix+d) memory operand forms: parse which op is the memory ref
    midx = None
    for i, o in enumerate(ops):
        if '(ix' in o.lower() or '(iy' in o.lower():
            midx = i
    if midx is None:
        raise AssertionError('транслятор не разбирает форму IX/IY: %s' % full)
    inner = ops[midx]
    disp = re.sub(r'^\((ix|iy)', '', inner, flags=re.I)[:-1]   # strip "(ix" and ")"
    addr = _idx_addr(cell, disp)

    if mn == 'ld':
        if midx == 1:                      # ld r,(ix+d)
            r = ops[0].lower()
            if r == 'a':
                # ld a,(ix+d): Z80 leaves FLAGS unchanged, but the addr build's
                # add/adc clobber them. Save incoming A+F, load the target, then
                # restore F while keeping the loaded value (stashed in il_a).
                # (Was: no push af -> flags leaked, breaking e.g.
                #  `dec (ix+TIMER); ld a,(ix+TIMER); jr z,...` -> jr never taken.)
                return (["push af", "ld (il_tmp2),hl"] + addr
                        + ["ld a,(hl)", "ld hl,(il_tmp2)", "ld (il_a),a",
                           "pop af", "ld a,(il_a)"])
            seq = ["push af", "ld (il_tmp2),hl"] + addr + ["ld a,(hl)",
                   "ld hl,(il_tmp2)", f"ld {r},a", "pop af"]
            return seq
        else:                              # ld (ix+d),r  or  ld (ix+d),n
            src = ops[1]
            s = src.lower()
            if s == 'a':
                # Source is A, but the addr build clobbers A (it computes idx+disp via
                # ld a,l/add/ld a,h/adc). `ld a,a` cannot recover it -> stash A in il_a
                # first, build addr, then write the stashed value. (Was: wrote the
                # clobbered A = high byte of the pointer -> corrupted every actor field.)
                return (["push af", "ld (il_a),a", "ld (il_tmp2),hl"] + addr
                        + ["ld a,(il_a)", "ld (hl),a", "ld hl,(il_tmp2)", "pop af"])
            seq = ["push af", "ld (il_tmp2),hl"] + addr
            if s in ('b', 'c', 'd', 'e'):
                seq += [f"ld a,{src}", "ld (hl),a"]
            elif s in ('h', 'l'):
                # h/l were clobbered by addr build; read from saved il_tmp2
                byte = "(il_tmp2)" if s == 'l' else "(il_tmp2+1)"
                seq += [f"ld a,{byte}", "ld (hl),a"]
            else:                          # immediate n
                seq += [f"ld a,{src}", "ld (hl),a"]
            seq += ["ld hl,(il_tmp2)", "pop af"]
            return seq
    if mn in ('inc', 'dec'):
        # inc/dec (ix+d) sets flags from the result -> preserve A via il_a (ld doesn't
        # touch flags), NOT push/pop af (which would restore old flags).
        s = 'inc' if mn == 'inc' else 'dec'
        return ["ld (il_a),a", "ld (il_tmp2),hl"] + addr + [f"{s} (hl)",
                "ld hl,(il_tmp2)", "ld a,(il_a)"]
    if mn == 'bit':
        # BIT n,(ix+d): set Z = (bit==0). Consumed flag is Z only. Preserve A.
        n = ops[0]
        return ["ld (il_a),a", "ld (il_tmp2),hl"] + addr + ["ld a,(hl)",
                f"and 1<<{n}", "ld hl,(il_tmp2)", "ld a,(il_a)"]
    if mn in ('res', 'set'):
        n = ops[0]
        alu = f"and (~(1<<{n}))&255" if mn == 'res' else f"or 1<<{n}"
        return ["push af", "ld (il_tmp2),hl"] + addr + ["ld a,(hl)", alu, "ld (hl),a",
                "ld hl,(il_tmp2)", "pop af"]
    if mn in ('add', 'adc', 'sub', 'sbc', 'and', 'xor', 'or', 'cp'):
        # alu a,(ix+d): A is the operand, but the addr build clobbers A -> save A in
        # il_a, build addr, restore A, then operate on (hl). Flags = the alu result.
        alu = {'add': 'add a,', 'adc': 'adc a,', 'sub': 'sub ', 'sbc': 'sbc a,',
               'and': 'and ', 'xor': 'xor ', 'or': 'or ', 'cp': 'cp '}[mn]
        return ["ld (il_a),a", "ld (il_tmp2),hl"] + addr + ["ld a,(il_a)",
                f"{alu}(hl)", "ld hl,(il_tmp2)"]
    if mn in _SHIFTS:
        # sla/srl/sra/sll/rl/rr/rlc/rrc по (ix+d). ДО 2026-09-15 эта ветка отсутствовала:
        # форма уходила в последний `return` — строку `; UNHANDLED IX/IY ...`, то есть
        # в КОММЕНТАРИЙ. Команда молча не попадала в образ, и ни один гейт этого не видел
        # (check_i8080 смотрит опкоды, а не комментарии). В Alien 8 так потерялись шесть
        # команд, все в поведении робомыши (`sla (ix+9)`/`sla (ix+10)` в upd_5E_5F и
        # upd_56_57, `sla (ix+6)`/`srl (ix+6)` в sub_B1FA/sub_B20B): мышь ходила половинным
        # шагом, а её объект-тень upd_0B при нулевых полях +9/+10/+11 переставал ставить
        # флаги стирания и отрисовки — «враг забился в угол, на экране мусор» (журнал,
        # «Дефект владельца 2026-09-15: робомышь стояла на месте»).
        # Ниже по файлу для тех же форм есть и компактный хелпер (`il_ix_sla` и т. п.) —
        # тело у обоих путей ОДНО, _shift_cell.
        return ["ld (il_a),a", "ld (il_tmp2),hl"] + addr + _shift_cell(mn)
    raise AssertionError('транслятор не разбирает форму IX/IY: %s' % full)


# ---------------------------------------------------------------------------
# КОМПАКТНАЯ ЭМУЛЯЦИЯ IX/IY (KL): обращение (ix+d) = `call il_<ix|iy>_<форма>` + inline-байт(ы).
# Хелпер читает байты за адресом возврата и возвращается за них. Контракты регистров/флагов
# те же, что у встроенного разворачивания (_ixiy). Эмитятся только использованные хелперы.
# A8_IX_INLINE=1 -> старое встроенное разворачивание.
# ---------------------------------------------------------------------------
_IX_COMPACT = not __import__('os').environ.get('A8_IX_INLINE')
_ix_used = set()
# горячие процедуры (по профилю): встроенное разворачивание ради темпа, остальные — компактно
_IX_INLINE_FUNCS = set()   # цель lockstep: темп не меряем, все обращения — через хелперы
_cur_func = ['']

_ix_form_cnt = {}
# Редкую форму дешевле развернуть на месте, чем держать хелпер: тело 27..46 байт против
# 4 байт на `call+db` плюс 13..18 на развёртку. Порог выбран замером (низ региона):
#   N<=0: 0x7514 (все компактные)  N<=1: 0x74BB  N<=2: 0x7439  N<=3: 0x7597  N<=4: 0x7597
# То есть выгодно разворачивать формы с 1-2 обращениями; с 3 и более уже дороже.
# Побочный эффект — темп: развёртка быстрее call+хелпер.
_IX_RARE = int(__import__('os').environ.get('A8_IX_RARE', '2'))


def _ix_form(mn, ops, idxinfo):
    """(px, form) для обращения к (ix+d)/(iy+d) или None, если форма не компактная."""
    cell, _ = idxinfo
    px = 'ix' if cell == 'z80_ix' else 'iy'
    if mn in ('push', 'pop') or (mn == 'ld' and ops[0].lower() in ('ix', 'iy')) \
            or (mn == 'ld' and len(ops) == 2 and ops[1].lower() in ('ix', 'iy')) \
            or (mn in ('inc', 'dec', 'add') and ops[0].lower() in ('ix', 'iy')) \
            or (mn == 'jp'):
        return None
    midx = None
    for i, o in enumerate(ops):
        if '(ix' in o.lower() or '(iy' in o.lower():
            midx = i
    if midx is None:
        return None
    # ОТРИЦАТЕЛЬНОЕ смещение компактному хелперу не по зубам: он берёт смещение
    # из inline-байта и считает адрес как `add a,l / adc a,0`, то есть трактует его
    # как БЕЗЗНАКОВОЕ — (ix-19) превращается в (ix+237). Встроенная развёртка
    # (_idx_addr) знак учитывает, поэтому такие обращения разворачиваем на месте.
    # В Alien 8 их 13 (у tcdev они и напечатаны без знака: 237(ix) и т. п.).
    if re.search(r'\((?:ix|iy)\s*-\s*\d', ops[midx], re.I):
        return None
    if mn == 'ld':
        if midx == 1:
            r = ops[0].lower()
            return (px, 'ld' + r) if r in ('a', 'b', 'c', 'd', 'e', 'h', 'l') else None
        sl = ops[1].strip().lower()
        return (px, 'st' + sl) if sl in ('a', 'b', 'c', 'd', 'e', 'h', 'l') else (px, 'stn')
    if mn in ('inc', 'dec', 'bit', 'res', 'set', 'add', 'adc', 'sub', 'sbc', 'and', 'xor', 'or', 'cp') \
            or mn in _SHIFTS:
        return (px, mn)
    return None


def count_ix_forms(src):
    """Предпроход: сколько раз встречается каждая компактная форма (ix+d)/(iy+d)."""
    _ix_form_cnt.clear()
    cur = ''
    for line in src.split('\n'):
        label, body, _c = split_line(line)
        if label and not label.startswith(('loc_', '.')):
            cur = label.rstrip(':')
        if not body or cur in _IX_INLINE_FUNCS:
            continue
        mn, ops = operands(body)
        idx = has_idx(body)
        if not idx:
            continue
        f = _ix_form(mn, ops, idx)
        if f:
            _ix_form_cnt[f] = _ix_form_cnt.get(f, 0) + 1


def _ixiy_compact(mn, ops, idxinfo):
    cell, _ = idxinfo
    if _cur_func[0] in _IX_INLINE_FUNCS:
        return _ixiy(mn, ops, idxinfo)
    f = _ix_form(mn, ops, idxinfo)
    if f and _ix_form_cnt.get(f, 99) <= _IX_RARE:
        return _ixiy(mn, ops, idxinfo)
    px = 'ix' if cell == 'z80_ix' else 'iy'
    full = (mn + ' ' + ','.join(ops)).lower()
    # формы, которые остаются встроенными (регистр IX целиком)
    if mn in ('push', 'pop') or (mn == 'ld' and ops[0].lower() in ('ix', 'iy')) \
            or (mn == 'ld' and len(ops) == 2 and ops[1].lower() in ('ix', 'iy')) \
            or (mn in ('inc', 'dec', 'add') and ops[0].lower() in ('ix', 'iy')) \
            or (mn == 'jp'):
        return _ixiy(mn, ops, idxinfo)
    midx = None
    for i, o in enumerate(ops):
        if '(ix' in o.lower() or '(iy' in o.lower():
            midx = i
    if midx is None:
        return _ixiy(mn, ops, idxinfo)
    disp = re.sub(r'^\((ix|iy)', '', ops[midx], flags=re.I)[:-1].strip().lstrip('+') or '0'
    # ОТРИЦАТЕЛЬНОЕ смещение компактному хелперу не по зубам: он берёт смещение из
    # inline-байта и считает адрес как `add a,l / adc a,0`, то есть трактует его как
    # БЕЗЗНАКОВОЕ — (ix-19) давало (ix+237). Встроенная развёртка (_idx_addr) знак
    # учитывает (`(d)&255` и `((d)>>8)&255`), поэтому разворачиваем на месте.
    # В Alien 8 таких обращений 13 (у tcdev они напечатаны без знака: 237(ix) и т.п.).
    if disp.lstrip().startswith('-'):
        return _ixiy(mn, ops, idxinfo)
    def use(form, *extra):
        name = f"il_{px}_{form}"
        _ix_used.add((px, form))
        return [f"call {name}", "db " + ", ".join([disp] + list(extra))]
    if mn == 'ld':
        if midx == 1:
            r = ops[0].lower()
            if r in ('a', 'b', 'c', 'd', 'e', 'h', 'l'):
                return use('ld' + r)
        else:
            src = ops[1].strip(); sl = src.lower()
            if sl in ('a', 'b', 'c', 'd', 'e', 'h', 'l'):
                return use('st' + sl)
            return use('stn', src)
    if mn in ('inc', 'dec'):
        return use(mn)
    if mn == 'bit':
        return use('bit', f"1<<{ops[0]}")
    if mn == 'res':
        return use('res', f"(~(1<<{ops[0]}))&255")
    if mn == 'set':
        return use('set', f"1<<{ops[0]}")
    if mn in ('add', 'adc', 'sub', 'sbc', 'and', 'xor', 'or', 'cp'):
        return use(mn)
    if mn in _SHIFTS:
        return use(mn)
    return _ixiy(mn, ops, idxinfo)

_ADDR = ["ld hl,({C})", "add a,l", "ld l,a", "ld a,h", "adc a,0", "ld h,a"]   # HL = cell + A
_PRO_AF = ["ld (il_tmp2),hl", "push af", "pop hl", "ld (il_f),hl", "pop hl", "ld a,(hl)", "inc hl", "push hl"]
_EPI_AF = ["ld hl,(il_f)", "push hl", "pop af", "ld hl,(il_tmp2)", "ret"]
_PRO_A  = ["ld (il_tmp2),hl", "ld (il_a),a", "pop hl", "ld a,(hl)", "inc hl", "push hl"]   # только A (флаги — результат)
_PRO_AF2 = ["ld (il_tmp2),hl", "push af", "pop hl", "ld (il_f),hl", "pop hl", "ld a,(hl)", "ld (il_tmp),a",
            "inc hl", "ld a,(hl)", "ld (il_tmp+1),a", "inc hl", "push hl", "ld a,(il_tmp)"]     # d + второй байт в il_tmp+1
_PRO_A2  = ["ld (il_tmp2),hl", "ld (il_a),a", "pop hl", "ld a,(hl)", "ld (il_tmp),a",
            "inc hl", "ld a,(hl)", "ld (il_tmp+1),a", "inc hl", "push hl", "ld a,(il_tmp)"]

def _ix_helper(px, form):
    C = 'z80_' + px
    A = [x.replace('{C}', C) for x in _ADDR]
    body = None
    if form == 'lda':
        body = _PRO_AF + A + ["ld a,(hl)", "ld (il_a),a", "ld hl,(il_f)", "push hl", "pop af", "ld a,(il_a)", "ld hl,(il_tmp2)", "ret"]
    elif form in ('ldb', 'ldc', 'ldd', 'lde'):
        body = _PRO_AF + A + [f"ld {form[2]},(hl)"] + _EPI_AF
    elif form == 'ldl':
        body = _PRO_AF + A + ["ld a,(hl)", "ld (il_tmp2),a"] + _EPI_AF
    elif form == 'ldh':
        body = _PRO_AF + A + ["ld a,(hl)", "ld (il_tmp2+1),a"] + _EPI_AF
    elif form == 'sta':
        body = _PRO_AF + A + ["ld a,(il_f+1)", "ld (hl),a"] + _EPI_AF
    elif form in ('stb', 'stc', 'std', 'ste'):
        body = _PRO_AF + A + [f"ld (hl),{form[2]}"] + _EPI_AF
    elif form == 'stl':
        body = _PRO_AF + A + ["ld a,(il_tmp2)", "ld (hl),a"] + _EPI_AF
    elif form == 'sth':
        body = _PRO_AF + A + ["ld a,(il_tmp2+1)", "ld (hl),a"] + _EPI_AF
    elif form == 'stn':
        body = _PRO_AF2 + A + ["ld a,(il_tmp+1)", "ld (hl),a"] + _EPI_AF
    elif form in ('inc', 'dec'):
        body = _PRO_A + A + [f"{form} (hl)", "ld a,(il_a)", "ld hl,(il_tmp2)", "ret"]
    elif form == 'bit':
        body = _PRO_A2 + A + ["ld a,(il_tmp+1)", "and (hl)", "ld a,(il_a)", "ld hl,(il_tmp2)", "ret"]
    elif form == 'res':
        body = _PRO_AF2 + A + ["ld a,(il_tmp+1)", "and (hl)", "ld (hl),a"] + _EPI_AF
    elif form == 'set':
        body = _PRO_AF2 + A + ["ld a,(il_tmp+1)", "or (hl)", "ld (hl),a"] + _EPI_AF
    elif form in _SHIFTS:
        # сдвиг ЯЧЕЙКИ (ix+d): _PRO_A уже сохранил A в il_a и HL в il_tmp2, тело — общее
        # с встроенной развёрткой (_shift_cell): A и HL сохраняются, флаги — от результата
        body = _PRO_A + A + _shift_cell(form) + ["ret"]
    elif form in ('add', 'adc', 'sub', 'sbc', 'and', 'xor', 'or', 'cp'):
        alu = {'add': 'add a,', 'adc': 'adc a,', 'sub': 'sub ', 'sbc': 'sbc a,', 'and': 'and ', 'xor': 'xor ', 'or': 'or ', 'cp': 'cp '}[form]
        body = _PRO_A + A + ["ld a,(il_a)", f"{alu}(hl)", "ld hl,(il_tmp2)", "ret"]
    assert body, form
    return f"il_{px}_{form}:\n" + "\n".join("\t" + x for x in body) + "\n"

def ix_helpers_text():
    if not _ix_used:
        return ""
    out = ["\n; ===== компактные IX/IY-хелперы (только использованные формы) ====="]
    for px, form in sorted(_ix_used):
        out.append(_ix_helper(px, form))
    return "\n".join(out) + "\n"

def has_idx(body):
    """Detect IX/IY usage; return (cell, None) or None."""
    b = body.lower()
    if re.search(r'\(ix', b) or re.search(r'\bix\b', b):
        return ('z80_ix', None)
    if re.search(r'\(iy', b) or re.search(r'\biy\b', b):
        return ('z80_iy', None)
    return None


def translate(src):
    count_ix_forms(src)
    out = []
    inserted_scratch = False
    for line in src.split('\n'):
        label, body, comment = split_line(line)
        if label and not label.startswith(('loc_', '.')):
            _cur_func[0] = label.rstrip(':')
        if not body:
            out.append(line)
            continue
        mn, ops = operands(body)
        idx = has_idx(body)
        seq = expand(mn, ops, idx)
        if seq is None:
            out.append(line)              # pass through (i8080 / directive)
            continue
        # emit: source label on its own line, then the i8080 sequence (tab-indented;
        # sub-labels at col0). Attach the source comment to the first emitted line.
        if label:
            out.append(label)
        emitted_comment = False
        for s in seq:
            is_label = s.endswith(':')
            ln = s if is_label else ('\t' + s)
            if not emitted_comment and comment:
                ln += '\t' + comment
                emitted_comment = True
            out.append(ln)
    return "\n".join(out)






_R8 = {'a', 'b', 'c', 'd', 'e', 'h', 'l', '(hl)'}
_RR16 = {'bc', 'de', 'hl', 'sp', 'af'}


def _i8080_len(t):
    """Длина инструкции i8080 в байтах; None — не инструкция.
    Сверено с листингом сборки: 7685 инструкций, 0 расхождений."""
    p = t.split(None, 1)
    mn = p[0].lower()
    ops = [o.strip().lower() for o in p[1].split(',')] if len(p) > 1 else []
    if mn in ('nop', 'halt', 'di', 'ei', 'cpl', 'daa', 'scf', 'ccf', 'rlca', 'rrca', 'rla', 'rra',
              'ex', 'ret', 'rst', 'push', 'pop', 'inc', 'dec'):
        return 1
    if mn == 'call':
        return 3
    if mn == 'jp':
        return 1 if ops and ops[-1] == '(hl)' else 3
    if mn in ('in', 'out'):
        return 2
    if mn == 'add' and len(ops) == 2 and ops[0] == 'hl':
        return 1
    if mn in ('add', 'adc', 'sub', 'sbc', 'and', 'or', 'xor', 'cp'):
        return 1 if ops[-1] in _R8 else 2
    if mn == 'ld':
        if len(ops) != 2:
            return None
        d, s = ops
        if d == 'sp' and s == 'hl':
            return 1
        if d in _RR16 or (s in _RR16 and d.startswith('(')):
            return 3
        if (d.startswith('(') and d not in ('(hl)', '(bc)', '(de)')) or \
           (s.startswith('(') and s not in ('(hl)', '(bc)', '(de)')):
            return 3
        if d in ('(bc)', '(de)') or s in ('(bc)', '(de)'):
            return 1
        return 1 if s in _R8 else 2
    return None


_H_LBL = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):')
_H_HARD = re.compile(r'(?i)^(ORG|DEVICE|SAVEBIN|SAVESNA|ASSERT|ALIGN|IF|ELSE|ENDIF|INCBIN|DS|DB|DW|EQU)\b')
# halt НЕ прерывает поток: после прерывания исполнение идёт дальше (vec_di_budget: ei/halt/ret)
_H_TERM = re.compile(r'(?i)^(ret$|jp\s+(?!nz\b|z\b|nc\b|c\b|po\b|pe\b|p\b|m\b))')


# ---------------------------------------------------------------------------
# ДЫРЫ ВНЕ КАРТИНКИ (цель vec). §17.5 рецепта Knight Lore.
#
# Картинка занимает строки 32..223 каждого из 32 столбцов плоскости (адрес = база + столбец*256
# + 32 + Y). Строки 224..255 столбца c и 0..31 столбца c+1 лежат в памяти ПОДРЯД — это 64
# непрерывных байта, куда не пишет ни рендер, ни очистка буфера, и на экране они всегда чёрные.
# 32 столбца дают 32 + 31*64 + 32 = 2048 байт. У Alien 8 отдана плоскость 1 (буфер 0xA000):
# её очистка (clear_scrn_buffer, a8_vec.py) с самого начала идёт ПОСТОЛБЦОВО по строкам 32..223,
# отдельной платы за дыры нет. ЗАМЕР (tools/holescan_vec.js): шесть сценариев по 200 итераций и
# все 128 комнат по 150 — в плоскости 1 тронуты РОВНО строки 32..223, ни одной записи в дыры.
#
# Туда уезжают самостоятельные процедуры нижнего региона. Темп не меняется: у i8080 нет ни кэша,
# ни штрафа за выравнивание — адрес процедуры на её скорость не влияет.
# ---------------------------------------------------------------------------
_H_ANYLBL = re.compile(r'^\.?[A-Za-z_][A-Za-z0-9_]*:')
_H_DATA = re.compile(r'(?i)^(DB|DW|DEFB|DEFW|DC)\b')
_H_PAD = re.compile(r'(?i)^(ORG|ALIGN)\b')
_H_SKIP = re.compile(r'(?i)^(ASSERT|DEVICE|SAVEBIN|SAVESNA|IF|ELSE|ENDIF|OUTPUT|DISPLAY|END)\b')
# Операнд IX-хелпера: `call il_ix_lda` + `db 7` — это не данные, а вторая половина одной
# развёрнутой инструкции (ix+d). Считается за 1 байт и блок кодом быть не перестаёт.
_H_IXCALL = re.compile(r'(?i)^call\s+il_')
_H_IXDB = re.compile(r'(?i)^db\s')
# метка в «адресном» выражении: high/low, сдвиг, маска, разность адресов. Такой блок двигать
# нельзя — его адрес либо читают по половине, либо он участвует в ASSERT'е.
_H_SENS = re.compile(r'(?i)(?:\b(?:high|low)\s*\(?\s*([A-Za-z_]\w*))'
                     r'|(?:([A-Za-z_]\w*)\s*(?:&|\||\^|\*|/|%|<<|>>|-))'
                     r'|(?:(?:&|\||\^|\*|/|%|<<|>>|-)\s*([A-Za-z_]\w*))')


def _nocom(s):
    """Снять комментарий, УВАЖАЯ строковые литералы: у Alien 8 есть `DB "CHAMBERS;;;;;;;;; "`
    (точки — заполнитель строки статуса), и наивный split(';') урезал бы её до одного байта."""
    q = None
    for i, ch in enumerate(s):
        if q:
            if ch == q:
                q = None
        elif ch in '"\'':
            q = ch
        elif ch == ';':
            return s[:i]
    return s


def _db_len(code):
    """Длина строки DB/DW в байтах. Ошибка в меньшую сторону ловится ASSERT'ом дыры при сборке."""
    mn = code.split()[0].upper()
    unit = 2 if mn in ('DW', 'DEFW') else 1
    rest = code[len(mn):].strip()
    items, cur, q, depth = [], '', None, 0
    for ch in rest:
        if q:
            cur += ch
            if ch == q:
                q = None
            continue
        if ch in '"\'':
            q = ch; cur += ch; continue
        if ch in '([':
            depth += 1
        elif ch in ')]':
            depth -= 1
        if ch == ',' and depth == 0:
            items.append(cur); cur = ''; continue
        cur += ch
    if cur.strip():
        items.append(cur)
    n = 0
    for it in items:
        it = it.strip()
        if len(it) >= 2 and it[0] in '"\'' and it[-1] == it[0]:
            n += (len(it) - 2) * unit
        else:
            n += unit
    return n


def a8_walk(lines, hi):
    """Адрес каждой строки исходника от начала до hi включительно; None — если счёт сбился.

    Нужен ровно для одного числа — сколько байт добивки съедает `ALIGN 256` перед таблицей
    a8_optr: блок, снятый ВЫШЕ этого ALIGN'а, нижний регион не укорачивает, пока добивка не
    перевалит через страницу. Сторож счёта — ASSERT'ы регионов в ассемблере и отдельная сверка
    с листингом (tools/check_plane1.py --walk): промах стоит места, но не поведения.

    ORG у Alien 8 бывает СИМВОЛИЧЕСКИМ (`ORG a8_low_resume` — возврат из разреза спрайтов),
    поэтому значения меток `X: equ $` запоминаются на ходу."""
    eqs, syms = {}, {}
    for l in lines:
        m = re.match(r'^([A-Za-z_]\w*)[: \t]+\s*(?:EQU|equ)\s+(.+)$', _nocom(l).strip())
        if m and m.group(2).strip() != '$':
            eqs[m.group(1)] = m.group(2).strip()

    def ev(e):
        for k, v in eqs.items():
            e = re.sub(r'\b' + k + r'\b', '(' + v + ')', e)
        return int(eval(e, {'__builtins__': {}}, {}))

    addr, at, prev_ix = None, [None] * (hi + 1), False
    for i in range(hi + 1):
        l = lines[i]
        m = _H_ANYLBL.match(l)
        body = _nocom(l[m.end():] if m else l)
        raw = body.strip()          # БЕЗ схлопывания пробелов: `DB "CIRCUITS  HEL"` — 13 байт,
        code = ' '.join(body.split())   # а схлопнутая строка дала бы 12 (ловушка, найдена --walk)
        at[i] = addr
        me = re.match(r'^([A-Za-z_]\w*)[: \t]+\s*(?:EQU|equ)\s+\$\s*$', _nocom(l).strip())
        if me:                                          # `метка: equ $` — запомнить адрес
            syms[me.group(1)] = addr
            continue
        if not code:
            continue
        u = code.upper()
        if u.startswith('ORG'):
            a = code.split(None, 1)[1].strip()
            try:
                addr = int(a, 0)
            except ValueError:
                addr = syms.get(a)
            prev_ix = False
            continue
        if addr is None:
            continue
        if u.startswith('ALIGN'):
            n = int(code.split()[1], 0)
            addr = (addr + n - 1) & ~(n - 1)
            prev_ix = False
            continue
        if u.startswith('DS'):
            try:
                addr += ev(code.split(None, 1)[1].split(',')[0])
            except Exception:
                return None
            prev_ix = False
            continue
        if _H_IXDB.match(code) and prev_ix:             # операнд IX-хелпера (1 или 2 байта)
            addr += _db_len(raw)
            prev_ix = False
            continue
        if _H_DATA.match(code):
            addr += _db_len(raw)
            prev_ix = False
            continue
        if re.search(r'(?i)\bequ\b', code) or _H_SKIP.match(code):
            continue
        n = _i8080_len(code)
        if n is None:
            return None                                 # неизвестная инструкция — счёт врёт
        addr += n
        prev_ix = bool(_H_IXCALL.match(code))
    return at


def a8_holes(base, pages=32):
    """Дыры одной плоскости: (адрес, размер). Строки 224..255 столбца c + 0..31 столбца c+1."""
    h = [(base, 32)]
    h += [(base + c * 256 + 224, 64) for c in range(pages - 1)]
    h.append((base + (pages - 1) * 256 + 224, 32))
    return h


A8_HOLE_PLANES = [0xA000]           # плоскость 1 (буфер): её дыры вне картинки отданы под код.
# Плоскость 0 (экран) в фазе игры тоже пишется только в строках 32..223 (замер holescan), но её
# vec_boot стирает СПЛОШНЫМ циклом 8 КБ — прежде чем брать и её дыры, очистку надо переписать
# постолбцово. Пока не понадобилось: плоскости 1 хватило.
A8_HOLE_BYTES = int(os.environ.get('A8_HOLE_BYTES', '-1'))   # -1 = сколько влезет
A8_HOLE_SKIP = tuple(x for x in os.environ.get('A8_HOLE_SKIP', '').split(',') if x)
A8_HOLES = [h for b in A8_HOLE_PLANES for h in a8_holes(b)]
A8_LOW_END = 'ASSERT $ <= 0x7f00'   # метка конца нижнего региона в собранном тексте


def a8_pack_holes(src, holes, need=-1, exclude=()):
    """Увезти мелкие самостоятельные процедуры нижнего региона в дыры вне картинки.

    Блок «метка: ... ret/jp» движим, если:
      * весь состоит из инструкций (операнд IX-хелпера `db d` — часть инструкции, см. _H_IXDB);
      * кончается БЕЗУСЛОВНОЙ передачей управления (иначе из него проваливаются вниз);
      * предыдущий блок тоже кончается безусловно и непуст (иначе метка-синоним или провал
        сверху) — в противном случае на месте блока остаётся `jp <метка>` (3 Б);
      * перед ним нет ORG/ALIGN (иначе на его адрес уедет следующий блок);
      * его метка не участвует в адресной арифметике (high/low, маска, сдвиг, разность) и ни
        в одном ASSERT'е: такие адреса читают по половине или проверяют.

    ALIGN 256 перед таблицей a8_optr. Блок, снятый ВЫШЕ него, нижний регион НЕ укорачивает —
    он ровно на свой размер удлиняет добивку, пока та не перевалит через страницу (тогда разом
    −256 Б). Поэтому блоки НИЖЕ ALIGN'а кладутся первыми (там байт за байт), а на снятое выше
    перебирается квота: лучший вариант считается точно и берётся он."""
    if not holes or need == 0:
        return src, 0, 0, ''
    lines = src.split('\n')
    end = next(i for i, l in enumerate(lines) if A8_LOW_END in l)
    nocom = '\n'.join(_nocom(l) for l in lines)
    sens = set()
    for l in nocom.split('\n'):
        if re.match(r'(?i)^\s*ASSERT\b', l):           # метка в ASSERT'е: её адрес проверяют
            sens.update(re.findall(r'[A-Za-z_]\w*', l))
    for m in _H_SENS.finditer(nocom):
        sens.add(m.group(1) or m.group(2) or m.group(3))
    # ---- разбор на блоки ----
    blocks, cur, low, prev_pad, prev_ix = [], None, False, False, False
    for i in range(end):
        raw = lines[i]
        m = _H_LBL.match(raw)
        ml = m or _H_ANYLBL.match(raw)
        body = _nocom(raw[ml.end():] if ml else raw)
        rawc = body.strip()                            # без схлопывания — для _db_len
        code = ' '.join(body.split())                  # пробелы схлопнуть: иначе `jp\s+` в _H_TERM
        if m:                                          # отступает назад и «jp nz, x» сойдёт за jp
            cur = {'name': m.group(1), 'i0': i, 'iend': i + 1, 'size': 0, 'ok': True,
                   'low': low, 'after_pad': prev_pad, 'last': ''}
            blocks.append(cur)
        if not code:
            continue
        if _H_PAD.match(code):
            prev_pad = True
            if code.upper().startswith('ORG'):
                a = code.split(None, 1)[1].strip()
                try:
                    low = 0x0100 <= int(a, 0) < 0x8000
                except ValueError:
                    low = (a == 'a8_low_resume')       # возврат из разреза спрайтов
        else:
            prev_pad = False
        ixdb = bool(_H_IXDB.match(code)) and prev_ix
        if cur is not None:
            if ixdb:
                cur['size'] += _db_len(rawc)   # `db d` (или `db d, n` у il_*_stn) — часть инструкции
                cur['iend'] = i + 1
            elif _H_HARD.match(code):
                cur['ok'] = False
            else:
                n = _i8080_len(code)
                if n is None:
                    cur['ok'] = False
                else:
                    cur['size'] += n
                    cur['last'] = code
                    cur['iend'] = i + 1
        prev_ix = bool(_H_IXCALL.match(code))
    # ---- ALIGN 256 нижнего региона: где он и какова добивка сейчас ----
    at = a8_walk(lines, end) or []
    aligns = []
    for i in range(end):
        ml = _H_ANYLBL.match(lines[i])
        code = ' '.join(_nocom(lines[i][ml.end():] if ml else lines[i]).split())
        if code.upper().startswith('ALIGN') and i < len(at) and at[i] is not None:
            n = int(code.split()[1], 0)
            if n >= 64 and 0x0100 <= at[i] < 0x8000:
                aligns.append((i, at[i], n))
    lastbig, pad0, amod = -1, 0, 256
    if aligns:
        lastbig, aaddr, amod = aligns[-1]
        pad0 = (-aaddr) % amod
    maxh = max(h[1] for h in holes)
    # ---- кандидаты ----
    cand = []
    for k, b in enumerate(blocks):
        pv = blocks[k - 1] if k else None
        if not (b['low'] and b['ok'] and 0 < b['size'] <= maxh):
            continue
        if b['after_pad'] or b['name'] in exclude or b['name'] in sens:
            continue
        if not _H_TERM.match(b['last']):
            continue
        b['stub'] = pv is None or pv['size'] == 0 or not (pv['ok'] and _H_TERM.match(pv['last']))
        b['net'] = b['size'] - (3 if b['stub'] else 0)
        if b['net'] < 1:                               # заглушка съедает весь выигрыш
            continue
        b['above'] = b['i0'] < lastbig
        cand.append(b)
    # НИЖЕ ALIGN'а — первыми (там выигрыш байт за байт), без заглушки — раньше, крупные — раньше
    cand.sort(key=lambda b: (b['above'], bool(b['stub']), -b['size'], b['name']))

    def lay(ycap):
        """Разложить кандидатов по дырам при квоте ycap на СНЯТОЕ ВЫШЕ ALIGN'а (None = без квоты)."""
        free = [[a, sz] for a, sz in holes]
        placed, below, above = [[] for _ in holes], 0, 0
        for b in cand:
            if need >= 0 and below + above >= need:
                break
            if b['above'] and ycap is not None and above + b['net'] > ycap:
                continue
            best = -1
            for j, (a, sz) in enumerate(free):         # ПЛОТНАЯ укладка: самый тесный подходящий
                if sz < b['size']:
                    continue
                if best < 0 or sz < free[best][1]:
                    best = j
            if best < 0:
                continue
            placed[best].append(b)
            free[best][0] += b['size']; free[best][1] -= b['size']
            if b['above']:
                above += b['net']
            else:
                below += b['net']
        # конец нижнего региона: снятое ниже ALIGN'а — байт за байт; снятое выше сначала уходит
        # в добивку и отыгрывается только страницами
        delta = -below - above + ((pad0 + above) % amod) - pad0 if lastbig >= 0 else -below - above
        return placed, below, above, delta

    tries = [lay(y) for y in [None] + [(-pad0) % amod + k * amod for k in range(12)]]
    placed, below, above, delta = min(tries, key=lambda r: (r[3], -(r[1] + r[2])))
    moved = sum(b['size'] for lst in placed for b in lst)
    nblk = sum(len(x) for x in placed)
    if not nblk:
        return src, 0, 0, ''
    # ---- вынести блоки ----
    drop, stubs = set(), {}
    for lst in placed:
        for b in lst:
            drop.update(range(b['i0'], b['iend']))
            if b['stub']:                              # оставить переход на уехавший блок
                stubs[b['i0']] = '        jp %s   ; блок уехал в дыру вне картинки' % b['name']
    out = ['', '; ==== ДЫРЫ ВНЕ КАРТИНКИ: строки 224..255/0..31 столбцов плоскости 1 (буфер) ====',
           '; Туда не пишет ни рендер, ни постолбцовая clear_scrn_buffer (замер holescan_vec.js),',
           '; на экране они всегда чёрные. Здесь лежат мелкие процедуры нижнего региона.']
    for j, (a, sz) in enumerate(holes):
        if not placed[j]:
            continue
        out.append('        ORG %#06x   ; дыра %d Б' % (a, sz))
        for b in placed[j]:
            out += [lines[i] for i in range(b['i0'], b['iend'])]
        out.append('        ASSERT $ <= %#06x   ; дыра %#06x (%d Б) не должна переполниться' % (a + sz, a, sz))
    kept = []
    for i, l in enumerate(lines):
        if i not in drop:
            kept.append(l)
        elif i in stubs:
            kept.append(stubs[i])
    ei = next(i for i, l in enumerate(kept) if A8_LOW_END in l)
    desc = ('увезено %d Б в %d процедур (ниже ALIGN %d Б, выше %d Б), нижний регион %+d Б'
            % (moved, nblk, below, above, delta))
    if os.environ.get('A8_HOLE_DEBUG'):
        for j, (a, sz) in enumerate(holes):
            for b in placed[j]:
                print('   %-28s %3d Б -> %#06x%s%s' % (b['name'], b['size'], a,
                      ' (+jp)' if b['stub'] else '', ' [выше ALIGN]' if b['above'] else ''),
                      file=sys.stderr)
    return '\n'.join(kept[:ei + 1] + out + kept[ei + 1:]), moved, nblk, desc


# ============ верхний регион в обход полосы HUD (плоскость 2) ============
# Под селектор БЕЛОГО HUD (как в Knight Lore) отдана плоскость 2, 0xC000..0xDFFF. Панель
# Alien 8 занимает нижние 32 строки картинки — ZX-строки 160..191, — а буфер Вектора
# столбцовый: адрес = база + столбец*256 + 32 + Y, Y = 223 - строка ZX. То есть панель
# лежит в смещениях 0x20..0x3F КАЖДОЙ из 32 страниц плоскости, а не одним куском.
#
# Верхний регион кода 0xD000..0xDFFF из-за этого рассыпается на окна: 32 байта в начале,
# потом по 224 (0xnn40..0xmm1F, через границу страницы) и 192 в конце. Раскладчик режет
# регион на блоки и раскладывает их по окнам, вставляя ORG; окна задаются списком —
# после переезда переменных (varmove) к ним добавятся окна страниц 0xC0..0xCF.
A8_HUD_LO, A8_HUD_HI = 0x20, 0x3F        # полоса панели в каждой странице плоскости 2
A8_PLANE2 = (0xC000, 0xE000)

# Резать ПЕРЕД этими метками нельзя, хотя формально можно:
_U_NOCUT = {
    # Вход в цепочку print_sprite патчится ТОЛЬКО младшим байтом `jp` (`add a, low (loc_D0BB+3)`
    # в print_sprite, `ld a, low (ps_fixe)` в ps_cw), поэтому pixel_chain_aligned..ps_fix —
    # ОДИН блок и он обязан целиком уместиться в одной странице (ASSERT'ы на месте).
    'loc_D0B9': 'цепочка: вход патчится младшим байтом jp',
    'ps_fixe': 'хвост клипа: ps_cw патчит младший байт ps_jrow',
}
_U_ONEPAGE = {'pixel_chain_aligned'}     # блок обязан лежать в ОДНОЙ странице
_U_DS = re.compile(r'(?i)^DS\b')
_U_CUTPREV = re.compile(r'(?i)^(ret$|jp\s+(?!nz\b|z\b|nc\b|c\b|po\b|pe\b|p\b|m\b)'
                        r'|DB\b|DW\b|DS\b|DEFB\b|DEFW\b|ORG\b|ALIGN\b)')


def a8_hud_windows(lo, hi):
    """Разрешённые окна в [lo, hi): всё, кроме полос page+0x20..page+0x3F плоскости 2."""
    wins, a = [], lo
    for p in range(lo & ~0xFF, hi, 0x100):
        if not A8_PLANE2[0] <= p < A8_PLANE2[1]:
            continue
        b0, b1 = max(p + A8_HUD_LO, lo), min(p + A8_HUD_HI + 1, hi)
        if b1 <= b0:
            continue
        if b0 > a:
            wins.append((a, b0 - a))
        a = max(a, b1)
    if hi > a:
        wins.append((a, hi - a))
    return wins


# Окна раскладчика — СПИСОК, а не одна пара границ. Сейчас верхний регион это 0xD000..0xDFFF:
# страницы 0xC0..0xC7 держит защитная зона спиллов, 0xC8..0xCF — переменные игры (0xC800..0xCF87).
# После их переезда в нижний регион (ветка varmove) сюда добавятся окна a8_hud_windows(0xC000,
# 0xD000); A8_HUD_LOW=1 включает их уже сейчас — проверить, что раскладчик берёт окна из списка.
A8_HUD_WINDOWS = ((a8_hud_windows(0xC000, 0xD000) if os.environ.get('A8_HUD_LOW') else [])
                  + a8_hud_windows(0xD000, 0xE000))


def _u_split(lines, at, i0, i1):
    """Разбить верхний регион (строки i0..i1) на блоки, которые можно двигать порознь.

    Резать можно ПЕРЕД меткой, если последняя выдающая байты инструкция до неё — безусловный
    переход/ret, данные или ORG/ALIGN: в такую метку проваливаться неоткуда, все входы в неё
    по имени. Ячейки `метка: DS n` остаются при своей процедуре. ALIGN, комментарии и пустые
    строки перед меткой уезжают в НОВЫЙ блок (ALIGN 8 перед vec_kbzx — часть таблицы)."""
    code, size, emits = {}, {}, {}
    for i in range(i0, i1):
        m = _H_ANYLBL.match(lines[i])
        c = ' '.join(_nocom(lines[i][m.end():] if m else lines[i]).split())
        code[i] = c
        pad = c.upper().startswith('ALIGN')
        size[i] = 0 if pad or at[i] is None or at[i + 1] is None else at[i + 1] - at[i]
        emits[i] = bool(c) and not pad and not _H_SKIP.match(c) and not re.search(r'(?i)\bequ\b', c)
    cuts, prev, got = [i0], '', False
    for i in range(i0 + 1, i1):
        m = _H_LBL.match(lines[i])
        if m and got and m.group(1) not in _U_NOCUT and not _U_DS.match(code[i]) \
                and _U_CUTPREV.match(prev):
            j = i                                   # ALIGN/комментарии — в новый блок
            while j > cuts[-1] and (not code[j - 1] or code[j - 1].upper().startswith('ALIGN')
                                    or lines[j - 1].lstrip().startswith(';')):
                j -= 1
            cuts.append(j)
            got = False
        if emits[i]:
            prev, got = code[i], True
        elif size[i]:
            got = True
    blocks = []
    for k, j in enumerate(cuts):
        end = cuts[k + 1] if k + 1 < len(cuts) else i1
        nm = next((_H_LBL.match(lines[x]).group(1) for x in range(j, end) if _H_LBL.match(lines[x])), '?')
        al = max([int(code[x].split()[1], 0) for x in range(j, end)
                  if code[x].upper().startswith('ALIGN')] or [1])
        blocks.append({'name': nm, 'lines': lines[j:end], 'size': sum(size[x] for x in range(j, end)),
                       'align': al, 'page': nm in _U_ONEPAGE})
    return blocks


def a8_layout_upper(src, windows, mark='ВЕРХНИЙ регион кода', endmark='блок Вектора не должен'):
    """Разложить верхний регион по окнам между полосами HUD, вставляя ORG между блоками.

    Длины блоков считаются тем же счётом, что у упаковщика дыр (a8_walk/_i8080_len/_db_len);
    сверка счёта с листингом — tools/check_plane2.py --walk. Порядок блоков свободен: каждый
    начинается с метки, в которую нельзя провалиться сверху (см. _u_split), а адрес процедуры
    на скорость i8080 не влияет — ни кэша, ни штрафа за выравнивание у него нет."""
    lines = src.split('\n')
    i0 = next(i for i, l in enumerate(lines) if mark in l)
    i1 = next(i for i, l in enumerate(lines) if endmark in l)
    at = a8_walk(lines, i1)
    if at is None or at[i1] is None:
        # Счёт всего текста сбивает ЛЮБАЯ неизвестная инструкция, в том числе в НИЖНЕМ регионе
        # (так роняла раскладчик порча гейта check_i8080: `bit n,r` — Z80-only). Раскладчику
        # нижний регион не нужен: считаем только сам верхний, от его собственного ORG.
        sub = a8_walk(lines[i0:i1 + 1], i1 - i0)
        assert sub and sub[-1] is not None, 'верхний регион: счёт адресов сбился'
        at = [None] * i0 + sub
    blocks = _u_split(lines, at, i0 + 1, i1)
    wins = [{'a': a, 'end': a + sz, 'cur': a, 'blk': []} for a, sz in windows]
    # тесная укладка: ограниченные блоки первыми, дальше крупные; окно — самое тесное подходящее
    for b in sorted(blocks, key=lambda b: (not b['page'], b['align'] == 1, -b['size'], b['name'])):
        best = None
        for w in wins:
            a = (w['cur'] + b['align'] - 1) & ~(b['align'] - 1)
            if a + b['size'] > w['end']:
                continue
            if b['page'] and b['size'] and (a >> 8) != ((a + b['size'] - 1) >> 8):
                continue
            if best is None or w['end'] - a - b['size'] < best[0]:
                best = (w['end'] - a - b['size'], a, w)
        assert best, ('верхний регион: блок %s (%d Б) не влез ни в одно окно'
                      % (b['name'], b['size']))
        _, a, w = best
        b['at'] = a
        w['cur'] = a + b['size']
        w['blk'].append(b)
    out = ['', '; ==== ВЕРХНИЙ РЕГИОН В ОБХОД ПОЛОСЫ HUD (плоскость 2) ====',
           '; Панель Alien 8 (ZX-строки 160..191) лежит в смещениях 0x%02X..0x%02X КАЖДОЙ страницы'
           % (A8_HUD_LO, A8_HUD_HI),
           '; плоскости 2, поэтому регион разложен по окнам между полосами (a8_layout_upper).']
    for w in wins:
        if not w['blk']:
            continue
        out.append('        ORG %#06x   ; окно %#06x..%#06x (%d Б)'
                   % (w['blk'][0]['at'], w['a'], w['end'] - 1, w['end'] - w['a']))
        for b in w['blk']:
            out += b['lines']
        out.append('        ASSERT $ <= %#06x   ; окно %#06x не должно налезть на полосу HUD'
                   % (w['end'], w['a']))
    used = sum(b['size'] for b in blocks)
    free = sum(w['end'] - w['a'] for w in wins) - used
    desc = ('%d блоков, %d Б в %d окнах из %d, свободно %d'
            % (len(blocks), used, sum(1 for w in wins if w['blk']), len(wins), free))
    if os.environ.get('A8_HUD_DEBUG'):
        for w in wins:
            print('   окно %#06x..%#06x (%3d Б): свободно %3d' % (w['a'], w['end'] - 1,
                  w['end'] - w['a'], w['end'] - w['cur']), file=sys.stderr)
            for b in w['blk']:
                print('      %#06x %4d Б  %-28s%s%s' % (b['at'], b['size'], b['name'],
                      ' [одна страница]' if b['page'] else '',
                      ' [ALIGN %d]' % b['align'] if b['align'] > 1 else ''), file=sys.stderr)
    return '\n'.join(lines[:i0] + out + lines[i1:]), desc


# ============================ склейка Alien 8 ============================
# Цель `lockstep`: логика 1:1 с оригиналом ZX, вывод заглушен, стенд подаёт
# байт-оракул mem[seed_2]. Раскладка памяти (код i8080 в раскладку ZX не влезает):
#   0x0000 загрузчик + scratch + хелперы ldir
#   0x0100 код и данные игры
#   ...    стек растёт вниз от A8_STACK
#   0xC000 переменные игры (0x788)
#   0xC800 vidbuf (6144)
#   0xE000 zx_vram (6144), он же shift_bits_table — при заглушенном рендере читателей нет
#   0xF800 zx_aram (768)
#   0xFB00 reverse_bits_table (256)
A8_STACK = 0xBC00
A8_VARS = 0xC000
A8_VIDBUF = 0xC800
A8_ZXVRAM = 0xE000
A8_ZXARAM = 0xF800
A8_REVTAB = 0xFB00

A8_HEADER = """
; ---- загрузчик (.r0m грузится с 0x0000, PC=0) ----
				ORG		0x0000
				di
				ld		sp, %#06x
				jp		START
; ---- scratch i8080-эмуляции + виртуальная клавиатура (область ПЗУ ZX, здесь это ОЗУ) ----
				ORG		0x0040
vkbd:			DS		8			; 8 рядов ZX-матрицы, активный ноль, 0xFF = ничего не нажато
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
a8_seed:		DS		1			; seed_1 при старте; стенд задаёт
a8_blk_off:		DS		2			; upd_42/43: смещения (ix+d), в оригинале патчились в код
a8_visit_bit:	DS		1			; build_screen_objects: номер бита SET n,(HL) (был опкодом)
a8_rnd_feed:	DS		1			; lockstep: байт mem[seed_2] из журнала ZX
__A8_NATIVE_SCRATCH__				ASSERT $ <= 0x00A0
				ORG		0x00A0		; хелперы ldir (scratch выше кончается ~0x76 — не пересекать!)
"""

A8_READ_KEY = """read_key:		; A = маска рядов (бит i=0 -> ряд i опрошен). Вместо ULA: AND выбранных рядов vkbd,
				; затем cpl/and 0x1F как в оригинале. Портит только A и флаги (как оригинал).
				push	hl
				push	bc
				push	de
				ld		c, a
				ld		hl, vkbd
				ld		b, 8
				ld		d, 0xFF
rk_loop:		ld		a, c
				rra
				ld		c, a
				jp		c, rk_skip
				ld		a, (hl)
				and		d
				ld		d, a
rk_skip:		inc		hl
				dec		b
				jp		nz, rk_loop
				ld		a, d
				cpl
				and		0x1F
				pop		de
				pop		bc
				pop		hl
				ret
; End of function read_key"""


def _stub_after_label(src, label, note):
    """Вставить `ret` сразу после строки `label:` — тело становится мёртвым."""
    pat = re.compile(r'^(' + re.escape(label) + r':[^\n]*\n)', re.M)
    m = pat.search(src)
    if not m:
        raise SystemExit(f"glue: метка {label} не найдена")
    return src[:m.end()] + f"        ret   ; ЗАГЛУШКА({note})\n" + src[m.end():]


# ---------------------------------------------------------------------------
# МЕНЮ И УПРАВЛЕНИЕ (обе цели): варианты ввода ZX вырезаны, меню — как у Городецкого.
# ---------------------------------------------------------------------------
A8_SETMODE_VEC = """a8_setmode:   ; номер режима (tmp_input_method 0..2) -> user_input_method + полоса подсветки.
        ; ПОДСВЕТКА — ФОН строки, а не инверсия картинки: буквы остаются белыми, как у Городецкого.
        ; Как: знакоместа строки заливаются 0xFF в ПЛОСКОСТИ 0 (экран), а буквы от фона отличает
        ; ПЛОСКОСТЬ 1 — столбцовый буфер: наш update_screen буфер НЕ обнуляет (он только копирует,
        ; в отличие от Knight Lore), поэтому в меню буфер побайтно повторяет экран. Палитра меню:
        ; индексы 8..11 (p0=1, p1=0) — синий фон полосы, 12..15 (p0=1, p1=1) — белые буквы.
        ; Точки с p0=0 остаются чёрными при любых p1..p3, поэтому плоскости 2 и 3 (а там лежат
        ; переменные, верхний регион кода и таблицы сдвига) наружу не проступают.
        ; Плоскость 2 под полосу НЕ ГОДИТСЯ вовсе: 0xC000..0xDFFF занято кодом и переменными,
        ; красить пришлось бы индексы с p0=0 — и весь этот код вылез бы рябью по всему кадру.
        ; Экран Вектора столбцовый: адрес = 0x8000 + столбец*256 + (Y + 32); print_8x8 идёт ВНИЗ
        ; по младшему байту (dec l), поэтому знакоместо строки Y занимает L = Y+25 .. Y+32.
        ld hl, vidbuf + 6*256 + 112   ; чистый текст трёх строк режимов из буфера
        ld de, 0x8000 + 6*256 + 112   ; в плоскость 0: снимает прежнюю полосу.
        ld bc, 28*256 + 21            ; столбцы 6..26, строки 112..167; два блита по 28 строк —
        call blit_to_screen           ; быстрый (стековый) путь blit_to_screen работает до 32
        ld hl, vidbuf + 6*256 + 140
        ld de, 0x8000 + 6*256 + 140
        ld bc, 28*256 + 21
        call blit_to_screen
        ld a, (tmp_input_method)
        ld e, a
        add a, a
        add a, e             ; *3
        ld e, a
        ld d, 0
        ld hl, a8_modetab
        add hl, de
        ld a, (hl)
        ld (user_input_method), a
        inc hl
        ld d, (hl)           ; нижняя строка полосы
        inc hl
        ld b, (hl)           ; ширина в знакоместах
        ld h, 0x86           ; X = 48 -> столбец 6 плоскости 0 (0x8000 + 6*256)
        ld a, 0xFF
a8_sm_col:
        ld l, d
        ld c, 8
a8_sm_row:
        ld (hl), a
        inc l
        dec c
        jr nz, a8_sm_row
        inc h
        dec b
        jr nz, a8_sm_col
a8_menu_exit:
        ; полосу за собой убирать не надо: в игру идут через clear_scrn_buffer + update_screen,
        ; а палитру перебивает vec_set_pal по цвету комнаты (крючок в hooks())
        ; ЗАМОК КНОПОК: игру запустили с зажатой FIRE — в игре она не должна тут же читаться как
        ; прыжок и «взять». Замок снимает сам a8_in_joy, когда кнопку отпустят.
        ; Сюда ПРОВАЛИВАЕТСЯ и a8_setmode — и это не вредно: в игре замок стоит ровно до первого
        ; кадра с отпущенной кнопкой, а смена раскладки в меню кнопкой не делается.
        ld a, 0xC0
        ld (vec_joylck), a
        ret
a8_joy_menu:   ; МЕНЮ: направление переключает раскладку ПО ФРОНТУ. По уровню одно отклонение стика
        ; пролистало бы все три за кадр-другой: menu_loop крутится много раз в кадр, а vec_joyraw
        ; обновляется раз в кадр. LEFT/UP — назад, RIGHT/DOWN — вперёд, по кругу 1->2->3->1.
        ; Кнопка (старт игры) сюда не заходит: она сведена к клавише '0' прямо в рядах ZX (vec_joy),
        ; и её разбирает та же строка меню, что и настоящую '0'.
        ld hl, vec_joyprv
        ld a, (vec_joyraw)
        and 0x0F             ; только направления
        ld b, a
        xor (hl)
        ld (hl), b
        and b                ; 1 = нажато сейчас и НЕ было в прошлый раз
        ret z
        and 0x09             ; RIGHT | DOWN -> следующая раскладка
        ld hl, tmp_input_method   ; номер раскладки 0..2
        ld a, (hl)           ; ld a,(hl) флагов не трогает — Z ещё от `and`
        jr z, a8_jm_prev
        inc a
        cp 3
        jr c, a8_jm_set
        xor a
        jr a8_jm_set
a8_jm_prev:
        and a
        jr nz, a8_jm_dec
        ld a, 3
a8_jm_dec:
        dec a
a8_jm_set:
        ld (hl), a
        jp a8_setmode        ; раскладка + полоса подсветки
a8_modetab:   ; режим: user_input_method, нижняя строка полосы (Y+25), ширина в знакоместах
        DB 0, 160, 10   ; 1 KEYBOARD            (Y = 135, 10 знаков)
        DB 4, 136, 8    ; 2 CURSOR              (Y = 111,  8 знаков)
        DB 8, 112, 21   ; 3 DIRECTIONAL CONTROL (Y =  87, 21 знак)
"""

A8_VEC_INPUT = """a8_vec_input:   ; ТРИ РАСКЛАДКИ, читаются ПРЯМО ИЗ МАТРИЦЫ ВЕКТОРА (vec_kbmat, active-high).
        ; Таблица: младший байт адреса ряда, маска клавиш ряда, биты user_input; 0 = конец списка.
        ; Биты user_input: 0 влево, 1 вправо, 2 вперёд, 3 прыжок, 4 взять (поворотный режим,
        ; в directional этот бит — «вниз»), 5 взять (directional; chk_pickup_drop его сдвигает).
        ; Ряды Вектора: 0 ВК(0x04)/стрелки, 2 цифры 0..7, 3 цифры 8,9, 4 @ABCDEFG, 5 HIJKLMNO,
        ; 6 PQRSTUVW, 7 XYZ[\\]^ПРБ.
        ld de, a8_in_t3
        ld a, (user_input_method)
        and 8                  ; 3 DIRECTIONAL CONTROL
        jr nz, a8_in_scan
        ld de, a8_in_t2
        ld a, (user_input_method)
        and 4                  ; 2 CURSOR
        jr nz, a8_in_scan
        ld de, a8_in_t1        ; 1 KEYBOARD (user_input_method = 0)
a8_in_scan:
        ld c, 0
        ld h, high vec_kbmat
a8_in_1:
        ld a, (de)             ; младший байт ряда (0 = конец)
        and a
        jr z, a8_in_joy
        ld l, a
        inc de
        ld a, (de)             ; маска клавиш ряда
        and (hl)
        inc de
        ld a, (de)             ; биты user_input; ld a,(de) и inc de флагов не трогают,
        inc de                 ; поэтому Z здесь ещё от `and (hl)`
        jr z, a8_in_1
        or c
        ld c, a
        jr a8_in_1
a8_in_joy:   ; ДЖОЙСТИК РАБОТАЕТ ВСЕГДА, ПАРАЛЛЕЛЬНО С КЛАВИАТУРОЙ (биты просто складываются с
        ; набранными, ничего не отменяется) и сводится ровно к тем же битам user_input, что клавиши
        ; ВЫБРАННОЙ раскладки. Состояние кладёт в vec_joyraw кадровый ISR (vec_joy).
        ; Таблица: маска джойстика (active-high), биты user_input; 0 = конец.
        ; Сюда НЕ заходят по раннему выходу «конец игры» (там jp a8_in_store с C = 0) — и правильно:
        ; после конца игры ввода нет ни с клавиатуры, ни со стика.
        ld hl, a8_joy_r        ; раскладки 1 и 2 — поворотные
        ld a, (user_input_method)
        and 8                  ; 3 DIRECTIONAL CONTROL
        jr z, a8_joy_go
        ld hl, a8_joy_d
a8_joy_go:
        ; ЗАМОК КНОПОК: игру запустили, не отпустив FIRE, — первый же кадр игры прочёл бы её как
        ; прыжок. a8_menu_exit пишет в vec_joylck 0xC0 (обе кнопки), здесь замок держится, пока
        ; кнопку не отпустят, и открывается сам (lck &= raw).
        ld a, (vec_joylck)
        ld b, a
        ld a, (vec_joyraw)
        and b
        ld (vec_joylck), a
        cpl
        ld b, a
        ld a, (vec_joyraw)
        and b
        ld b, a                ; B = действующее состояние джойстика
        jr z, a8_in_store
a8_joy_1:
        ld a, (hl)             ; маска джойстика (0 = конец таблицы)
        inc hl
        and a
        jr z, a8_in_store
        and b
        ld a, (hl)             ; биты user_input; ld a,(hl) и inc hl флагов не трогают,
        inc hl                 ; поэтому Z здесь ещё от `and b`
        jr z, a8_joy_1
        or c
        ld c, a
        jr a8_joy_1
a8_in_store:
        ld a, c
        ld (user_input), a
        ret
        ; End of function check_user_input
a8_anykey:   ; «ЛЮБАЯ КЛАВИША» = ряды ZX ПЛЮС ВЕСЬ ДЖОЙСТИК (подставляется в play_audio_until_keypress).
        ; Кнопка в рядах ZX и так есть — vec_joy прижимает ей '0'. А НАПРАВЛЕНИЯ в ряды не сведены
        ; (в ряду 0 матрицы Вектора со стрелками лежит ВК, ложная пауза = зависание), и без этой
        ; строки мелодия меню играла бы свои полминуты, а стик за это время не пролистал бы ни одной
        ; раскладки: menu_loop висит внутри play_audio_until_keypress и до a8_ctl_done не доходит.
        ; У клавиатуры ровно так же: ЛЮБАЯ клавиша рвёт мелодию, и только поэтому работают '1'/'2'/'3'.
        xor a
        call read_key
        ret nz
        ld a, (vec_joyraw)
        and a
        ret
a8_joy_r:   ; 1 KEYBOARD и 2 CURSOR (поворотные): «вниз» не заведено — его нет и у клавиатуры
        DB 0x02, 0x01   ; LEFT  -> поворот влево  (как Z / стрелка влево)
        DB 0x01, 0x02   ; RIGHT -> поворот вправо (как X / стрелка вправо)
        DB 0x04, 0x04   ; UP    -> шаг вперёд     (как A / стрелка вверх)
        DB 0x40, 0x08   ; FIRE1 -> прыжок         (как Q / пробел)
        DB 0x80, 0x10   ; FIRE2 -> взять/бросить  (как цифры / стрелка вниз)
        DB 0
a8_joy_d:   ; 3 DIRECTIONAL CONTROL: стик = стороны света, «взять» на бите 5
        DB 0x02, 0x01   ; LEFT  -> влево          (как стрелка влево)
        DB 0x01, 0x02   ; RIGHT -> вправо         (как стрелка вправо)
        DB 0x04, 0x04   ; UP    -> вверх          (как стрелка вверх)
        DB 0x08, 0x10   ; DOWN  -> вниз           (как стрелка вниз)
        DB 0x40, 0x08   ; FIRE1 -> прыжок         (как пробел)
        DB 0x80, 0x20   ; FIRE2 -> взять/бросить  (как цифры 0..7)
        DB 0
a8_in_t1:   ; 1 KEYBOARD — КЛАВИШИ ОРИГИНАЛА Alien 8 (расшифровка `keyboard:` листинга tcdev):
            ; Z C M B влево, X V N SYM вправо, A..G H..L вперёд, Q..T P..Y прыжок, цифры взять.
            ; ZX ENTER (тоже «вперёд») на Вектор не перенесён: ВК отдана ПАУЗЕ, см. audio_CE22.
            ; ZX SYMBOL SHIFT лежит в позиции «\\» матрицы Вектора — маска ряда 7 общая, даром.
        DB low (vec_kbmat+7), 0x04, 0x01   ; Z             -> влево
        DB low (vec_kbmat+4), 0x0C, 0x01   ; C B           -> влево
        DB low (vec_kbmat+5), 0x20, 0x01   ; M             -> влево
        DB low (vec_kbmat+7), 0x11, 0x02   ; X \\ (SYM)     -> вправо
        DB low (vec_kbmat+6), 0x40, 0x02   ; V             -> вправо
        DB low (vec_kbmat+5), 0x40, 0x02   ; N             -> вправо
        DB low (vec_kbmat+4), 0xD2, 0x04   ; A D F G       -> вперёд
        DB low (vec_kbmat+6), 0x08, 0x04   ; S             -> вперёд
        DB low (vec_kbmat+5), 0x1D, 0x04   ; H J K L       -> вперёд
        DB low (vec_kbmat+6), 0xB7, 0x08   ; P Q R T U W   -> прыжок
        DB low (vec_kbmat+4), 0x20, 0x08   ; E             -> прыжок
        DB low (vec_kbmat+5), 0x82, 0x08   ; I O           -> прыжок
        DB low (vec_kbmat+7), 0x02, 0x08   ; Y             -> прыжок
        DB low (vec_kbmat+2), 0xFF, 0x10   ; 0..7          -> взять/бросить
        DB low (vec_kbmat+3), 0x03, 0x10   ; 8 9           -> взять/бросить
        DB 0
a8_in_t3:   ; 3 DIRECTIONAL CONTROL = 2 CURSOR плюс цифры: у Городецкого обе раскладки дают
            ; стрелкам ОДНИ И ТЕ ЖЕ биты (влево 0, вправо 1, вверх 2, вниз 4), пробел — прыжок,
            ; и отличается только «взять»: в directional это цифры (бит 5), в cursor — «вниз».
            ; Поэтому t3 — это t2 с одной лишней записью впереди, а не вторая копия списка.
        DB low (vec_kbmat+2), 0xFF, 0x20   ; 0..7          -> взять (directional: бит 5)
a8_in_t2:   ; 2 CURSOR: стрелки влево/вправо поворот, вверх вперёд, пробел прыжок, вниз взять
        DB low (vec_kbmat+0), 0x10, 0x01   ; стрелка влево
        DB low (vec_kbmat+0), 0x40, 0x02   ; стрелка вправо
        DB low (vec_kbmat+0), 0x20, 0x04   ; стрелка вверх
        DB low (vec_kbmat+0), 0x80, 0x10   ; стрелка вниз
        DB low (vec_kbmat+7), 0x80, 0x08   ; пробел
        DB 0
        ASSERT (low vec_kbmat) != 0   ; 0 — признак конца таблицы раскладки
"""

A8_PAUSE_VEC = """audio_CE22:   ; ПАУЗА. Оригинал: ПРОБЕЛ (ряд ZX 0+7, бит 0) и ни одной другой клавиши тех же
        ; рядов (`and 0x1E : ret nz`). На Векторе пробел стал прыжком в раскладках 2 и 3, и пауза
        ; переехала на ВК — как у Городецкого. Матрицу читаем НАПРЯМУЮ: гонять read_port ради
        ; маски одного ряда не за чем. Защита оригинала сохранена дословно: ВК лежит в ряду 0
        ; ВМЕСТЕ СО СТРЕЛКАМИ (клавиши движения раскладок 2 и 3), и без проверки «ни одной
        ; стрелки» ходьба ставила бы ложную паузу — а выглядит она ровно как зависание (Knight
        ; Lore, 65962fe). Ожидание отпускания/нажатия смотрит только на ВК, как в оригинале.
        ld a, (vec_kbmat+0)
        and 0xF4        ; ВК (0x04) + стрелки (0x10 0x20 0x40 0x80)
        cp 4
        ret nz
a8_pz_rel:
        ld a, (vec_kbmat+0)
        and 4
        jr nz, a8_pz_rel
        call toggle_FE_bit4_x24
a8_pz_wait:
        ld a, (vec_kbmat+0)
        and 4
        jr z, a8_pz_wait
a8_pz_rel2:
        ld a, (vec_kbmat+0)
        and 4
        jr nz, a8_pz_rel2
        jp toggle_FE_bit4_x24
        ; End of function audio_CE22
"""


def a8_cut_attrs(src):
    """Атрибутная память ZX — выбросить (§17.3 рецепта KL, цель `vec`).

    На Векторе цвет — палитра, а не знакоместа, и 768 байт `zxaram` были мусорным ОЗУ в
    ЗАЩИТНОЙ ЗОНЕ 0xC000-0xC7FF. Зона лежит в ПЛОСКОСТИ 2, а под цветной HUD (как в Knight
    Lore) плоскость 2 нужна целиком под селектор — значит ни атрибутов, ни спиллов печати там
    быть не должно. Вырезаны ВСЕ писатели атрибутов; сохранены крючки Вектора, поставленные
    a8_vec.glue/hooks: `fill_attr` -> vec_set_pal (цвет комнаты и экрана «RE-PROGRAMMING»),
    `clear_scrn` -> vec_wipe0, палитра меню.

    Что вырезано (каждая замена — с assert на число):
      calc_attrib_addr           расчёт адреса атрибута (3 вызывателя, см. ниже)
      upd_55_58_to_5B            заливка атрибутов под объектом (тело -> ret, 11 вызывателей)
      print_text/_in_colour      адрес атрибута, байт атрибута на символ; заодно ушли ЧЕТЫРЕ
                                 `exx` и три `ex af,af'` — у i8080 это обмен с ячейкой (33 Б)
      sub_BCAB                   заливка 3x3 под предметом в панели
      colour_something           две заливки fill_DE, sub_A7AE, два байта 0x47, окно 3x3
      sub_A7AE + byte_A7CA       рисунок панели атрибутами (тело и данные)
      colour_panel               мёртвая и до нас (вызывателей нет) — снята целиком
      clr_attr/fill_attr         тело; метка fill_attr ОСТАЁТСЯ — на ней висит крючок палитры
      loc_B005                   пробег «перекраска» в гибели (звук sub_B5EE и задержка целы)
      zxaram/zxvram              сами сегменты

    НЕ трогаем: `set_room_attrs` (правит АТРИБУТЫ КОМНАТ в location_tbl — из них берётся
    палитра), `curr_room_attrib`, `tmp_attrib` (ячейка сравнивается локстепом, её пишет
    display_text_list), `BC_to_Attr_In_DE` (на Векторе это адрес в плоскости 0, см. a8_vec)."""
    def cut(old, new, name, count=1):
        nonlocal src
        n = src.count(old)
        assert n == count, "a8_cut_attrs: %s — вхождений %d, ждали %d" % (name, n, count)
        src = src.replace(old, new)

    def cutre(pat, new, name, count=1, flags=re.M | re.S):
        nonlocal src
        src, n = re.subn(pat, lambda m: new, src, count=count, flags=flags)
        assert n == count, "a8_cut_attrs: %s (%d)" % (name, n)

    # ---- 1. colour_something: остаются fill_attr (палитра), sub_BCAB, счётчик и print_lives ----
    cut("""        ld a, 0x47   ; 'G'
        ld de,  zxaram+0x2CE
        ld b, 2
        call fill_DE
        ld de,  zxaram+0x2EE
        ld b, 4
        call fill_DE
        call sub_A7AE
        call sub_BCAB
""", "        call sub_BCAB\n", 'colour_something: заливки панели')
    cut("""        ld a, (curr_room_attrib)
        cpl
        and 7
        add a, 0x42   ; 'B'
        ld (light_years_attr), a
        ld de, light_years_attr
""", "        ld de, light_years_attr   ; байт атрибута строки print_text пропускает\n",
        'colour_something: цвет счётчика')
    cut("""        call sub_A7A3
        ld hl,  zxaram+0x284
        ld (hl), 0x47   ; 'G'
        inc hl
        ld (hl), 0x47   ; 'G'
        ld hl,  zxaram+0x241
        ld bc, 0x303
        ld a, (light_years_attr)
        call fill_window
        jp print_lives
""", "        call sub_A7A3\n        jp print_lives\n", 'colour_something: окно счётчика')
    # ---- 2. sub_A7AE и её данные (рисунок панели атрибутами) ----
    cutre(r'^sub_A7AE:\n.*?        DB 0x42, 0x42, 0x42, 0x42\n', '', 'sub_A7AE + byte_A7CA')
    # ---- 3. upd_55_58_to_5B: заливка атрибутов под объектом ----
    cutre(r'^upd_55_58_to_5B:\n.*?        ; End of function upd_55_58_to_5B\n',
          "upd_55_58_to_5B:\n        ret   ; Вектор: атрибутов ZX нет\n"
          "        ; End of function upd_55_58_to_5B\n", 'upd_55_58_to_5B')
    # ---- 4. print_text / print_text_in_colour ----
    # Байт атрибута строки (print_text) и tmp_attrib (print_text_in_colour) больше не нужны,
    # `push bc` держал XY только для calc_attrib_addr, а альтернативный набор — адрес атрибута.
    cut("""        ld a, (tmp_attrib)
        ex af, af'
        jr loc_BBC2
""", "        jr loc_BBC2\n", 'print_text_in_colour: атрибут')
    cut("""        ld a, (de)
        ex af, af'
        inc de
loc_BBC2:
        exx
        pop hl
        push de
        call calc_attrib_addr
        ld l, e
        ld h, d
        pop de
loc_BBCB:
        exx
""", "        inc de   ; байт атрибута строки — на Векторе только пропустить\nloc_BBC2:\nloc_BBCB:\n",
        'print_text: адрес атрибута')
    cut("""        pop bc
        push bc
        call calc_screen_buffer_addr
""", "        pop bc\n        call calc_screen_buffer_addr\n", 'print_text: XY для атрибута', count=2)
    cut("""        exx
        ex af, af'
        ld (hl), a
        inc l
        ex af, af'
        jr loc_BBCB
""", "        jr loc_BBCB\n", 'print_text: байт атрибута на символ')
    cut("""        exx
        ex af, af'
        ld (hl), a
        exx
        ret
""", "        ret\n", 'print_text: байт атрибута последнего символа')
    # ---- 5. sub_BCAB: заливка 3x3 под предметом панели ----
    cut("""        push bc
        push hl
        ld a, (hl)
        and 0xF
        ld e, a
        ld d, 0
        ld hl, byte_BD34
        add hl, de
        ld c, (hl)
        ld l, (ix+26)
        ld a, (ix+27)
        add a, 0x17
        ld h, a
        call calc_attrib_addr
        ex de, hl
        ld a, c
        ld bc, 0x303
        call fill_window
        pop hl
        pop bc
""", "", 'sub_BCAB: заливка под предметом')
    # ---- 6. colour_panel: вызывателей нет и в оригинале ----
    cutre(r'^colour_panel:\n        xor a\n.*?        jp fill_window\n', '', 'colour_panel')
    # ---- 7. clr_attr/fill_attr: тело долой, метка fill_attr держит крючок палитры ----
    cut("""fill_attr:
        ld e, a
        ld hl, zxaram
        ld bc, 0x300
        jr fill_mem
""", "fill_attr:\n        ret   ; Вектор: атрибутов ZX нет (крючок палитры ставит a8_vec.glue)\n",
        'fill_attr')
    # ---- 8. «перекраска» в гибели: пробег по атрибутам долой, звук и задержка целы ----
    # Пробег красит 768 знакомест и служит ЗАДЕРЖКОЙ между 16 звуками «перекраски»: сами
    # записи в атрибуты уходят, счёт остаётся — иначе гибель отыграет мелодию вчетверо быстрее.
    # Строки `loc_B00B:` и `jr nz, loc_B00B` ОБЯЗАНЫ уцелеть: на них стоит сайт a8_sound_ay
    # (лесенка вместо эффекта), а это чужой файл.
    cut("""loc_B00B:
        ld a, (hl)
        and 0xF8   ; 'ø'
        ld e, a
        ld a, (hl)
        inc a
        and 7
        or e
        ld (hl), a
        inc hl
        dec bc
""", "loc_B00B:   ; Вектор: записи в атрибуты вырезаны, счёт остался задержкой\n        dec bc\n",
        'loc_B005: перекраска')
    cut("""loc_B005:
        ld hl, zxaram
        ld bc, 0x300
""", "loc_B005:\n        ld bc, 0x300\n", 'loc_B005: адрес атрибутов')
    # ---- 9. сам расчёт адреса ----
    cutre(r'^calc_attrib_addr:\n.*?        ; End of function calc_attrib_addr\n', '', 'calc_attrib_addr')
    # ---- 10. сегменты: zxaram уходит целиком, zxvram остаётся двумя ссылками ----
    # (их снимает a8_vec.glue: loc_CE60 -> vec_wipe0 и update_screen -> блок Вектора)
    cutre(r'^        ORG 0x5800\nzxaram:\n        DS 0x300\n', '', 'сегмент zxaram')
    cutre(r'^        ORG 0x4000\nzxvram:\n        DS 0x1800\n', '', 'сегмент zxvram')
    assert 'zxaram' not in src, "остались ссылки на zxaram: " + str(re.findall(r'[^\n]*zxaram[^\n]*', src))
    left = re.findall(r'[^\n]*zxvram[^\n]*', src)
    assert left == ['        ld hl, zxvram', '        ld de,  zxvram+0x17E0'], left
    return src

def a8_cut_controls(src, vec=False):
    """Варианты ввода ZX (Kempston, курсорный джойстик, Interface II) вырезаны — на Векторе
    только клавиатура. Меню повторяет порт Городецкого (caglrc.cc/scalar/ware/558): шесть строк —
    заголовок, три режима управления, «0 START GAME», копирайт; выбранный режим подсвечен
    цветной полосой. Копирайт ОРИГИНАЛЬНЫЙ («© 1985 A.C.G.»): это порт, а не подмена авторства.

        1 KEYBOARD              клавиши оригинала Alien 8 (Z C M B / X V N / A..L / Q..Y / цифры)
        2 CURSOR                стрелки влево/вправо поворот, вверх вперёд, пробел прыжок, вниз взять
        3 DIRECTIONAL CONTROL   стрелки = стороны света, пробел прыжок, цифры 0..7 взять

    user_input_method: 0 / 4 / 8 (бит 3 = directional, как в оригинале; 0 у режима 1 ОБЯЗАТЕЛЕН —
    ячейка сравнивается в локстепе, на ZX там 0). Номер режима 0..2 живёт в tmp_input_method:
    ячейка освободилась (её читал только «сменился ли режим» в меню) и лежит ВЫШЕ objs_wiped_cnt,
    то есть НЕ обнуляется между заходами — режим переживает игру, как old_input_method у KL.

    Меню на обеих целях одинаковое; ввод и пауза через матрицу Вектора — только vec (`vec=True`),
    на цели lockstep остаётся оригинальный `keyboard:` по рядам ZX, и локстеп судит ту же логику."""
    def cut(pat, name, repl='', flags=re.S, count=1):
        nonlocal src
        src, n = re.subn(pat, lambda m: repl, src, count=count, flags=flags)
        assert n == count, "a8_cut_controls: %s (%d)" % (name, n)

    # ---- меню: 6 строк вместо 8 ----
    # Y с шагом 24 (как у Городецкого), X строк режимов 48 — как в оригинале: самая длинная
    # («3 DIRECTIONAL CONTROL», 21 знак) встаёт по центру кадра. Заголовок и копирайт — на своих
    # исходных местах. Цвета на Векторе не нужны (атрибутов нет), но display_text_list читает по
    # байту на строку — их должно быть ровно 6.
    cut(r'menu_colours:\n        DB 0x43, 0x44, 0x44, 0x44, 0x44, 0x45, 0x47, 0x47\n', 'menu_colours',
        'menu_colours:\n        DB 0x43, 0x44, 0x44, 0x45, 0x47, 0x47\n')
    cut(r'menu_xy:\n(?:        DB 0x[0-9A-F]{2}, 0x[0-9A-F]{2}\n){8}', 'menu_xy',
        'menu_xy:\n'
        '        DB 104, 159   ; ALIEN 8 (на исходном месте)\n'
        '        DB 48, 135    ; 1 KEYBOARD\n'
        '        DB 48, 111    ; 2 CURSOR\n'
        '        DB 48, 87     ; 3 DIRECTIONAL CONTROL\n'
        '        DB 48, 63     ; 0 START GAME\n'
        '        DB 80, 39     ; (c) 1985 A.C.G. (на исходном месте)\n')
    # строки: «3 DIRECTIONAL CONTROL» — оригинальная (сменён только номер), «2 CURSOR» набрана
    # заново. Шрифт ASCII, бит 7 последнего байта = конец строки.
    cut(r'a2KempstonJoystick:\n.*?(?=a0StartGame:)', 'строки режимов',
        'a2Cursor:\n        DB "2 CURSO"\n        DB 0xD2\n'
        'a3DirectionalControl:\n        DB "3 DIRECTIONAL CONTRO"\n        DB 0xCC\n')
    src, _n = re.subn(r'(display_menu:\n(?:[^\n]*\n){4}        ld b, )8\n', r'\g<1>6\n', src, count=1)
    assert _n == 1, 'a8_cut_controls: display_menu b'

    # ---- вход в меню: рамка и выгрузка на экран как в оригинале, затем полоса подсветки ----
    # Цикл `res 7,(hl)` по menu_colours снимал мерцание выбранной строки (атрибут FLASH) — на
    # Векторе атрибутов нет, а подсветка теперь своя.
    cut(r'do_menu_selection:\n        xor a\n        ld \(suppress_border\), a\n'
        r'        ld hl, menu_colours\n        ld b, 8\nloc_BA87:\n        res 7, \(hl\)\n'
        r'        inc hl\n        djnz loc_BA87\n        call clear_scrn_buffer\n'
        r'        call display_menu\n        call flash_menu\n', 'do_menu_selection head',
        'do_menu_selection:\n        xor a\n        ld (suppress_border), a\n'
        '        call clear_scrn_buffer\n'
        '        call display_menu   ; текст, рамка, выгрузка на экран\n'
        '        call a8_setmode     ; режим + полоса подсветки\n')
    # ---- цикл меню: клавиши 1/2/3 выбирают режим, «0» — старт ----
    # Полоса живёт в ПЛОСКОСТИ 0 и между кадрами никем не трогается: display_menu в цикле пишет
    # только в буфер (suppress_border уже взведён, update_screen второй раз не зовётся).
    cut(r"        ld a, 0xF7   ; '÷'\n        call read_key\n        ld e, a\n"
        r".*?        ; End of function do_menu_selection\n", 'menu loop tail',
        "        ld a, 0xF7   ; ряд ZX 3: клавиши 1..5\n"
        "        call read_key\n"
        "        and 7               ; '1' / '2' / '3' — режим управления\n"
        "        jr z, a8_ctl_done\n"
        "        ld b, 0xFF          ; B = номер младшего нажатого бита (and 7 обнулил перенос)\n"
        "a8_ctl_idx:\n"
        "        inc b\n"
        "        rra\n"
        "        jr nc, a8_ctl_idx\n"
        "        ld hl, tmp_input_method   ; номер режима 0..2 (переживает игру)\n"
        "        ld a, b\n"
        "        cp (hl)\n"
        "        jr z, a8_ctl_done   ; тот же режим — экран не трогаем\n"
        "        ld (hl), a\n"
        "        call a8_setmode\n"
        "a8_ctl_done:\n"
        "        call a8_joy_menu    ; джойстик: раскладка по фронту направления\n"
        "        ld a, 0xEF          ; ряд ZX 4: клавиши 0,9,8,7,6 ('0' прижимает и FIRE, см. vec_joy)\n"
        "        call read_key\n"
        "        bit 0, a            ; '0' — начать игру\n"
        "        jp nz, a8_menu_exit\n"
        "        ld hl, seed_1\n"
        "        inc (hl)\n"
        "        jp menu_loop\n"
        "        ; End of function do_menu_selection\n")
    cut(r'flash_menu:\n.*?        ; End of function flash_menu\n', 'flash_menu',
        A8_SETMODE_VEC if vec else
        'a8_setmode:\n        ret   ; полоса подсветки — только цель vec (плоскость 0 + палитра)\n'
        'a8_joy_menu:\n        ret   ; джойстик — только цель vec (порт 0x0E)\n'
        'a8_menu_exit:\n        ret\n')
    cut(r'toggle_selected:\n.*?        ; End of function toggle_selected\n', 'toggle_selected')

    # ---- ввод: только клавиатура ----
    # Диспетчер вариантов ZX и три их обработчика долой; бит 3 (directional) работает теперь
    # сам по себе — в оригинале он проверялся ТОЛЬКО вместе с джойстиком (`and 6`).
    cut(r'        ld a, \(user_input_method\)\n        rrca\n        and 3\n'
        r'        jp z, keyboard\n.*?(?=keyboard:\n)', 'диспетчер вариантов ввода')
    cut(r'chk_pickup_drop:\n        ld hl, user_input_method\n        ld a, \(hl\)\n'
        r'        and 6\n        ld a, \(user_input\)\n        jr z, loc_BD68\n'
        r'        bit 3, \(hl\)\n        jr z, loc_BD68\n', 'chk_pickup_drop',
        'chk_pickup_drop:\n        ld hl, user_input_method\n'
        '        bit 3, (hl)   ; directional: «взять» в бите 5 (у оригинала ещё and 6 — джойстик)\n'
        '        ld a, (user_input)\n        jr z, loc_BD68\n')
    cut(r'handle_left_right:\n        ld hl, user_input_method\n        ld a, \(hl\)\n'
        r'        and 6\n        jr z, loc_C18F\n        bit 3, \(hl\)\n        jr z, loc_C18F\n',
        'handle_left_right',
        'handle_left_right:\n        ld hl, user_input_method\n'
        '        bit 3, (hl)   ; directional (у оригинала ещё and 6 — джойстик)\n'
        '        jr z, loc_C18F\n')
    if vec:
        # Ряды ZX для игрока не годятся: у оригинала «вперёд» — это ZX ENTER, а на Векторе ВК
        # отдана паузе; сами ряды остаются для меню, «любой клавиши» в мелодиях и read_key.
        cut(r'keyboard:\n.*?        ; End of function check_user_input\n', 'keyboard -> матрица Вектора',
            A8_VEC_INPUT)
        cut(r'        jp nz, finished_input\n', 'ранний выход check_user_input',
            '        jp nz, a8_in_store   ; конец игры: ввод не читаем (C = 0)\n')
        assert 'finished_input' not in src, 'остались ссылки на finished_input'
        cut(r'audio_CE22:\n.*?        ; End of function audio_CE22\n', 'пауза', A8_PAUSE_VEC)
    return src


def a8_no_delay(src):
    """Искусственная задержка оригинала (B * 0x300 пустых витков при < 6 нарисованных объектов).

    На ZX она выравнивала темп в лёгких комнатах; i8080-Вектор и без неё вдвое медленнее
    оригинала (11.7 против 24.8 итер/с в стартовой), а темп теперь держит ограничитель
    `vec_pace`. Цикл снимается ЦЕЛИКОМ (-10 Б), а не глушится переходом.

    Состояние игры не меняется — доказательство по коду:
    * цикл пишет только HL, A, B и флаги, в память не ходит;
    * на loc_A715 те же HL/A/B/флаги приходят и по двум ДРУГИМ путям (`jp m, loc_A715`
      при cnt > 6 и `jr z, loc_A715` при cnt == 6), где HL — что осталось от
      render_dynamic_objects, B = 6-cnt, флаги — от `add a, 6`. Значит на loc_A715 ни
      один из этих регистров не может быть прочитан осмысленно;
    * и прямо: loc_A715 = `call sub_AD66`, а sub_AD66 первой строкой зовёт sub_ADC9,
      который начинает с `ld hl, unk_5B39` и `ld b, 4` — B и HL мертвы.
    Локстеп (600 итераций, 1928 Б переменных против журнала ZX) это подтверждает.
    """
    old = ("game_delay:\n        ld hl, 0x300\n"
           "loc_A70E:\n        dec hl\n        ld a, l\n        or h\n"
           "        jr nz, loc_A70E\n        djnz game_delay\n")
    assert src.count(old) == 1, 'game_delay'
    return src.replace(old, "        ; A8: искусственная задержка оригинала снята (a8_no_delay)\n", 1)


_PACE_BLOCK = re.compile(r'(?m)^;__PACE_BEG__\n.*?^;__PACE_END__\n', re.S)


def a8_pace(src):
    """Потолок темпа (цель `vec`): итерация главного цикла не короче заданного времени.

    A8PACE — потолок в итерациях в секунду; по умолчанию 28.5 = МАКСИМУМ оригинала ZX по
    шести замеренным комнатам (замер build/zxpace.lua на стенде MAME: 19 → 25.2, 104 → 28.5,
    39 → 25.5, 56 → 13.4, 88 → 8.7, 48 → 7.7 итер/с). A8PACE=off — ограничителя нет вовсе:
    весь помеченный код и `call` снимаются, ROM байт в байт равен сборке без правки.

    Вариант А рецепта KL §19 (вариант Б — «длительность всегда целое число кадров» — там
    отвергнут числами: в тяжёлых комнатах он снимает до 7.5 % темпа и сглаженности не даёт).
    Возвращает (src, описание).
    """
    env = os.environ.get('A8PACE', '28.5').strip().lower()
    if env in ('off', 'no', 'none', '0', ''):
        src, n = _PACE_BLOCK.subn('', src)
        assert n == 4, 'блоков ограничителя темпа должно быть четыре, найдено %d' % n
        return src, 'выключен (A8PACE=off)'
    rate = float(env)
    FPS = 3000000.0 / 59904.0          # кадр Вектора = 59904 такта на 3 МГц -> 50.08 Гц
    period = FPS / rate
    pint = int(period)
    pfrc = int(round((period - pint) * 256))
    if pfrc == 256:
        pint, pfrc = pint + 1, 0
    assert 0 <= pint <= 255, 'потолок темпа вне диапазона'
    src = _PACE_BLOCK.sub(lambda m: m.group(0).replace(';__PACE_BEG__\n', '').replace(';__PACE_END__\n', ''), src)
    src = src.replace("vec_pace:\t\t",
                      "PACE_INT\t\tequ\t\t%d\t\t\t; потолок темпа: целых кадров на итерацию\n"
                      "PACE_FRC\t\tequ\t\t%d\t\t\t; и дробь, 1/256 кадра (%.1f итер/с)\n"
                      "vec_pace:\t\t" % (pint, pfrc, rate), 1)
    old = "onscreen_loop:\n"
    assert src.count(old) == 1, 'onscreen_loop'
    src = src.replace(old, old + "        call vec_pace   ; A8: потолок темпа (вариант А)\n", 1)
    eff = FPS / (pint + pfrc / 256.0)
    return src, '%d+%d/256 кадра = %.2f итер/с' % (pint, pfrc, eff)


_DIB_BLOCK = re.compile(r'(?m)^;__DIB_BEG__\n.*?^;__DIB_END__\n', re.S)
_CU_BLOCK = re.compile(r'(?m)^;__CU_BEG__\n.*?^;__CU_END__\n', re.S)
_EI_BLOCK = re.compile(r'(?m)^;__EI_BEG__\n.*?^;__EI_END__\n', re.S)
_DIB_N, _CU_N, _EI_N = 10, 6, 5   # догон/ei: +1 на vec_wipe0 (стирание плоскости 0)


def _unmark(rx, src, n_want, name):
    """Снять маркеры, оставив тело блока."""
    src, n = rx.subn(lambda m: m.group(0).split('\n', 1)[1].rsplit('\n', 2)[0] + '\n', src)
    assert n == n_want, 'блоков %s должно быть %d, найдено %d' % (name, n_want, n)
    return src


def _drop(rx, src, n_want, name):
    src, n = rx.subn('', src)
    assert n == n_want, 'блоков %s должно быть %d, найдено %d' % (name, n_want, n)
    return src


def a8_dibudget(src):
    """Цена отказа бюджета di (цель `vec`): что делать, когда блок не помещается до конца кадра.

    Кадровое прерывание Вектора НЕ защёлкивается, поэтому обратный ход, пришедшийся на di,
    теряется насовсем (см. §12 рецепта KL и reference_vector06c_interrupt_not_latched).

    A8_DIBUDGET=on   — прежний бюджет: перед каждым di-блоком `vec_di_budget` читает секундомер
                       ВИ53 и при нехватке остатка кадра уходит в `ei/halt`. ЦЕЛЫЙ кадр за
                       каждый отказ, фаза кадра залипает (журнал, заход 4.4).
    A8_DIBUDGET=off  — (по умолчанию) бюджета нет, блок идёт сразу; конец блока зовёт `vec_cu`,
                       который по секундомеру замечает потерянный кадр и выполняет тело ISR
                       руками (скан клавиатуры, ряды ZX, pace_el, перезарядка секундомера).
    A8_DIBUDGET=raw  — НЕГАТИВНЫЙ КОНТРОЛЬ для замера: ни бюджета, ни догона. Кадры реально
                       теряются, `pace_el` и скан клавиатуры отстают. В игру не годится.

    Блоки помечены в tools/a8_vec.py: __DIB__ — машинерия бюджета, __CU__ — догон,
    __EI__ — голый `ei` в хвосте di-блока (он нужен и `on`, и `raw`).
    Возвращает (src, описание).
    """
    env = os.environ.get('A8_DIBUDGET', 'off').strip().lower()
    if env in ('on', '1', 'yes', 'true'):
        src = _unmark(_DIB_BLOCK, src, _DIB_N, 'бюджета di')
        src = _drop(_CU_BLOCK, src, _CU_N, 'догона')
        src = _unmark(_EI_BLOCK, src, _EI_N, 'ei хвоста')
        return src, 'бюджет di + ei/halt (A8_DIBUDGET=on)'
    if env == 'raw':
        src = _drop(_DIB_BLOCK, src, _DIB_N, 'бюджета di')
        src = _drop(_CU_BLOCK, src, _CU_N, 'догона')
        src = _unmark(_EI_BLOCK, src, _EI_N, 'ei хвоста')
        return src, 'НЕТ НИЧЕГО: кадры теряются (A8_DIBUDGET=raw, только для замера)'
    assert env in ('off', '0', 'no', 'none', ''), 'A8_DIBUDGET: on|off|raw, дано %r' % env
    src = _drop(_DIB_BLOCK, src, _DIB_N, 'бюджета di')
    src = _unmark(_CU_BLOCK, src, _CU_N, 'догона')
    src = _drop(_EI_BLOCK, src, _EI_N, 'ei хвоста')
    return src, 'догоняющий ISR, ожидания нет (A8_DIBUDGET=off)'


def a8_logic_fixes(src):
    """Самомодифицирующийся код ЛОГИКИ -> переменные (три сайта, см. docs/PORT_RECIPE.md).

    Рендерные сайты (fill_window 0xBF95+1, print_sprite 0xD0BB+1/0xD10F+1) здесь не трогаем:
    в цели lockstep их тела заглушены целиком.
    """
    # 1) upd_42/43: смещения (ix+d) писались прямо в код (loc_B249+2 и loc_B25A+2)
    old = ("        ld a, h\n        ld (loc_B249+2), a\n"
           "        ld a, l\n        ld (loc_B25A+2), a\n")
    assert src.count(old) == 1, 'upd_42/43 self-mod'
    src = src.replace(old, "        ld (a8_blk_off), hl   ; A8: смещения (ix+d) в переменной\n", 1)
    for lbl, want in (("loc_B249", "ld a, (ix+1)"), ("loc_B25A", "ld (ix+9), a")):
        i = src.index(lbl + ":")
        j = src.index("\n", i) + 1
        line = src[j:src.index("\n", j)]
        assert want in line, (lbl, line)
        off = "a8_blk_off+1" if lbl == "loc_B249" else "a8_blk_off"
        if lbl == "loc_B249":       # чтение: A = (ix + смещение)
            new = ("        push hl\n        push de\n        ld hl, (z80_ix)\n"
                   f"        ld a, ({off})\n        ld e, a\n        ld d, 0\n        add hl, de\n"
                   "        ld a, (hl)\n        pop de\n        pop hl")
        else:                        # запись: (ix + смещение) = A
            new = ("        push hl\n        push de\n        push af\n        ld hl, (z80_ix)\n"
                   f"        ld a, ({off})\n        ld e, a\n        ld d, 0\n        add hl, de\n"
                   "        pop af\n        ld (hl), a\n        pop de\n        pop hl")
        src = src[:j] + new + src[j + len(line):]
    # 2) build_screen_objects: опкод `SET n,(HL)` собирался в байт byte_B87F за `DB 0xCB`
    old = ("        rlca\n        rlca\n        rlca\n        and 0x38   ; '8'\n"
           "        or 0xC6   ; 'Æ'             ; SET 0,(HL)\n"
           "        ld (byte_B87F), a   ; self_modifying code\n")
    assert src.count(old) == 1, 'SET n,(HL) self-mod'
    src = src.replace(old, "        and 7\n        ld (a8_visit_bit), a   ; A8: номер бита в переменной\n", 1)
    i = src.index("        DB 0xCB   ; Ë                    ; set n,(HL)\n")
    j = src.index("        ret\n", i)
    src = src[:i] + ("; A8: SET n,(HL) без самомодификации — маска сдвигом\n"
                     "        push bc\n        ld a, (a8_visit_bit)\n        ld b, a\n"
                     "        ld a, 1\n        inc b\n"
                     "a8_vb_m:\n        dec b\n        jp z, a8_vb_d\n        rlca\n        jp a8_vb_m\n"
                     "a8_vb_d:\n        or (hl)\n        ld (hl), a\n        pop bc\n") + src[j:]
    # 2а) sub_AD66: `xor a / .loop: or (hl) / inc hl / djnz .loop / jp z, game_over` —
    #     Z после цикла должен отражать НАКОПЛЕННЫЙ OR (все байты нулевые = игра окончена).
    #     У Z80 djnz флаги не трогает, на i8080 он разворачивается в `dec b / jp nz` и Z
    #     всегда равен 1 (выход по B==0) — игра уходила в GAME OVER на первой же итерации
    #     главного цикла. Пересчитываем Z по A: `and a` не меняет A и стоит 4 такта.
    old = ("        djnz loc_ADA8\n"
           "        jp z, game_over\n")
    assert src.count(old) == 1, 'sub_AD66 djnz/Z'
    src = src.replace(old,
        "        djnz loc_ADA8\n"
        "        and a   ; A8: djnz на i8080 портит Z — пересчитать по накопленному OR\n"
        "        jp z, game_over\n", 1)

    # 3) upd_103 («лишняя жизнь»): `is_on_or_near_obj` возвращает ответ в ПЕРЕНОСЕ, а между
    #    ним и `jr nc` стоят `dec (ix+4)`/`dec (ix+5)`. У Z80 `dec (ix+d)` перенос не трогает,
    #    а хелпер il_ix_dec считает адрес через `add a,l / adc a,0` и перенос выставляет —
    #    ответ терялся бы всегда (в Knight Lore ровно на этом лишняя жизнь не выдавалась
    #    НИКОГДА). Сохраняем флаги вокруг. A после pop af тот же, что и был: на Z80
    #    `dec (ix+d)` его не меняет; Z между push и jr никто не читает.
    old = ("        call is_on_or_near_obj\n"
           "        dec (ix+4)   ; plyr bottom width\n"
           "        dec (ix+5)   ; plyr bottom depth\n")
    assert src.count(old) == 1, 'upd_103 dec/CY'
    src = src.replace(old,
        "        call is_on_or_near_obj\n"
        "        push af   ; A8: хелпер (ix+d) портит перенос, а ответ процедуры — в нём\n"
        "        dec (ix+4)   ; plyr bottom width\n"
        "        dec (ix+5)   ; plyr bottom depth\n"
        "        pop af\n", 1)

    # 3) print_sprite: `ld a,(ix+25)` стоял ПОСЛЕ `ld sp,hl` (SP = данные спрайта). На i8080 это
    #    call IX-хелпера, который пишет адрес возврата в стек, то есть В СПРАЙТ. Читать до смены SP.
    src, n = re.subn(r'(        ld \(tmp_SP\), sp\n        ex de, hl\n        ld sp, hl\n        ex de, hl\n)'
                     r'(        ld a, \(ix\+25\)[^\n]*\n)', lambda m: m.group(2) + m.group(1), src, count=1)
    assert n == 1, 'print_sprite: порядок ld sp / (ix+25)'
    return src


def a8_seed_oracle(src):
    """done_sprite_updates: seed_3 += mem[seed_2] — байт памяти по адресу-счётчику.
    На ZX это переменные и код игры; после перекладки кода значения другие, поэтому
    в цели lockstep байт подаёт стенд (a8_rnd_feed, берётся из журнала ZX)."""
    old = ("        ld a, (seed_3)\n        add a, (hl)\n        add a, l\n        add a, h\n"
           "        ld (seed_3), a\n")
    assert src.count(old) == 1, 'seed_3 mem-mix'
    return src.replace(old,
        "        ld a, (seed_3)\n        push hl\n        ld hl, a8_rnd_feed   ; A8(lockstep): mem[seed_2] подаёт стенд\n"
        "        add a, (hl)\n        pop hl\n        add a, l\n        add a, h\n        ld (seed_3), a\n", 1)


# Горячие процедуры цели `vec`: обращения (ix+d)/(iy+d) в них разворачиваются НА МЕСТЕ, а не
# через компактный хелпер. Замер (tools/profile_vec.js, 100 итераций покоя): хелпер стоит
# 265 тактов на обращение и съедает 58 % всех тактов; развёртка — около 60. Список — по профилю,
# сверху вниз по «тактов/итер * доля хелперов». A8_IX_HOT=0 выключает (для сверки).
A8_VEC_INLINE = {
    'update_sprite_loop', 'calc_display_order_and_render', 'set_draw_objs_overlapped',
    'list_objects_to_draw', 'jump_to_upd_object',
    'print_sprite',
    'sub_C099', 'flip_sprite', 'sub_C082', 'upd_10_to_17', 'add_dXYZ',
    'calc_2d_info', 'upd_20_to_2B', 'get_ptr_object',
    # Второй заход (после ручной переписи четырёх циклов): процедуры, у которых больше 70 %
    # собственных тактов уходило в компактные хелперы. Порог — ЗАМЕР «тактов на байт»
    # (цена каждой мерялась отдельной сборкой, выигрыш = половина её хелперных тактов):
    #   vflip_sprite_data 34, upd_03 26, adj_dZ_for_out_of_bounds 14, sub_C2BC 6.4,
    #   set_wipe_and_draw_flags 6.4, adj_for_out_of_bounds 6.3, dZ_ok 6.2, clear_dX_dY 5.6,
    #   handle_forward 5.2, chk_plyr_OOB 5.2, move_player 5.2.
    # Ниже порога 5 и потому НЕ взяты: handle_exit_screen 4.2 (61 Б),
    # next_fg_obj_sprite 3.0 (221 Б — вдобавок процедура холодная, работает при входе в комнату).
    'vflip_sprite_data', 'adj_for_out_of_bounds', 'dZ_ok',
    'adj_dZ_for_out_of_bounds', 'sub_C2BC', 'upd_03', 'handle_forward', 'chk_plyr_OOB',
    'move_player', 'set_wipe_and_draw_flags', 'clear_dX_dY',
}


def a8_vec_glue(src):
    """Цель `vec`: Вектор-06Ц, ч/б, нативный столбцовый буфер (см. tools/a8_vec.py)."""
    import a8_vec
    hot = os.environ.get('A8_IX_HOT')
    if hot is None or hot == '1':
        _IX_INLINE_FUNCS.update(A8_VEC_INLINE)
    elif hot not in ('', '0'):
        _IX_INLINE_FUNCS.update(x for x in hot.split(',') if x)
    src = a8_cut_attrs(src)            # атрибутная память ZX — долой (§17.3 рецепта KL)
    src = a8_vec.glue(src)
    src = a8_logic_fixes(src)          # три сайта самомодификации логики + djnz/Z + перенос (ix+25)
    src = a8_vec.hooks(src)            # палитра комнаты и меню
    src = a8_vec.glue_i8080(src)       # print_sprite: счётчик строк, вход в цепочку, бюджет di
    src = src.replace("        DEVICE ZXSPECTRUM48\n",
                      "        DEVICE ZXSPECTRUM48\n" + a8_vec.header() + _LDIR_HELPERS + "\n", 1)
    src = re.sub(r'^\s*SAVEBIN[^\n]*$', a8_vec.tail().replace("\\", "\\\\") +
                 '\n        SAVEBIN "build/alien8_vec.r0m", 0, 0x10000', src, count=1, flags=re.M)
    return src


def a8_joy_anykey(src):
    """«Любая клавиша» в play_audio_until_keypress обязана слышать и джойстик (только цель vec).

    Правится не текст драйвера звука (tools/a8_sound_ay.py не трогаем — там чужая ветка), а уже
    склеенный исходник, ПОСЛЕ a8_sound_ay.apply: два места `xor a : call read_key` внутри
    play_audio_until_keypress заменяются на `call a8_anykey` (он же читает ещё и vec_joyraw).

    Зачем: мелодия меню играет десятки секунд, и всё это время menu_loop висит внутри
    play_audio_until_keypress. Клавиша '1'/'2'/'3' работает только потому, что ЛЮБАЯ клавиша рвёт
    мелодию; кнопка джойстика — потому что vec_joy прижимает ей '0' в рядах ZX. А направления в
    ряды не сведены намеренно (в ряду 0 матрицы Вектора со стрелками лежит ВК = пауза), и без этой
    правки отклонение стика в меню не делало бы РОВНО НИЧЕГО, пока мелодия не доиграет.
    """
    body = re.search(r'play_audio_until_keypress:\n.*?; End of function play_audio_until_keypress\n',
                     src, flags=re.S)
    assert body, 'a8_joy_anykey: play_audio_until_keypress не найдена'
    new, n = re.subn(r'[ \t]*xor a\n[ \t]*call read_key\n', '        call a8_anykey\n', body.group(0))
    assert n == 2, 'a8_joy_anykey: мест «любой клавиши» %d, ждали 2' % n
    return src[:body.start()] + new + src[body.end():]


def a8_glue(src, target):
    # меню и вырезание вариантов ввода ZX — ОБЕИМ целям (иначе локстеп судил бы чужое меню);
    # ввод через матрицу Вектора и пауза на ВК — только vec
    src = a8_cut_controls(src, vec=(target == 'vec'))
    # Звук: весь ZX-путь (бипер) -> драйвер MSX на AY. ОБЕИМ целям, чтобы локстеп доказывал,
    # что драйвер не трогает 1928 Б состояния игры (см. PORT_RECIPE «этап 5, заход 3: звук»).
    # Идёт ПОСЛЕ склейки: a8_vec.glue переносит адреса, записанные числом, и снимает
    # out (0xFE) по ИСХОДНОМУ тексту ZX-пути, который звук вырезает целиком.
    if target == 'vec':
        return a8_joy_anykey(a8_sound_ay.apply(a8_vec_glue(src))[0])
    assert target == 'lockstep', target
    # Развёртка (ix+d) в горячих процедурах здесь ВЫКЛЮЧЕНА по умолчанию (темп на этой цели
    # не меряем), но `A8_IX_HOT=1` включает ТОТ ЖЕ список, что у цели vec: иначе гейт локстепа
    # вакуумный — он проверяет код с компактными хелперами, а в игру идёт код с развёрткой,
    # где флаги вокруг обращения сохраняются другим способом (журнал, этап 5).
    hot = os.environ.get('A8_IX_HOT')
    if hot == '1':
        _IX_INLINE_FUNCS.update(A8_VEC_INLINE)
    elif hot:
        _IX_INLINE_FUNCS.update(x for x in hot.split(',') if x)
    src = src.replace("        DEVICE ZXSPECTRUM48\n",
                      "        DEVICE ZXSPECTRUM48\n" + (A8_HEADER % A8_STACK) + _LDIR_HELPERS + "\n", 1)
    src = a8_logic_fixes(src)
    src = a8_seed_oracle(src)
    # клавиатура: вместо ULA — виртуальная матрица
    src, n = re.subn(r'read_key:\n.*?; End of function read_key', A8_READ_KEY, src, count=1, flags=re.S)
    assert n == 1, 'read_key'
    # ---- раскладка ----
    def org(old_org, label, new):
        nonlocal src
        pat = '        ORG %s\n%s:' % (old_org, label)
        assert src.count(pat) == 1, pat
        src = src.replace(pat, '        ORG %#06x\n%s:' % (new, label), 1)
    org('0x4000', 'zxvram', A8_ZXVRAM)
    org('0x5800', 'zxaram', A8_ZXARAM)
    org('0x5B00', 'seed_1', A8_VARS)
    # конец блока переменных = бывший адрес font; он служит ограничителем «конец таблицы
    # объектов» (2 сайта). После переноса кода на 0x0100 font ниже таблицы -> своя метка.
    old = "        ORG 0x6288\nfont:"
    assert src.count(old) == 1
    src = src.replace(old, "a8_vars_end:\n        ORG 0x0100   ; код и данные игры\nfont:", 1)
    n_end = src.count("ld bc, font") + src.count("ld hl, font\n")
    assert n_end == 2, n_end
    src = src.replace("ld bc, font", "ld bc, a8_vars_end")
    src = src.replace("ld hl, font\n", "ld hl, a8_vars_end\n")
    src = a8_native_logic.presub(src)
    # ---- КОД, ЛЕЖАЩИЙ В ДАННЫХ ----
    # Пролог calc_display_order_and_render (8 байт) спрятан в ХВОСТЕ буфера
    # objects_to_draw и вызывается как `call objects_to_draw+0x40`; tcdev разобрал
    # его как данные. На i8080 эти байты (DD E5 / FD E5 = push ix / push iy) —
    # не инструкции вовсе, поэтому пролог надо вернуть в код. Буфер остаётся
    # 64 байта: список объектов не длиннее 41 (40 объектов + маркер 0xFF).
    old = "        DB 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0xAF, 0x32, 0x1E, 0x5B, 0xDD, 0xE5, 0xFD, 0xE5\n"
    assert src.count(old) == 1, 'пролог в objects_to_draw'
    src = src.replace(old,
        "        DB 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        "a8_cdo_prolog:   ; A8: пролог calc_display_order_and_render лежал в буфере как данные\n"
        "        xor a\n        ld (rendered_objs_cnt), a\n        push ix\n        push iy\n", 1)
    n_c = src.count("call objects_to_draw+0x40")
    assert n_c == 1, n_c
    src = src.replace("call objects_to_draw+0x40", "call a8_cdo_prolog", 1)

    # ---- АДРЕСА, ЗАПИСАННЫЕ ЧИСЛОМ (а не меткой) ----
    # Оригинал кое-где адресует память числовой константой. После переноса переменных
    # на 0xc000 и кода на 0x0100 такая константа указывает в чужое место: `ld hl,0x5C08`
    # в find_special_objs_here — это ограничитель конца таблицы спецобъектов, и
    # zero_DE заливал нулями всё от DE до 0x5C08, то есть ПРЯМО ПО НАШЕМУ КОДУ
    # (симптом: через ~20 кадров после входа в комнату PC уходит в середину
    # инструкции loc_AEF7+1). Замены обязаны быть символическими.
    # Отдельно — таблица направлений робомыши. Она лежит СРАЗУ ЗА телом sub_B0E7, и оригинал
    # адресует её числом 0xB108 = sub_B0E7 + 0x21, где 0x21 — ДЛИНА ТЕЛА НА Z80. После
    # рекомпиляции тело длиннее (три обращения (ix+d) стали `call+db` — 4 байта вместо 3),
    # и «метка + смещение» показывала бы в ХВОСТ СОБСТВЕННОГО КОДА процедуры: мышь получала
    # нулевое направление и стояла на месте (журнал, «Дефект владельца 2026-09-15»).
    # Поэтому у таблицы своя метка, а смещения нет вовсе.
    old = "        DB 0xFF, 0, 1, 0, 0, 1, 0, 0xFF\n"
    assert src.count(old) == 1, 'таблица направлений робомыши'
    src = src.replace(old, "a8_mouse_dirs:   ; таблица направлений sub_B0E7 (была 0xB108 = sub_B0E7+0x21)\n"
                      + old, 1)
    for num, sym, cnt in (('0x5C08', 'other_objs_here', 2),   # конец таблицы спецобъектов
                          ('0x5B36', 'unk_5B36', 1),
                          ('0x5B3A', 'unk_5B3A', 2),
                          ('0x5B40', 'unk_5B40', 1),
                          ('0x5B41', 'byte_5B41', 1),
                          ('0x7827', 'sprite_tbl', 1),
                          ('0xB6AD', 'byte_B6A9+4', 1),       # таблица параметров звука
                          ('0xB108', 'a8_mouse_dirs', 1)):    # направления робомыши, см. выше
        pat = re.compile(r'(?m)^(        ld (?:hl|de|bc|iy|ix), )' + num + r'\b')
        src, n = pat.subn(lambda m: m.group(1) + sym, src)
        assert n == cnt, (num, n, cnt)

    # буфер и таблицы
    src = src.replace("        ORG 0xD200\nvidbuf:",
                      "        ASSERT $ <= %#06x   ; код не должен дорасти до стека\n"
                      "        ORG %#06x\nvidbuf:" % (A8_STACK - 0x400, A8_VIDBUF), 1)
    # build_lookup_tbls строит таблицы по абсолютным адресам 0xF100/0xF200 (print_sprite
    # адресует страницу константой `or 0xF0`). В lockstep рендер заглушен, читателей нет:
    # reverse_bits_table кладём в свободное место, таблицу сдвига накладываем на zx_vram.
    src += ("\n        ORG %#06x\nreverse_bits_table:\n        DS 0x100\n"
            "shift_bits_table: equ %#06x   ; alias zxvram (в lockstep читателей нет)\n" % (A8_REVTAB, A8_ZXVRAM))
    # стек: в оригинале `ld sp, 0xF100` (главный он же временный в update_sprite_loop)
    n_sp = src.count("ld sp, 0xF100")
    assert n_sp == 1, n_sp
    src = src.replace("ld sp, 0xF100", "ld sp, %#06x" % A8_STACK)
    # seed_1 при старте оригинал берёт из байта области переменных ДО её очистки
    # (`ld a,(other_objs_here+0x70)`) — адрес валиден и в нашей раскладке, не трогаем:
    # стенд всё равно прибивает сиды в точке синхронизации.
    # ---- вывод заглушен ----
    # пиксельный цикл print_sprite: всё после сохранения SP — самомодифицируемые цепочки
    src, n = re.subn(r'^        ld \(tmp_SP\), sp[^\n]*$',
                     "        ret   ; ЗАГЛУШКА(lockstep): пиксельный цикл print_sprite отключён",
                     src, count=1, flags=re.M)
    assert n == 1, 'заглушка print_sprite'
    for lbl in ('blit_to_screen', 'fill_window', 'update_screen'):
        src = _stub_after_label(src, lbl, 'lockstep: самомод. цикл, пишет только в буфер/экран')
    src = re.sub(r'^\s*SAVEBIN[^\n]*$',
                 '        SAVEBIN "build/alien8_8080.r0m", 0, 0x10000', src, flags=re.M)
    return a8_sound_ay.apply(src)[0]


def main():
    argv = sys.argv[1:]
    target = 'lockstep'
    pos = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--target':
            target = argv[i + 1]; i += 2; continue
        if a.startswith('--target='):
            target = a.split('=', 1)[1]; i += 1; continue
        pos.append(a); i += 1
    inp, outp = pos[0], pos[1]
    src = open(inp, encoding='utf-8').read()
    src = a8_no_delay(src)             # обе цели: состояние не меняется, локстеп это судит
    src = a8_glue(src, target)
    pace_desc = None
    dib_desc = None
    if target == 'vec':
        src, pace_desc = a8_pace(src)  # потолок темпа: только цель vec (нужен ISR Вектора)
        src, dib_desc = a8_dibudget(src)   # цена отказа бюджета di: ожидание или догоняющий ISR
    src = a8_native_flip.presub(src)   # ветка flipcache: разворот спрайтов (обе цели)
    src, exx_pairs = _classify_exx(src)
    src = translate(src)
    src = a8_native_logic.apply(src)
    src = a8_native_flip.apply(src)
    src = a8_sound_ay.emit(src, target)  # ядро драйвера звука — уже в i8080, транслировать нельзя
    helpers = ix_helpers_text()
    if target == 'vec':
        # хелперы — ПОСЛЕ цепочек print_sprite: цепочки обязаны начинаться на границе страницы
        assert src.count('__A8_HELPERS__') == 1, 'место для IX-хелперов'
        src = src.replace('__A8_HELPERS__', helpers, 1)
    elif helpers:
        src, n = re.subn(r'(^        ORG 0x[0-9A-Fa-f]+\nvidbuf:)', lambda m: helpers + m.group(1),
                         src, count=1, flags=re.M)
        assert n == 1, 'место для IX-хелперов'
    # СТОРОЖ против целого класса дефектов: команда, которую транслятор не разобрал, не имеет
    # права уехать в КОММЕНТАРИЙ — она просто не попадёт в образ, и ни один гейт этого
    # не увидит (так шесть `sla`/`srl` по (ix+d) молча пропали, см. журнал 2026-09-15).
    # Сами ветки транслятора теперь падают ассертом; это — последняя проверка по тексту.
    assert 'UNHANDLED' not in src, 'транслятор уронил команду в комментарий:\n  ' + \
        '\n  '.join(l.strip() for l in src.split('\n') if 'UNHANDLED' in l)
    hole_desc = hud_desc = None
    if target == 'vec':
        # ПОСЛЕДНИМ шагом: текст уже окончательный (трансляция, нативные процедуры, звук,
        # IX-хелперы), поэтому длины считаются по тому же тексту, что уйдёт в ассемблер.
        src, hmoved, hblk, hole_desc = a8_pack_holes(src, A8_HOLES, A8_HOLE_BYTES, A8_HOLE_SKIP)
        if os.environ.get('A8_HUD_LAYOUT', 'on') != 'off':
            src, hud_desc = a8_layout_upper(src, A8_HUD_WINDOWS)
    open(outp, 'w', encoding='utf-8').write(src)
    print(f'{inp} -> {outp} (цель {target}); IX-хелперов {len(_ix_used)}; exx-пар {exx_pairs}'
          + (f'; ограничитель темпа: {pace_desc}' if pace_desc else '')
          + (f'; di-блоки: {dib_desc}' if dib_desc else '')
          + (f'; дыры вне картинки: {hole_desc}' if hole_desc else '')
          + (f'; верхний регион мимо полосы HUD: {hud_desc}' if hud_desc else ''))


if __name__ == '__main__':
    main()
