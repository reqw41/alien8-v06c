#!/usr/bin/env node
// ГЕЙТ РАСКЛАДОК И МЕНЮ Alien 8: клавиша матрицы Вектора -> биты user_input, отдельно для каждого
// из трёх режимов; выбор режима в меню; полоса подсветки; пауза на ВК.
// Ни локстеп, ни гейт картинки этого не видят: локстеп кормит ряды ZX напрямую и собирает ДРУГУЮ
// цель (там остался оригинальный keyboard:), а гейт картинки ходит только клавишами раскладки 1.
//   node tools/inputcheck_vec.js build/alien8_vec.r0m build/alien8_vec.sld
// Часть 1: меню — нажатие '1'/'2'/'3' меняет tmp_input_method (номер режима) и user_input_method.
// Часть 2: полоса подсветки — заливка в плоскости 0 на своих строках, текст в буфере цел.
// Часть 3: ввод — главный код паркуется в jp $, работает только ISR (она набивает vec_kbmat);
//          check_user_input зовётся точечно, читается user_input.
// Часть 4: пауза — audio_CE22 выходит сразу без ВК и виснет в ожидании отпускания с ВК.
"use strict";
const fs = require("fs"), vm = require("vm");
const base = "/Users/boris/projects/vector06js";
const [ROM, SLD] = process.argv.slice(2);
const L = {};
for (const l of fs.readFileSync(SLD, "latin1").split("\n")) {
  const p = l.split("|"); if (p.length >= 8 && p[6] === "L") { const n = p[7].split(",")[1]; if (n && !(n in L)) L[n] = +p[5]; }
}
const g = {}; g.window = g; g.document = { createElement: () => fc(), getElementById: () => fc() };
function fcx() { return { createImageData: () => ({ data: new Uint8ClampedArray(4) }), putImageData: () => {}, getImageData: () => ({ data: new Uint8ClampedArray(4) }), fillRect() {}, drawImage() {} }; }
function fc() { return { width: 0, height: 0, style: {}, getContext: () => fcx() }; }
g.requestAnimationFrame = () => 0; g.setTimeout = () => 0; g.print = () => 0;
g.console = { log() {}, debug() {}, warn() {}, error() {}, info() {} };
const ctx = vm.createContext(g);
for (const f of ["i8080-js/i8080_trace.js", "i8080-js/i8080_disasm.js", "i8080-js/i8080.js", "src/fili.js", "src/ay.js", "src/fd1793.js", "src/fddimage.js", "src/i8253.js", "src/io.js", "src/keyboard.js", "src/memory.js", "src/sound.js", "src/tv.js"])
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
const rd = a => memory.bytes[memory.tobank(a & 0xffff)];
const wr = (a, v) => memory.write(a & 0xffff, v & 0xff, false);
const PARK = 0x0030;           // дыра между загрузчиком (0x0000..0x0006) и RST 38h (0x0038)
const SP = 0x7FFE;             // стек игры растёт вниз от 0x8000

// ---- клавиши матрицы Вектора: [ряд, маска] ----
// ряд 0 ВК/стрелки, ряд 2 цифры 0..7, ряд 3 цифры 8,9,
// ряд 4 @ABCDEFG, ряд 5 HIJKLMNO, ряд 6 PQRSTUVW, ряд 7 XYZ[\]^ПРБ
const K = { "ВК": [0, 0x04], "<": [0, 0x10], "^": [0, 0x20], ">": [0, 0x40], "v": [0, 0x80], "ПРБ": [7, 0x80] };
"@ABCDEFG".split("").forEach((c, i) => K[c] = [4, 1 << i]);
"HIJKLMNO".split("").forEach((c, i) => K[c] = [5, 1 << i]);
"PQRSTUVW".split("").forEach((c, i) => K[c] = [6, 1 << i]);
"XYZ".split("").forEach((c, i) => K[c] = [7, 1 << i]);
for (let d = 0; d <= 7; d++) K["" + d] = [2, 1 << d];
K["8"] = [3, 0x01]; K["9"] = [3, 0x02];
function press(keys) { keyboard.matrix.fill(0); for (const k of keys) { const [r, m] = K[k]; keyboard.matrix[r] |= m; } }

let bad = 0;
const chk = (ok, msg) => { if (!ok) { bad++; console.log("  x " + msg); } else console.log("  + " + msg); };

cpu.pc = 0; cpu.sp = 0x8000; cpu.iff = false;
for (let f = 0; f < 150; f++) v06c.oneInterrupt(true);   // загрузка, меню нарисовано, крутится menu_loop

// ================= часть 1: меню =================
// Экран Вектора столбцовый: адрес = плоскость + столбец*256 + (Y + 32); print_8x8 идёт вниз по
// младшему байту, поэтому знакоместо строки Y занимает строки Y+25..Y+32. X = 48 -> столбец 6.
// Строки меню: 1 KEYBOARD Y=135 (10 знаков), 2 CURSOR Y=111 (8), 3 DIRECTIONAL CONTROL Y=87 (21).
const BAND = [[160, 10], [136, 8], [112, 21]];
const SCR = 0x8000, BUF = 0xA000;
function bandCheck(idx) {
  let fill = 0, need = 0, glyph = 0, stale = 0;
  for (let m = 0; m < 3; m++) {
    const [row0, w] = BAND[m];
    for (let c = 6; c < 6 + w; c++) for (let y = row0; y < row0 + 8; y++) {
      const s = rd(SCR + c * 256 + y), b = rd(BUF + c * 256 + y);
      if (m === idx) { need++; if (s === 0xFF) fill++; if (b !== 0xFF && b !== 0x00) glyph++; }
      else if (s !== b) stale++;   // не выбранная строка: экран обязан повторять буфер
    }
  }
  return { fill, need, glyph, stale };
}
console.log("МЕНЮ: выбор режима клавишами 1/2/3, полоса подсветки");
for (const [key, idx, uim] of [["1", 0, 0], ["2", 1, 4], ["3", 2, 8], ["2", 1, 4], ["1", 0, 0]]) {
  press([key]); for (let f = 0; f < 25; f++) v06c.oneInterrupt(true);
  press([]);    for (let f = 0; f < 25; f++) v06c.oneInterrupt(true);
  const oi = rd(L.tmp_input_method), ui = rd(L.user_input_method);
  chk(oi === idx && ui === uim, `'${key}' -> tmp_input_method=${oi} (ждём ${idx}), user_input_method=${ui} (ждём ${uim})`);
  const b = bandCheck(idx);
  chk(b.fill === b.need, `   полоса залита в плоскости 0: ${b.fill} из ${b.need} байт строки ${idx + 1}`);
  chk(b.glyph > 0, `   буквы в буфере (плоскость 1) целы: ${b.glyph} байт строки отличаются от фона`);
  chk(b.stale === 0, `   с двух других строк полоса снята: несовпадений экран/буфер ${b.stale}`);
}

// ================= часть 2: раскладки =================
wr(PARK, 0xC3); wr(PARK + 1, PARK & 0xFF); wr(PARK + 2, PARK >> 8);
cpu.pc = PARK; cpu.sp = 0x8000; cpu.iff = true;
press([]); for (let f = 0; f < 3; f++) v06c.oneInterrupt(true);

function userInput(uim, keys) {
  wr(L.user_input_method, uim);
  wr(L.byte_5B23, 0); wr(L.byte_5B24, 0);   // конец игры: иначе check_user_input выходит сразу
  press(keys); for (let f = 0; f < 3; f++) v06c.oneInterrupt(true);   // ISR набивает vec_kbmat
  cpu.iff = false;
  wr(SP + 1, PARK >> 8); wr(SP, PARK & 0xFF); cpu.sp = SP;            // адрес возврата = PARK
  cpu.pc = L.check_user_input;
  for (let n = 0; n < 100000 && cpu.pc !== PARK; n++) cpu.instruction();
  if (cpu.pc !== PARK) throw new Error("check_user_input не вернулся");
  cpu.iff = true;
  return rd(L.user_input);
}
const BITS = ["влево", "вправо", "вперёд", "прыжок", "взять", "взять(dir)"];
const show = v => v ? BITS.filter((_, i) => v & (1 << i)).join("+") : "-";
const TESTS = [
  // 1 KEYBOARD — клавиши ОРИГИНАЛА Alien 8 (ZX: Z C M B / X V N SYM / A..G ENTER..H / Q..T P..Y / цифры)
  ["1 KEYBOARD", 0, [
    [["Z"], 0x01], [["C"], 0x01], [["M"], 0x01], [["B"], 0x01],
    [["X"], 0x02], [["V"], 0x02], [["N"], 0x02],
    [["A"], 0x04], [["D"], 0x04], [["F"], 0x04], [["G"], 0x04], [["S"], 0x04],
    [["H"], 0x04], [["J"], 0x04], [["K"], 0x04], [["L"], 0x04],
    [["Q"], 0x08], [["W"], 0x08], [["E"], 0x08], [["R"], 0x08], [["T"], 0x08],
    [["P"], 0x08], [["O"], 0x08], [["I"], 0x08], [["U"], 0x08], [["Y"], 0x08],
    [["0"], 0x10], [["7"], 0x10], [["3"], 0x10], [["8"], 0x10], [["9"], 0x10],
    [["<"], 0x00], [[">"], 0x00], [["^"], 0x00], [["v"], 0x00], [["ПРБ"], 0x00], [["ВК"], 0x00],
    [["Z", "Q"], 0x09], [["X", "A", "5"], 0x16], [[], 0x00],
  ]],
  ["2 CURSOR", 4, [
    [["<"], 0x01], [[">"], 0x02], [["^"], 0x04], [["ПРБ"], 0x08], [["v"], 0x10],
    [["Z"], 0x00], [["X"], 0x00], [["A"], 0x00], [["Q"], 0x00], [["M"], 0x00],
    [["0"], 0x00], [["7"], 0x00], [["9"], 0x00], [["ВК"], 0x00],
    [["<", "^"], 0x05], [[">", "ПРБ"], 0x0A], [[], 0x00],
  ]],
  ["3 DIRECTIONAL CONTROL", 8, [
    [["<"], 0x01], [[">"], 0x02], [["^"], 0x04], [["v"], 0x10], [["ПРБ"], 0x08],
    [["0"], 0x20], [["7"], 0x20], [["5"], 0x20],
    [["Z"], 0x00], [["X"], 0x00], [["A"], 0x00], [["Q"], 0x00], [["M"], 0x00],
    [["8"], 0x00], [["9"], 0x00], [["ВК"], 0x00],
    [["<", "ПРБ", "3"], 0x29], [["^", "v"], 0x14], [[], 0x00],
  ]],
];
for (const [name, uim, cases] of TESTS) {
  console.log(`РЕЖИМ ${name} (user_input_method=${uim})`);
  for (const [keys, want] of cases) {
    const got = userInput(uim, keys);
    chk(got === want, `${(keys.join("+") || "ничего").padEnd(12)} -> ${got.toString(2).padStart(6, "0")} (${show(got)}), ждём ${want.toString(2).padStart(6, "0")} (${show(want)})`);
  }
}
// «взять/бросить» проходит через chk_pickup_drop: в directional бит 5, иначе бит 4
console.log("chk_pickup_drop: бит «взять» по режиму");
function pickup(uim, keys) {
  userInput(uim, keys);
  cpu.iff = false; wr(SP + 1, PARK >> 8); wr(SP, PARK & 0xFF); cpu.sp = SP;
  cpu.pc = L.chk_pickup_drop;
  for (let n = 0; n < 10000 && cpu.pc !== PARK; n++) cpu.instruction();
  if (cpu.pc !== PARK) throw new Error("chk_pickup_drop не вернулся");
  cpu.iff = true; return cpu.a() & 0xFF;
}
chk(pickup(0, ["0"]) === 0x10, "1 KEYBOARD: цифра 0 -> «взять»");
chk(pickup(4, ["v"]) === 0x10, "2 CURSOR: стрелка вниз -> «взять»");
chk(pickup(8, ["0"]) === 0x10, "3 DIRECTIONAL: цифра 0 -> «взять» (бит 5 сдвигается в 4)");
chk(pickup(8, ["v"]) === 0x00, "3 DIRECTIONAL: стрелка вниз — это юг, а не «взять»");
chk(pickup(0, ["Z"]) === 0x00, "1 KEYBOARD: поворот — не «взять»");

// ================= часть 3: пауза на ВК =================
// audio_CE22 ждёт нажатия внутри себя, поэтому проверяем не прогоном, а тем, что процедура
// читает ряд 0 матрицы Вектора и при ненажатой ВК возвращается сразу.
console.log("ПАУЗА");
function pauseRuns(keys) {
  cpu.iff = true; press(keys); for (let f = 0; f < 3; f++) v06c.oneInterrupt(true);
  cpu.iff = false; wr(SP + 1, PARK >> 8); wr(SP, PARK & 0xFF); cpu.sp = SP; cpu.pc = L.audio_CE22;
  let n = 0; for (; n < 20000 && cpu.pc !== PARK; n++) cpu.instruction();
  return cpu.pc === PARK ? n : -1;
}
chk(pauseRuns([]) >= 0, "без ВК audio_CE22 выходит сразу");
chk(pauseRuns(["ВК"]) < 0, "с зажатой ВК audio_CE22 не выходит (ждёт отпускания) — пауза встала");
chk(pauseRuns(["ПРБ"]) >= 0, "пробел паузу не ставит (он прыжок в раскладках 2 и 3)");
// ЗАЩИТА ОРИГИНАЛА: пауза только если нажат ВК и НИ ОДНОЙ клавиши того же ряда. В ряду 0 Вектора
// вместе с ВК лежат стрелки — клавиши движения раскладок 2 и 3; без этой проверки ложная пауза
// (в том числе «призрак» матрицы) выглядит как зависание.
for (const arr of ["<", ">", "^", "v"])
  chk(pauseRuns(["ВК", arr]) >= 0, `ВК вместе со стрелкой ${arr} паузу НЕ ставит (защита оригинала)`);

console.log(bad ? `РАСХОЖДЕНИЙ: ${bad}` : "все проверки сошлись");
process.exit(bad ? 1 : 0);
