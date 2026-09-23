#!/usr/bin/env node
// ГЕЙТ «ПЕРЕКРАСКА» (loc_AFF8 -> loc_B005): мигание комнаты с лесенкой audio_msx_ladder
// обязано КОНЧИТЬСЯ и ЗВУЧАТЬ на ВИ53.
//
//   node tools/recolourcheck_vec.js build/alien8_vec.r0m build/alien8_vec.sld
//
// ЧТО ЭТО ЗА ПУТЬ. loc_AFF8 — хвост upd_60_to_63 (вентиль криокамеры встал точно на своё
// гнездо: «собран кусок головоломки», см. palseq_vec.js). Оригинал ZX: (ix+0) |= 4, 16 раз
// «пробег по атрибутам 768 Б + звук sub_B5EE + пауза 0x200» (счётчик — D), потом
// curr_room_attrib := 7, colour_something, unk_5B40 += 1 (BCD), при 0x24 — конец игры.
// У ZX sub_B5EE регистр D НЕ ТРОГАЛ; у нас на месте sub_B5EE стоит лесенка MSX 0x50F5.
// Это НЕ гибель героя: гибель идёт мимо loc_B005 (сценарии гибели в zxpix/nobjcheck/hudfilm
// зелёные и лесенку не зовут).
//
// СЦЕНАРИЙ. Сценарии стенда этот путь не достают (вентиль надо донести до гнезда), поэтому
// вход — подменой PC, в контексте, в котором путь и живёт: игра доводится до комнаты
// (клавиша «0», как в остальных гейтах), крутится WARM итераций, и на входе в msx_frame_off
// (call из loc_A72E — точка конца игровой итерации, в стеке адрес возврата в главный цикл)
// PC ставится на loc_AFF8. Хвост пути (loc_B04C: sub_A7A3 / jp sub_BF2F) кончается `ret`
// — возврат в главный цикл по тому же адресу. z80_ix при этом — последний объект цикла
// (его (ix+0) |= 4 — побочный эффект сценария, на критерий не влияет).
//
// КРИТЕРИЙ (любое нарушение = код 1):
//   1) перекраска кончилась: PC вернулся по адресу возврата со снятым SP не позже MAXF кадров
//      после подмены. ПОРОГ: счёт тактов пути — 16 x (0x300 + 0x200 итераций пустого цикла по
//      24 такта + лесенка 8 x (0x400 x 24 + ~3 000 на установку и слив)) ~ 4.0 М тактов =
//      ~67 кадров по 59 904 такта; замер на исправленной сборке — в выводе. MAXF = 150
//      (запас > 2x на прерывания и рост слива, но на порядок меньше «зависания»).
//   2) лесенку позвали РОВНО 16 раз (D — счётчик вызывающего; при порче D не 16);
//   3) за каждый вызов лесенки на счётчики 1/2 ВИ53 (порты 0x0A/0x09) загружены делители
//      всех семи слышимых ступеней: 13.5 x P для P = (B-1)*16, B = 8..2 (1512 1296 1080 864
//      648 432 216); ступень B = 1 даёт P = 0 -> делитель < 64 -> тишина; к выходу из лесенки
//      счётчик, на котором она звучала, остановлен (управляющее слово без делителя);
//   4) секундомер (счётчик 0) лесенка не трогает — правило tunecheck_vec.js: 0x0B только в
//      кадре с защёлкой vec_cu, слова счётчика 0 на 0x08 — только 0x30/0x00;
//   5) игра идёт дальше: после возврата ещё POST итераций (входов в msx_frame_off) не позже
//      POSTF кадров.
"use strict";
const fs = require("fs"), vm = require("vm");
const base = "/Users/boris/projects/vector06js";
const [ROM, SLD] = process.argv.slice(2);
if (!ROM || !SLD) { console.log("нужно: <rom> <sld>"); process.exit(2); }
const WARM = +(process.env.A8RC_WARM || 20), MAXF = +(process.env.A8RC_MAXF || 150);
const POST = 10, POSTF = 400;
const L = {};
for (const l of fs.readFileSync(SLD, "latin1").split("\n")) {
  const p = l.split("|");
  if (p.length >= 8 && p[6] === "L") { const n = p[7].split(",")[1]; if (n && !(n in L)) L[n] = +p[5]; }
}
for (const t of ["audio_msx_ladder", "loc_AFF8", "msx_frame_off", "loc_A72E", "unk_5B40", "curr_room_attrib", "z80_ix"])
  if (L[t] === undefined) { console.log("нет метки " + t); process.exit(2); }

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
if (L.vkbd !== undefined) for (let r = 0; r < 8; r++) memory.write(L.vkbd + r, 0xFF, false);

// ---- тап на порты ВИ53 ----
let taps = [], ftaps = [];   // taps — разбор делителей (сбрасывается на границах вызова), ftaps — кадр целиком
{ const _wr = io.output.bind(io);
  io.output = (p, v) => { if ((p & 0xFF) >= 0x08 && (p & 0xFF) <= 0x0B) { taps.push(p & 0xFF, v); ftaps.push(p & 0xFF, v); } return _wr(p, v); }; }

// ---- довести игру до комнаты (как tunecheck_vec.js) ----
const lst = fs.readFileSync(ROM.replace(/\.r0m$/, ".lst"), "latin1").split("\n");
let SYNC = -1;
for (const l of lst) { const m = l.match(/^\s*\d+\+?\s+([0-9A-F]{4})\s.*\s+call\s+init_start_location/); if (m) { SYNC = parseInt(m[1], 16); break; } }
if (SYNC < 0) { console.log("не нашёл call init_start_location"); process.exit(2); }
const ow = memory.write.bind(memory);
let phase2 = "menu";
memory.write = function (a, w, s) {
  a &= 0xffff;
  if (phase2 === "menu" && cpu.pc === SYNC) phase2 = "init";
  if (a === L.curr_room_attrib && phase2 === "init" && w !== 0) phase2 = "game";
  return ow(a, w, s);
};
for (let f = 0; f < 60; f++) v06c.oneInterrupt(true);
if (L.vkbd !== undefined) ow(L.vkbd + 4, 0xFE, false); else keyboard.matrix[2] |= 0x01;   // «0» — старт
let guard = 0; while (phase2 !== "game" && guard++ < 4000) v06c.oneInterrupt(true);
if (phase2 !== "game") { console.log("не дошли до комнаты"); process.exit(2); }
if (L.vkbd !== undefined) ow(L.vkbd + 4, 0xFF, false); else keyboard.matrix[2] &= ~0x01;
memory.write = ow;

// ---- покадровый прогон с тапами ----
const rw = a => memory.read(a & 0xFFFF, false);
let frc = 0, tacc = 0, frame = 0;
// разбор записей ВИ53 по ходу исполнения (как applyTaps tunecheck, но по каждой записи)
const eff = [0, 0, 0], rx = [0, 0, 0], pend = [0, 0, 0];
let onLoad = null, onStop = null;
function applyTaps() {
  for (let i = 0; i < taps.length; i += 2) {
    const p = taps[i], v = taps[i + 1];
    if (p === 0x08) {
      const c = v >> 6;
      if ((v & 0x30) !== 0) { eff[c] = 0; rx[c] = 0; pend[c] = 0; if (onStop) onStop(c); }
    } else {
      const c = 0x0B - p;
      if (rx[c] === 0) { pend[c] = v; rx[c] = 1; }
      else { eff[c] = ((v << 8) | pend[c]) & 0xFFFF; rx[c] = 0; if (onLoad) onLoad(c, eff[c]); }
    }
  }
  taps = [];
}
let c0bad = 0, c0watch = false;
function frameTick() {
  if (c0watch) {
    let latched = false;
    for (let i = 0; i < ftaps.length; i += 2) if (ftaps[i] === 0x08 && ftaps[i + 1] === 0x00) latched = true;
    for (let i = 0; i < ftaps.length; i += 2) {
      const p = ftaps[i], v = ftaps[i + 1];
      if (p === 0x0B && v !== 0xFF && !latched) c0bad++;
      if (p === 0x08 && (v >> 6) === 0 && v !== 0x30 && v !== 0x00) c0bad++;
    }
  }
  ftaps = [];
  applyTaps();
  frame++;
  v06c.irq = true; v06c.checkInterrupt();
}
function step() {
  const c = (cpu.instruction(), cpu.vcycles);
  frc += c; tacc += c;
  if (tacc > 1) { const tn = tacc >> 1; tacc -= tn * 2; timer.Count(tn); }
  if (cpu.last_opcode === 0xd3) io.commit();
  if (frc >= 59904) { frc -= 59904; frameTick(); }
}

// 1) разгон: WARM итераций
let iters = 0, steps = 0;
while (iters < WARM && steps < 5e8) {
  step(); steps++;
  if (cpu.pc === L.msx_frame_off) { iters++; if (iters < WARM) { step(); steps++; } }
}
if (iters < WARM) { console.log("разгон не дошёл до " + WARM + " итераций"); process.exit(2); }
// 2) подмена: вход в msx_frame_off -> loc_AFF8
const RET = rw(cpu.sp) | (rw(cpu.sp + 1) << 8), SP0 = cpu.sp;
const ix = rw(L.z80_ix) | (rw(L.z80_ix + 1) << 8);
const cnt0 = rw(L.unk_5B40);
applyTaps();
cpu.pc = L.loc_AFF8;
c0watch = true;
const F0 = frame;
const EXP = [1512, 1296, 1080, 864, 648, 432, 216];
const calls = [];                 // по вызову: {loads:[[c,div]], stopped:bool, lastc}
let cur = null, ladRet = -1, ladSP = -1, done = false, bad = 0;
onLoad = (c, d) => { if (cur && c !== 0) { cur.loads.push([c, d]); cur.lastc = c; } };
onStop = c => { if (cur && c !== 0 && c === cur.lastc) cur.stopped = true; };
while (frame - F0 <= MAXF) {
  if (cpu.pc === L.audio_msx_ladder && !cur) {
    applyTaps();
    cur = { loads: [], stopped: false, lastc: -1 };
    ladSP = cpu.sp; ladRet = rw(cpu.sp) | (rw(cpu.sp + 1) << 8);
  }
  if (cur && cpu.pc === ladRet && cpu.sp === ladSP + 2) {
    applyTaps();
    calls.push(cur); cur = null;
  }
  if (cpu.pc === RET && cpu.sp === SP0 + 2) { applyTaps(); done = true; break; }
  step();
}
const RF = frame - F0;
c0watch = false;
console.log(`подмена на итерации ${WARM}: z80_ix=0x${ix.toString(16)}, unk_5B40 ${cnt0.toString(16)} -> ${rw(L.unk_5B40).toString(16)}`);
if (!done) {
  console.log(`ПЕРЕКРАСКА НЕ КОНЧИЛАСЬ за ${MAXF} кадров: вызовов лесенки ${calls.length + (cur ? 1 : 0)}` +
              `, D = 0x${cpu.regs[2].toString(16)}`);
  bad++;
} else console.log(`перекраска кончилась за ${RF} кадров (порог ${MAXF}), вызовов лесенки ${calls.length}`);
if (calls.length !== 16) { console.log(`вызовов лесенки ${calls.length}, ожидалось 16`); bad++; }
let silent = 0, partial = 0, unstopped = 0;
calls.forEach((k, i) => {
  const got = k.loads.map(x => x[1]);
  const miss = EXP.filter(d => !got.includes(d));
  if (got.length === 0) silent++;
  else if (miss.length) { partial++; if (partial <= 3) console.log(`  вызов ${i}: нет ступеней ${miss.join(",")} (загружено ${got.join(",")})`); }
  if (got.length && !k.stopped) { unstopped++; if (unstopped <= 3) console.log(`  вызов ${i}: к выходу счётчик ${k.lastc} не остановлен`); }
});
if (silent) { console.log(`вызовов лесенки БЕЗ единой записи делителя в 0x09/0x0A: ${silent} из ${calls.length}`); bad++; }
if (partial) { console.log(`вызовов с пропущенными ступенями: ${partial}`); bad++; }
if (unstopped) { console.log(`вызовов без глушения на выходе: ${unstopped}`); bad++; }
if (calls.length && !silent && !partial) {
  const k = calls[0];
  console.log(`вызов 0: загрузки ${k.loads.map(x => "c" + x[0] + ":" + x[1]).join(" ")}, глушение ${k.stopped ? "да" : "нет"}`);
}
if (c0bad) { console.log(`за перекраску тронут счётчик 0 (секундомер): ${c0bad} записей`); bad++; }
// 3) игра идёт дальше
if (done) {
  let post = 0; const F1 = frame;
  while (post < POST && frame - F1 <= POSTF) { step(); if (cpu.pc === L.msx_frame_off) { post++; step(); } }
  if (post < POST) { console.log(`после перекраски игра стоит: итераций ${post} за ${POSTF} кадров`); bad++; }
  else console.log(`после перекраски ${POST} итераций за ${frame - F1} кадров`);
}
console.log(bad ? `ГЕЙТ ПЕРЕКРАСКИ КРАСНЫЙ: нарушений ${bad}` : "гейт перекраски зелёный");
process.exit(bad ? 1 : 0);
