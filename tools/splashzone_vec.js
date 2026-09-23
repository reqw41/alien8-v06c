#!/usr/bin/env node
// ГЕЙТ «ЗОНА 3 ЗАСТАВКИ НЕ ПИШЕТСЯ ЧУЖИМИ» (релиз, A8_SPLASH=1).
//
//   node tools/splashzone_vec.js build/alien8_release.r0m build/alien8_release.sld
//   A8SZ_KEYF=<кадр клавиши «0»> (по умолчанию 8600: мелодия целиком, 8427 кадров, + петля)
//
// ЧТО СТЕРЕЖЁТ. В релизе код заставки (a8_splash_cont, a8_tune_off) лежит в зоне 3 —
// 0x7E00..0x7F87, это переменные игры seed_1..+0x788, их чистит START (коммит 194f298).
// До jp START там ЖИВОЙ КОД: запись туда кем угодно, кроме самой заставки, портит её на ходу.
// Разрешённые писатели по решению владельца: сама заставка (зоны 1..3: a8_sp_isr,
// a8_tune_init/tick, a8_splash_cont..a8_tune_off), прерывание (вход RST 38h -> возврат по
// тому же SP: vec_isr, клавиатура, джойстик, палитра) и плеер мелодии (метки msx_tv*).
//
// СЦЕНАРИЙ. Сброс (PC = 0, загрузчик), кадры по 59 904 такта с прерыванием, клавиша «0» на
// кадре KEYF (6 кадров), прогон до первого PC == START (не позже KEYF + 400 кадров).
// Писатель — PC НАЧАЛА команды (не PC после выборки); вход в прерывание — отдельный класс.
//
// КРИТЕРИЙ (код 1): START не достигнут; записей в зону 3 от «чужих» > 0; или КОНТРОЛЬ ХУКА —
// записей в ячейки плеера msx_tv_stub..msx_tv_v1+15 (по меткам) за заставку 0: тогда тап слеп
// или плеер не играл, и «0 чужих» ничего не доказывает. Разрешённые записи в зону 3 печатаются
// по писателям (их сейчас тоже 0 — заставка свой код не пишет).
"use strict";
const fs = require("fs"), vm = require("vm");
const base = "/Users/boris/projects/vector06js";
const [ROM, SLD] = process.argv.slice(2);
if (!ROM || !SLD) { console.log("нужно: <rom> <sld>"); process.exit(2); }
const KEYF = +(process.env.A8SZ_KEYF || 8600);
const Z0 = 0x7E00, Z1 = 0x7F87;
const L = {};
for (const l of fs.readFileSync(SLD, "latin1").split("\n")) {
  const p = l.split("|");
  if (p.length >= 8 && p[6] === "L") { const n = p[7].split(",")[1]; if (n && !(n in L)) L[n] = +p[5]; }
}
for (const t of ["msx_tv_stub", "msx_tv_v1", "START", "a8_splash_cont", "a8_tune_off", "a8_sp_isr", "a8_tune_init", "a8_tune_tick", "a8_sp_v"])
  if (L[t] === undefined) { console.log("нет метки " + t + " — образ не релизный (A8_SPLASH=1)?"); process.exit(2); }
if (L.a8_sp_v !== Z0) { console.log(`зона 3 начинается с 0x${L.a8_sp_v.toString(16)}, гейт ждёт 0x7e00`); process.exit(2); }

// концы блоков кода заставки — по листингу: последняя строка с байтами перед следующим ORG/концом
const lst = fs.readFileSync(ROM.replace(/\.r0m$/, ".lst"), "latin1").split("\n");
function blockEnd(start) {             // адрес за последним байтом непрерывного блока с start
  let end = start, on = false;
  for (const l of lst) {
    const m = l.match(/^\s*\d+\+?\s+([0-9A-F]{4})\s((?:[0-9A-F]{2}\s)+)/);
    if (!m) continue;
    const a = parseInt(m[1], 16), n = m[2].trim().split(/\s+/).length;
    if (a === start) on = true;
    if (!on) continue;
    if (a !== end && a !== start) break;
    end = a + n;
  }
  return end;
}
const SPL = [[L.a8_sp_isr, blockEnd(L.a8_sp_isr)], [L.a8_tune_init, 0x10000], [L.a8_splash_cont, blockEnd(L.a8_splash_cont)]];
const inSplash = pc => SPL.some(([a, b]) => pc >= a && pc < b);
const labs = Object.entries(L).sort((a, b) => a[1] - b[1]);
function nm(pc) { let b = null; for (const [n, a] of labs) { if (a <= pc) b = [n, a]; else break; } return b ? `${b[0]}+${pc - b[1]}` : "?"; }
function encl(pc) { let b = null; for (const [n, a] of labs) { if (a <= pc) b = n; else break; } return b || ""; }

const g = {}; g.window = g;
function fcx() { return { createImageData: () => ({ data: new Uint8ClampedArray(4) }), putImageData: () => {}, getImageData: () => ({ data: new Uint8ClampedArray(4) }), fillRect() {}, drawImage() {} }; }
function fc() { return { width: 0, height: 0, style: {}, getContext: () => fcx() }; }
g.document = { createElement: () => fc(), getElementById: () => fc() };
g.requestAnimationFrame = () => 0; g.setTimeout = () => 0; g.print = () => 0;
g.console = { log() {}, debug() {}, warn() {}, error() {}, info() {} };
const ctx = vm.createContext(g);
for (const f of ["i8080-js/i8080_trace.js", "i8080-js/i8080_disasm.js", "i8080-js/i8080.js", "src/fili.js", "src/ay.js",
                 "src/fd1793.js", "src/fddimage.js", "src/i8253.js", "src/io.js", "src/keyboard.js", "src/memory.js",
                 "src/sound.js", "src/tv.js"])
  vm.runInContext(fs.readFileSync(base + "/" + f, "utf8"), ctx, { filename: f });
const memory = new ctx.Memory(), keyboard = new ctx.Keyboard(), timer = new ctx.I8253(), ay = new ctx.AY(),
      floppy = new (ctx.Floppy().FD1793)(), io = new ctx.IO(keyboard, timer, memory, ay, floppy);
{ const _rd = io.input.bind(io); io.input = p => ((p & 0xFF) === 0x0E ? 0xFF : _rd(p)); }
const cpu = new ctx.I8080(memory, io), tape = { advance: () => {}, sample: 0, reset: () => {} },
      v06c = new ctx.Vector06c(cpu, memory, io, ay, tape);
v06c.bmp = new Uint32Array(576 * 288); v06c.displayFrame = () => {}; v06c.check_breakpoint = () => false; v06c.dbg = null;
const IMG = new Uint8Array(fs.readFileSync(ROM)).subarray(0, 0x10000);
if (IMG[0] !== 0xF3 || IMG[1] !== 0x31) throw new Error("загрузчик не `di / ld sp,imm` — база стека не читается");
const SPBASE = IMG[2] | (IMG[3] << 8);
memory.init_from_array(IMG, 0);
memory.detach_boot && memory.detach_boot();
cpu.pc = 0; cpu.sp = SPBASE; cpu.iff = false;

// ---- тап записей ----
let ipc = 0, isr = [];                 // isr: стек {ret, sp} незакрытых входов в прерывание
const W = new Map();                   // писатель -> {cls, n}
let nForeign = 0, nAllowed = 0, nState = 0;
const ST0 = L.msx_tv_stub, ST1 = L.msx_tv_v1 + 16;   // ячейки плеера — контроль хука
const ow = memory.write.bind(memory);
memory.write = function (a, w, s) {
  a &= 0xffff;
  if (a >= ST0 && a < ST1) nState++;
  if (a >= Z0 && a <= Z1) {
    let cls;
    if (ipc === -1) cls = "вход прерывания";
    else if (isr.length) cls = "прерывание";
    else if (inSplash(ipc)) cls = "заставка";
    else if (encl(ipc).startsWith("msx_tv")) cls = "плеер";
    else cls = "ЧУЖОЙ";
    if (cls === "ЧУЖОЙ") nForeign++; else nAllowed++;
    const k = ipc === -1 ? "irq" : ipc.toString(16);
    const e = W.get(k) || { cls, n: 0, where: ipc === -1 ? "RST 38h" : nm(ipc), a0: a };
    e.n++; W.set(k, e);
  }
  return ow(a, w, s);
};
let frc = 0, tacc = 0, frame = 0, started = -1;
while (frame < KEYF + 400) {
  if (frame === KEYF) keyboard.matrix[2] |= 0x01;          // «0»
  if (frame === KEYF + 6) keyboard.matrix[2] &= ~0x01;
  if (cpu.pc === L.START) { started = frame; break; }
  while (isr.length && cpu.pc === isr[isr.length - 1].ret && cpu.sp === isr[isr.length - 1].sp + 2) isr.pop();
  ipc = cpu.pc;
  const c = (cpu.instruction(), cpu.vcycles);
  frc += c; tacc += c;
  if (tacc > 1) { const tn = tacc >> 1; tacc -= tn * 2; timer.Count(tn); }
  if (cpu.last_opcode === 0xd3) io.commit();
  if (frc >= 59904) {
    frc -= 59904; frame++;
    const was = cpu.iff, ret = cpu.pc;
    ipc = -1;
    v06c.irq = true; v06c.checkInterrupt();
    if (was && cpu.pc !== ret) isr.push({ ret, sp: cpu.sp });
  }
}
let bad = 0;
console.log(`заставка: клавиша на кадре ${KEYF}, START на кадре ${started}; блоки кода заставки: ` +
            SPL.map(([a, b]) => `${a.toString(16)}..${(b - 1).toString(16)}`).join(", "));
console.log(`записей в зону 3 0x7E00..0x7F87 до START: чужих ${nForeign}, разрешённых ${nAllowed}; ` +
            `контроль хука: записей в ячейки плеера 0x${ST0.toString(16)}..0x${(ST1 - 1).toString(16)} ${nState}`);
for (const [k, e] of W) console.log(`  писатель ${k} (${e.where}) — ${e.cls}: ${e.n} записей, первая в 0x${e.a0.toString(16)}`);
if (started < 0) { console.log(`START не достигнут за ${KEYF + 400} кадров`); bad++; }
if (nState === 0) { console.log("КОНТРОЛЬ ХУКА: ни одной записи в ячейки плеера — тап слеп или мелодия не играла"); bad++; }
if (nForeign) { console.log(`ЧУЖИЕ ЗАПИСИ В ЗОНУ 3 ЗАСТАВКИ: ${nForeign}`); bad++; }
console.log(bad ? `ГЕЙТ ЗОНЫ ЗАСТАВКИ КРАСНЫЙ: нарушений ${bad}` : "гейт зоны заставки зелёный");
process.exit(bad ? 1 : 0);
