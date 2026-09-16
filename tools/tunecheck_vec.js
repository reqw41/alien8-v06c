#!/usr/bin/env node
// Гейт ТЕМПА мелодий: все шесть мелодий MSX проигрываются на Векторе целиком, длительность
// в видеокадрах сверяется с моделью (каждый кадр = 114 «проходов» главного цикла MSX).
//
//   node tools/tunecheck_vec.js build/alien8_vec.r0m build/alien8_vec.sld
//
// Это ДРУГОЕ свойство, чем у aycheck.py: тот сверяет значения регистров поканально,
// а здесь — что мелодия кончается там же, где у MSX, и что счётчик длительности
// не накапливает ошибку (остаток проходов обязан переходить в следующий кадр).
//
// Как: игра доводится до комнаты, затем управление принудительно передаётся процедуре
// play_audio (DE = заголовок мелодии) с меткой возврата в стеке — то есть проигрыватель
// работает РОВНО так, как его зовёт игра, и считается число кадров до возврата.
"use strict";
const fs = require("fs"), vm = require("vm"), cp = require("child_process");
const base = "/Users/boris/projects/vector06js";
const [ROM, SLD] = process.argv.slice(2);
const L = {};
for (const l of fs.readFileSync(SLD, "latin1").split("\n")) {
  const p = l.split("|");
  if (p.length >= 8 && p[6] === "L") { const n = p[7].split(",")[1]; if (n && !(n in L)) L[n] = +p[5]; }
}
const TUNES = ["start_game", "game_over", "game_complete", "menu", "obj_5C", "blip"];
for (const t of TUNES) if (L["msx_hdr_" + t] === undefined) { console.log("нет метки msx_hdr_" + t); process.exit(2); }
if (L.play_audio === undefined) { console.log("нет метки play_audio"); process.exit(2); }

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
// БАЗА СТЕКА — ИЗ ОБРАЗА (загрузчик 0x0000: `di` + `ld sp,imm`), а не числом: она переехала
// вместе с переменными в конец нижнего региона и переедет ещё.
const IMG = new Uint8Array(fs.readFileSync(ROM)).subarray(0, 0x10000);
if (IMG[0] !== 0xF3 || IMG[1] !== 0x31) throw new Error("загрузчик не `di / ld sp,imm` — база стека не читается");
const SPBASE = IMG[2] | (IMG[3] << 8);
memory.init_from_array(IMG, 0);
memory.detach_boot && memory.detach_boot();
cpu.pc = 0; cpu.sp = SPBASE; cpu.iff = false;
if (L.vkbd !== undefined) for (let r = 0; r < 8; r++) memory.write(L.vkbd + r, 0xFF, false);

// довести игру до комнаты (как остальные гейты)
const lst = fs.readFileSync(ROM.replace(/\.r0m$/, ".lst"), "latin1").split("\n");
let SYNC = -1;
for (const l of lst) { const m = l.match(/^\s*\d+\+?\s+([0-9A-F]{4})\s.*\s+call\s+init_start_location/); if (m) { SYNC = parseInt(m[1], 16); break; } }
const ow = memory.write.bind(memory);
let phase = "menu";
memory.write = function (a, w, s) {
  a &= 0xffff;
  if (phase === "menu" && cpu.pc === SYNC) phase = "init";
  if (a === L.curr_room_attrib && phase === "init" && w !== 0) phase = "game";
  return ow(a, w, s);
};
for (let f = 0; f < 60; f++) v06c.oneInterrupt(true);
if (L.vkbd !== undefined) ow(L.vkbd + 4, 0xFE, false); else keyboard.matrix[2] |= 0x01;   // «0» — старт
let guard = 0; while (phase !== "game" && guard++ < 4000) v06c.oneInterrupt(true);
if (phase !== "game") { console.log("не дошли до комнаты"); process.exit(2); }
if (L.vkbd !== undefined) ow(L.vkbd + 4, 0xFF, false); else keyboard.matrix[2] &= ~0x01;
memory.write = ow;

// модель: сколько кадров должна звучать мелодия
const MODEL = JSON.parse(cp.execFileSync("python3", ["-c", `
import sys, json, os
sys.path.insert(0, os.path.expanduser('~/projects/alien8-research/msx'))
import msx_psg_model as M
out = {}
for i, nm in enumerate(M.TUNE_NAMES):
    t = M.Tune(M.A_HEADERS + 6 * i)
    t.run(200000)
    out[nm] = [(t.passes + 113) // 114, t.done, len(t.log)]
print(json.dumps(out))
`], { encoding: "utf8" }));

// A8TUNETRACE=<файл>: попутно писать журнал записей AY в формате aytrace_vec.js, чтобы
// ТЕ ЖЕ шесть мелодий можно было сверить поканально (python3 tools/aycheck.py <файл>).
const TRF = process.env.A8TUNETRACE || null;
const trace = [];
let curFrame = 0, reg = -1;
if (TRF) {
  const oout = io.output.bind(io);
  io.output = function (port, w) {
    if (port === 0x15) reg = w & 0x0F;
    else if (port === 0x14 && reg >= 0) trace.push("W " + curFrame + " " + reg + " " + (w & 0xFF));
    return oout(port, w);
  };
  // Метка мелодии ставится ТАМ ЖЕ, где в aytrace_vec.js — на msx_play 0 -> 1, то есть
  // ПОСЛЕ списка инициализации PSG: иначе его записи попадут в поканальную сверку.
  const ow2 = memory.write.bind(memory);
  memory.write = function (a, w, s) {
    a &= 0xffff;
    if (a === L.msx_play && w === 1)
      trace.push("TUNE " + curFrame + " " +
                 ((memory.read(L.msx_ch + 14, false) | (memory.read(L.msx_ch + 15, false) << 8)) - L.msx_stream));
    return ow2(a, w, s);
  };
}

const SENT = 0x0038;   // метка возврата: RST 38h (в игру не попадём — ловим PC)
const IRQDROP = !!process.env.A8_IRQDROP;
let bad = 0, lost = 0;
for (const nm of TUNES) {
  const hdr = L["msx_hdr_" + nm];
  cpu.sp = SPBASE;   // стек игры: своего у стенда нет, 0x7F00 после переезда переменных — их середина
  cpu.memory_write_word(cpu.sp - 2, SENT, true); cpu.sp -= 2;
  cpu.set_rp(2, hdr);           // DE = заголовок мелодии
  cpu.pc = L.play_audio;
  let frames = 0, frc = 0, tacc = 0, steps = 0;
  while (cpu.pc !== SENT && steps < 5e7) {
    // A8_IRQDROP=1 — модель железа: прерывание Вектора не защёлкивается, кадр под di теряется.
    // Проигрыватель мелодии ждёт кадр через ei/halt и под di не сидит, так что потерь тут быть
    // не должно вовсе — счётчик lost это и судит.
    if (frc >= 59904) { frc -= 59904; frames++; curFrame++; if (!cpu.iff) lost++;
      if (!(IRQDROP && !cpu.iff)) { v06c.irq = true; v06c.checkInterrupt(); } }
    const c = (cpu.instruction(), cpu.vcycles);
    steps++; frc += c; tacc += c;
    if (tacc > 1) { const tn = tacc >> 1; tacc -= tn * 2; timer.Count(tn); }
    if (cpu.last_opcode === 0xd3) io.commit();
  }
  const [want, done, nlog] = MODEL[nm];
  if (cpu.pc !== SENT) { console.log(`${nm}: НЕ ЗАВЕРШИЛАСЬ за ${steps} инструкций`); bad++; continue; }
  if (!done) { console.log(`${nm}: модель не дошла до END — мелодия бесконечная?`); bad++; continue; }
  const d = frames - want;
  console.log(`${nm}: кадров у нас ${frames}, у модели ${want} (записей модели ${nlog}), расхождение ${d}`);
  if (Math.abs(d) > 1) bad++;    // допуск 1 кадр: вход в проигрыватель приходится на середину кадра
}
console.log("---");
console.log(`потеряно кадров (обратный ход на di): ${lost}`);
if (TRF) { fs.writeFileSync(TRF, trace.join("\n") + "\n"); console.log(`журнал записей AY: ${TRF} (${trace.length} строк)`); }
console.log(bad ? `РАСХОЖДЕНИЙ ТЕМПА: ${bad} из ${TUNES.length}` : `все ${TUNES.length} мелодии совпали по длительности`);
process.exit(bad ? 1 : 0);
