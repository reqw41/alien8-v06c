#!/usr/bin/env node
// Журнал записей в AY на Векторе: headless vector06js, перехват портов 0x15 (номер регистра)
// и 0x14 (данные). Кадр считается по RST7 (59904 такта).
//
//   node tools/aytrace_vec.js build/alien8_vec.r0m build/alien8_vec.sld <итераций> [inputs.txt]
//
// Переменные окружения:
//   A8ROOM=<n>   подменить комнату при входе (как в остальных гейтах)
//   A8MENU=1     НЕ пропускать меню (нужно для мелодии меню и «блипа»)
//   A8SFX=id:слот:тиков:hi:lo   принудительно запустить эффект на итерации A8SFXIT (по умолчанию 10):
//                записывается тот же дескриптор слота, что кладёт msx_sfx_start. Нужно для
//                эффектов 1, 2, 9: сценарий ходьбы до них не доходит, а проверить их надо.
//
// Формат вывода (строки, которые читает tools/aycheck.py):
//   W <кадр> <регистр> <значение>              — запись в регистр AY
//   TUNE <кадр> <смещение потока канала 2>     — начало мелодии (msx_play 0 -> 1)
//   SFX <кадр> <слот> <id> <тиков> <hi> <lo>   — запуск эффекта (заполнен дескриптор слота)
//   ITER <кадр> <номер итерации>
"use strict";
const fs = require("fs"), vm = require("vm");
const base = "/Users/boris/projects/vector06js";
const [ROM, SLD, NS, INPUTS] = process.argv.slice(2);
const N = +NS || 300;
const LAG = +(process.env.A8_LAG || 1);
const L = {};
for (const l of fs.readFileSync(SLD, "latin1").split("\n")) {
  const p = l.split("|");
  if (p.length >= 8 && p[6] === "L") { const n = p[7].split(",")[1]; if (n && !(n in L)) L[n] = +p[5]; }
}
for (const need of ["msx_play", "msx_sfx", "msx_ch", "msx_stream", "seed_2", "curr_room_attrib"])
  if (L[need] === undefined) { console.log("нет метки " + need + " — сборка без звука?"); process.exit(2); }
const SEED2HI = L.seed_2 + 1, ROOM = L.curr_room_attrib, VKBD = L.vkbd;
const lst = fs.readFileSync(ROM.replace(/\.r0m$/, ".lst"), "latin1").split("\n");
let SYNC = -1;
for (const l of lst) { const m = l.match(/^\s*\d+\+?\s+([0-9A-F]{4})\s.*\s+call\s+init_start_location/); if (m) { SYNC = parseInt(m[1], 16); break; } }
if (SYNC < 0) throw new Error("не нашёл call init_start_location");

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
// ДЖОЙСТИК ВЕКТОРА (порт 0x0E, чтение) в vector06js СОБИРАЕТСЯ ИЗ МАТРИЦЫ (стрелки, пробел, W) —
// в стенде это подмешивало бы джойстик к каждому нажатию клавиши, чего на живом Векторе нет
// (там это отдельная микросхема). Подменяем чтение: по умолчанию покой, сценарий задаёт joy(...).
// Биты порта active-low: 0 RIGHT, 1 LEFT, 2 UP, 3 DOWN, 6 FIRE1, 7 FIRE2; биты 4,5 схема держит в 1.
const JOY_R=0x01, JOY_L=0x02, JOY_U=0x04, JOY_D=0x08, JOY_F1=0x40, JOY_F2=0x80, JOY_IDLE=0xFF;
let JOY = JOY_IDLE;
function joy(...bits){ JOY = JOY_IDLE; for(const b of bits) JOY &= ~b & 0xFF; return JOY; }
{ const _rd = io.input.bind(io); io.input = p => ((p & 0xFF) === 0x0E ? JOY : _rd(p)); }
const cpu = new ctx.I8080(memory, io), tape = { advance: () => {}, sample: 0, reset: () => {} },
      v06c = new ctx.Vector06c(cpu, memory, io, ay, tape);
v06c.bmp = new Uint32Array(576 * 288); v06c.displayFrame = () => {}; v06c.check_breakpoint = () => false; v06c.dbg = null;
memory.init_from_array(new Uint8Array(fs.readFileSync(ROM)).subarray(0, 0x10000), 0);
memory.detach_boot && memory.detach_boot();
cpu.pc = 0; cpu.sp = 0xBC00; cpu.iff = false;
if (VKBD !== undefined) for (let r = 0; r < 8; r++) memory.write(VKBD + r, 0xFF, false);
const ow = memory.write.bind(memory);
const poke = (a, v) => ow(a & 0xffff, v & 0xff, false);
const KEYS = { shift: [0, 0], z: [0, 1], x: [0, 2], c: [0, 3], v: [0, 4], a: [1, 0], s: [1, 1], d: [1, 2], f: [1, 3], g: [1, 4],
  q: [2, 0], w: [2, 1], e: [2, 2], r: [2, 3], t: [2, 4], "1": [3, 0], "2": [3, 1], "3": [3, 2], "4": [3, 3], "5": [3, 4],
  "0": [4, 0], "9": [4, 1], "8": [4, 2], "7": [4, 3], "6": [4, 4], p: [5, 0], o: [5, 1], i: [5, 2], u: [5, 3], y: [5, 4],
  enter: [6, 0], l: [6, 1], k: [6, 2], j: [6, 3], h: [6, 4], space: [7, 0], sym: [7, 1], m: [7, 2], n: [7, 3], b: [7, 4] };
const VKEYS = { z: [7, 0x04], x: [7, 0x01], a: [4, 0x02], q: [6, 0x02], "0": [2, 0x01], space: [7, 0x80] };
const rows = new Uint8Array(8).fill(0xFF);
function key(k, down) {
  if (VKBD === undefined) { const [r, b] = VKEYS[k]; if (down) keyboard.matrix[r] |= b; else keyboard.matrix[r] &= ~b; return; }
  const [r, b] = KEYS[k]; if (down) rows[r] &= ~(1 << b); else rows[r] |= (1 << b); poke(VKBD + r, rows[r]);
}
const inputs = {};
if (INPUTS && fs.existsSync(INPUTS)) for (const l of fs.readFileSync(INPUTS, "utf8").split("\n")) {
  const m = l.trim().match(/^(\d+)\s+(\S+)\s+(down|up)/i);
  if (m) (inputs[+m[1] + LAG] = inputs[+m[1] + LAG] || []).push([m[2].toLowerCase(), m[3].toLowerCase() === "down"]);
}

// ---------------- перехват записей в AY ----------------
let frame = 0, reg = -1, nw = 0;
const oout = io.output.bind(io);
const ALL = process.env.A8TRACE === "all";
let logging = true;
io.output = function (port, w) {
  if (port === 0x15) reg = w & 0x0F;
  else if (port === 0x14) { if (logging && reg >= 0) { console.log("W " + frame + " " + reg + " " + (w & 0xFF)); nw++; } }
  return oout(port, w);
};

// ---------------- события драйвера ----------------
const T = L.graphic_objs_tbl, SFX = L.msx_sfx, CH = L.msx_ch, STREAM = L.msx_stream, PLAY = L.msx_play;
let phase = process.env.A8MENU ? "menuplay" : "menu", iter = 0, startIter = 0, startseq = null;
// A8SFX: hi:lo можно задать именем списка эффекта 9 — "e9a" / "e9b" (адрес берётся из .sld)
const FSFX = process.env.A8SFX ? (function (p) {
  if (p.length === 4) { const a = L["msx_" + p[3]]; if (a === undefined) throw new Error("нет метки msx_" + p[3]);
    return [+p[0], +p[1], +p[2], a & 0xFF, a >> 8]; }   // (+2) = младший, (+3) = старший
  return p.map(Number);
})(process.env.A8SFX.split(":")) : null;
const FSFXIT = +(process.env.A8SFXIT || 10);
memory.write = function (a, w, s) {
  a &= 0xffff;
  if (phase === "menu" && cpu.pc === SYNC) {
    poke(L.seed_1, 0x34); poke(L.seed_1 + 1, 0x12); poke(L.seed_2, 0x78); poke(L.seed_2 + 1, 0x56); poke(L.seed_3, 0x9A);
    phase = "init";
  }
  if (process.env.A8ROOM && phase === "init" && (a === T + 8 || a === T + 40)) w = +process.env.A8ROOM;
  if (a === ROOM && phase === "init" && w !== 0) { phase = "game"; key("0", false); }
  if (a === SEED2HI && phase === "game") {
    iter++; console.log("ITER " + frame + " " + iter);
    for (const [k, d] of (inputs[iter] || [])) key(k, d);
    if (FSFX && iter - startIter === FSFXIT) {
      const [id, sl, tk, hi, lo] = FSFX;
      ow(SFX + sl * 4, id, false); ow(SFX + sl * 4 + 1, tk, false);
      ow(SFX + sl * 4 + 2, hi, false); ow(SFX + sl * 4 + 3, lo, false);
      ow(L.msx_busy, 1, false);
      // указатель списка эффекта 9 печатаем в адресах MSX — модель читает списки из картриджа
      let h2 = hi, l2 = lo;
      if (id === 9) { const a16 = hi | (lo << 8);
        const m = a16 === L.msx_e9a ? 0x456F : a16 === L.msx_e9b ? 0x457A : 0;
        if (m) { h2 = m & 0xFF; l2 = m >> 8; } }
      console.log("SFX " + frame + " " + sl + " " + id + " " + tk + " " + h2 + " " + l2 + " " +
                  memory.read(L.msx_stepc, false) + " " + memory.read(T + 1, false) + " " + memory.read(T + 2, false));
    }
  }
  if (a === PLAY && w === 1) {
    const p = memory.read(CH + 14, false) | (memory.read(CH + 15, false) << 8);
    console.log("TUNE " + frame + " " + (p - STREAM));
  }
  // ЗАПУСК эффекта отличается от тика по ПОРЯДКУ записей в дескриптор: msx_sfx_start пишет
  // +0,+1,+2,+3 подряд, а тик эффекта 9 переписывает указатель как +3, потом +2. Без этого
  // различения каждый тик эффекта 9 выглядел бы новым запуском и обрывал сверку.
  if (a >= SFX && a < SFX + 12) {
    const s = (a - SFX) >> 2, off = (a - SFX) % 4;
    if (off === 0) startseq = [s, 1];
    else if (startseq && startseq[0] === s && startseq[1] === off) {
      startseq[1]++;
      if (off === 3) {
        const id = memory.read(SFX + s * 4, false);
        let p2 = memory.read(SFX + s * 4 + 2, false), p3 = w;
        // Эффект 9 держит в параметре УКАЗАТЕЛЬ на список периодов. Модель читает списки
        // из картриджа MSX, поэтому наш адрес переводим в адрес MSX (0x456F / 0x457A).
        if (id === 9) { const a16 = p2 | (p3 << 8);
          const m = a16 === L.msx_e9a ? 0x456F : a16 === L.msx_e9b ? 0x457A : 0;
          if (m) { p2 = m & 0xFF; p3 = m >> 8; } }
        // для эффекта 3 («шаги») в модель нужны живые счётчик шагов и координаты игрока
        if (id !== 0) console.log("SFX " + frame + " " + s + " " + id + " " + memory.read(SFX + s * 4 + 1, false) + " " +
                                  p2 + " " + p3 + " " +
                                  memory.read(L.msx_stepc, false) + " " +
                                  memory.read(T + 1, false) + " " + memory.read(T + 2, false));
        startseq = null;
      }
    } else startseq = null;
  }
  return ow(a, w, s);
};

// Кадр считается и здесь: мелодия старта играет ДО входа в комнату, а oneInterrupt —
// это ровно один кадр Вектора.
for (let f = 0; f < 60; f++) { v06c.oneInterrupt(true); frame++; }
if (!process.env.A8MENU) {
  key("0", true);
  let guard = 0; while (phase !== "game" && guard++ < 4000) { v06c.oneInterrupt(true); frame++; }
  if (phase !== "game") { console.log("не дошли до комнаты"); process.exit(2); }
}
startIter = iter; let frc = 0, tacc = 0, steps = 0, lost = 0;
const IRQDROP = !!process.env.A8_IRQDROP;
const LIMIT = process.env.A8MENU ? N : N;   // A8MENU: N = кадров, иначе N = итераций
while (steps < 6e8) {
  if (process.env.A8MENU ? frame >= LIMIT : iter - startIter >= LIMIT) break;
  // A8_IRQDROP=1 — модель железа: прерывание Вектора не защёлкивается, кадр под di теряется.
  if (frc >= 59904) { frc -= 59904; frame++; if (!cpu.iff) lost++;
    if (!(IRQDROP && !cpu.iff)) { v06c.irq = true; v06c.checkInterrupt(); } }
  const c = (cpu.instruction(), cpu.vcycles);
  steps++; frc += c; tacc += c;
  if (tacc > 1) { const tn = tacc >> 1; tacc -= tn * 2; timer.Count(tn); }
  if (cpu.last_opcode === 0xd3) io.commit();
}
console.log("# записей " + nw + ", кадров " + frame + ", итераций " + (iter - startIter)
  + ", потеряно кадров (обратный ход на di) " + lost);
process.exit(nw ? 0 : 1);
