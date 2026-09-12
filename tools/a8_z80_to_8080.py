#!/usr/bin/env python3
"""a8_z80_to_8080.py — рекомпиляция Alien 8 (Z80 -> i8080) на уровне исходника, синтаксис sjasmplus.

Ядро (split_line/expand/_ixiy/_exx/_classify_exx/_bit/_resset/_shift/_ldir/_adcsbc_hl/translate)
взято ДОСЛОВНО из knightlore-v06c/tools/kl_z80_to_8080.py (оно же из kvalley-v06c) — оно общее
для всех трёх портов. Специфика Alien 8 — только в склейке (a8_*).

    python3 tools/a8_z80_to_8080.py <in.asm> <out.asm> [--target lockstep]
"""
import sys, re, os
import a8_native_logic
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
    if mn in ('sla', 'sra', 'srl', 'sll', 'rl', 'rr', 'rlc', 'rrc'):
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
    return [f"; UNHANDLED SHIFT {op}"]


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
        return [f"; UNHANDLED IX/IY {full}"]
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
    return [f"; UNHANDLED IX/IY {full}"]


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
    if mn in ('inc', 'dec', 'bit', 'res', 'set', 'add', 'adc', 'sub', 'sbc', 'and', 'xor', 'or', 'cp'):
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
    'print_sprite', 'wipe_next_object',
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
    src = a8_vec.glue(src)
    src = a8_logic_fixes(src)          # три сайта самомодификации логики + djnz/Z + перенос (ix+25)
    src = a8_vec.hooks(src)            # палитра комнаты и меню
    src = a8_vec.glue_i8080(src)       # print_sprite: счётчик строк, вход в цепочку, бюджет di
    src = src.replace("        DEVICE ZXSPECTRUM48\n",
                      "        DEVICE ZXSPECTRUM48\n" + a8_vec.header() + _LDIR_HELPERS + "\n", 1)
    src = re.sub(r'^\s*SAVEBIN[^\n]*$', a8_vec.tail().replace("\\", "\\\\") +
                 '\n        SAVEBIN "build/alien8_vec.r0m", 0, 0x10000', src, count=1, flags=re.M)
    return src


def a8_glue(src, target):
    if target == 'vec':
        return a8_vec_glue(src)
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
    for num, sym, cnt in (('0x5C08', 'other_objs_here', 2),   # конец таблицы спецобъектов
                          ('0x5B36', 'unk_5B36', 1),
                          ('0x5B3A', 'unk_5B3A', 2),
                          ('0x5B40', 'unk_5B40', 1),
                          ('0x5B41', 'byte_5B41', 1),
                          ('0x7827', 'sprite_tbl', 1),
                          ('0xB6AD', 'byte_B6A9+4', 1),       # таблица параметров звука
                          ('0xB108', 'sub_B0E7+0x21', 1)):    # таблица дельт upd_74_to_77
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
    return src


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
    src = a8_glue(src, target)
    src, exx_pairs = _classify_exx(src)
    src = translate(src)
    src = a8_native_logic.apply(src)
    helpers = ix_helpers_text()
    if target == 'vec':
        # хелперы — ПОСЛЕ цепочек print_sprite: цепочки обязаны начинаться на границе страницы
        assert src.count('__A8_HELPERS__') == 1, 'место для IX-хелперов'
        src = src.replace('__A8_HELPERS__', helpers, 1)
    elif helpers:
        src, n = re.subn(r'(^        ORG 0x[0-9A-Fa-f]+\nvidbuf:)', lambda m: helpers + m.group(1),
                         src, count=1, flags=re.M)
        assert n == 1, 'место для IX-хелперов'
    open(outp, 'w', encoding='utf-8').write(src)
    print(f'{inp} -> {outp} (цель {target}); IX-хелперов {len(_ix_used)}; exx-пар {exx_pairs}')


if __name__ == '__main__':
    main()
