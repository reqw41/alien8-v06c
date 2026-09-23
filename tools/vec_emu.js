// vec_emu.js — общий запуск vector06js для стендов упакованного релиза (unpack/splashpix/
// tracecmp/c64tune). Каждый вызов mk() — СВОЙ vm-контекст (своя копия эмулятора), поэтому два
// образа можно гонять рядом в одном процессе.
//   const E = require("./vec_emu"); const m = E.mk(romPath);
//   m.rd(a), m.wr(a,v), m.frame() — кадр по 59904 такта с прерыванием, m.cpu, m.keyboard, m.io
//   m.onInstr = pc => {...}   — перед каждой командой (PC начала команды)
//   m.onRead / m.onWrite = (a, v) => {...} — каждое обращение к памяти (адрес 0..0xFFFF)
//   m.taps — [порт, байт, ...] выводов в порты 0x08..0x0B за текущий кадр (сбрасывает вызывающий)
//   m.outs — если массив: туда же ВСЕ выводы в порты (m.outs = [] включает запись)
"use strict";
const fs = require("fs"), vm = require("vm");
const base = "/Users/boris/projects/vector06js";
const FILES = ["i8080-js/i8080_trace.js", "i8080-js/i8080_disasm.js", "i8080-js/i8080.js",
  "src/fili.js", "src/ay.js", "src/fd1793.js", "src/fddimage.js", "src/i8253.js",
  "src/io.js", "src/keyboard.js", "src/memory.js", "src/sound.js", "src/tv.js"];
const SRC = FILES.map(f => [f, fs.readFileSync(base + "/" + f, "utf8")]);

function labels(sld) {
  const L = {};
  for (const l of fs.readFileSync(sld, "latin1").split("\n")) {
    const p = l.split("|");
    if (p.length >= 8 && p[6] === "L") { const n = p[7].split(",")[1]; if (n && !(n in L)) L[n] = +p[5]; }
  }
  return L;
}

function mk(romPath, opt) {
  opt = opt || {};
  const g = {}; g.window = g;
  function fcx() { return { createImageData: () => ({ data: new Uint8ClampedArray(4) }), putImageData() {}, getImageData: () => ({ data: new Uint8ClampedArray(4) }), fillRect() {}, drawImage() {} }; }
  function fc() { return { width: 0, height: 0, style: {}, getContext: () => fcx() }; }
  g.document = { createElement: () => fc(), getElementById: () => fc() };
  g.requestAnimationFrame = () => 0; g.setTimeout = () => 0; g.print = () => 0;
  g.console = { log() {}, debug() {}, warn() {}, error() {}, info() {} };
  const ctx = vm.createContext(g);
  for (const [f, s] of SRC) vm.runInContext(s, ctx, { filename: f });
  const memory = new ctx.Memory(), keyboard = new ctx.Keyboard(), timer = new ctx.I8253(), ay = new ctx.AY(),
        floppy = new (ctx.Floppy().FD1793)(), io = new ctx.IO(keyboard, timer, memory, ay, floppy);
  const m = { memory, keyboard, timer, io, JOY: 0xFF, taps: [], outs: null, onInstr: null, onRead: null, onWrite: null, frames: 0 };
  { const _rd = io.input.bind(io); io.input = p => ((p & 0xFF) === 0x0E ? m.JOY : _rd(p)); }
  { const _wr = io.output.bind(io);
    io.output = (p, v) => { if ((p & 0xFF) >= 0x08 && (p & 0xFF) <= 0x0B) m.taps.push(p & 0xFF, v);
                            if (m.outs) m.outs.push(p & 0xFF, v & 0xFF); _wr(p, v); }; }
  const cpu = new ctx.I8080(memory, io), tape = { advance: () => {}, sample: 0, reset: () => {} },
        v06c = new ctx.Vector06c(cpu, memory, io, ay, tape);
  v06c.bmp = new Uint32Array(576 * 288); v06c.displayFrame = () => {}; v06c.dbg = null;
  v06c.check_breakpoint = () => { if (m.onInstr) m.onInstr(cpu.pc); return false; };
  const IMG = new Uint8Array(fs.readFileSync(romPath)).subarray(0, 0x10000);
  if (IMG[0] !== 0xF3 || IMG[1] !== 0x31) throw new Error(romPath + ": загрузчик не `di / ld sp,imm`");
  memory.init_from_array(IMG, 0); memory.detach_boot && memory.detach_boot();
  const oread = memory.read.bind(memory), owrite = memory.write.bind(memory);
  memory.read = function (a, s) { const v = oread(a, s); if (m.onRead) m.onRead(a & 0xffff, v); return v; };
  memory.write = function (a, w, s) { if (m.onWrite) m.onWrite(a & 0xffff, w & 0xff); return owrite(a, w, s); };
  cpu.pc = 0; cpu.sp = IMG[2] | (IMG[3] << 8); cpu.iff = false;
  m.cpu = cpu; m.v06c = v06c; m.img = IMG; m.ctx = ctx;
  m.rd = a => memory.bytes[memory.tobank(a & 0xffff)];
  m.wr = (a, v) => { memory.bytes[memory.tobank(a & 0xffff)] = v & 0xff; };
  m.dump = () => { const d = new Uint8Array(0x10000); for (let a = 0; a < 0x10000; a++) d[a] = m.rd(a); return d; };
  m.frame = () => { v06c.oneInterrupt(true); m.frames++; };
  m.palette = () => Array.from(io.Palette.slice(0, 16));
  m.regs = () => [cpu.pc, cpu.sp, cpu.iff ? 1 : 0, cpu.store_flags(), ...cpu.regs].join(",");
  return m;
}

// цвет палитры эмулятора (io.commit_palette) из байта BBGGGRRR
function palColor(w8) {
  const b = (w8 & 0xc0) >> 6, g = (w8 & 0x38) >> 3, r = w8 & 7;
  return (0xff000000 | (b << (6 + 16)) | (g << (5 + 8)) | (r << 5)) >>> 0;
}

module.exports = { mk, labels, palColor };
