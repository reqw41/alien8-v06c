#!/usr/bin/env node
// ГЕЙТ РАСКЛАДОК И МЕНЮ Alien 8: клавиша матрицы Вектора -> биты user_input, отдельно для каждого
// из трёх режимов; выбор режима в меню; полоса подсветки; пауза на ВК.
// Ни локстеп, ни гейт картинки этого не видят: локстеп кормит ряды ZX напрямую и собирает ДРУГУЮ
// цель (там остался оригинальный keyboard:), а гейт картинки ходит только клавишами раскладки 1.
//   node tools/inputcheck_vec.js build/alien8_vec.r0m build/alien8_vec.sld
// Часть 1: меню — нажатие '1'/'2'/'3' меняет tmp_input_method (номер режима) и user_input_method.
// Часть 1J: меню с ДЖОЙСТИКА — направление листает раскладку ПО ФРОНТУ, FIRE = «0 START GAME».
// Часть 2: полоса подсветки — заливка в плоскости 0 на своих строках, текст в буфере цел.
// Часть 3: ввод — главный код паркуется в jp $, работает только ISR (она набивает vec_kbmat);
//          check_user_input зовётся точечно, читается user_input.
// Часть 3J: ввод с ДЖОЙСТИКА во всех трёх раскладках, вместе с клавишами, замок кнопки после
//          старта из меню, «порта нет», ряды ZX и цена vec_joy в тактах.
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
// С 2026-10-19 джойстик — «П»: порт 6 за портом 5, как в ядре MiSTer (Vector-06C.sv, joyP_o:
// биты 6:5 порта 5 выбирают 00 = A&B, 01 = A, 10 = B, 11 = никого). Стенд держит одно устройство
// (A); порт 0x0E «молчит» (0xFF), чтобы засчитаться мог только путь через «П».
let JSEL = 3;
{ const _out = io.output.bind(io); io.output = (p, v) => { if ((p & 0xFF) === 0x05) JSEL = (v >> 5) & 3; return _out(p, v); }; }
{ const _rd = io.input.bind(io); io.input = p => ((p & 0xFF) === 0x06 ? (JSEL < 2 ? JOY : 0xFF) : (p & 0xFF) === 0x0E ? 0xFF : _rd(p)); }
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
const rd = a => memory.bytes[memory.tobank(a & 0xffff)];
const wr = (a, v) => memory.write(a & 0xffff, v & 0xff, false);
const PARK = 0x0030;           // дыра между загрузчиком (0x0000..0x0006) и RST 38h (0x0038)
const SP = SPBASE - 2;         // стек игры растёт вниз от SPBASE (= seed_1)

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

cpu.pc = 0; cpu.sp = SPBASE; cpu.iff = false;
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

// ============ часть 1J: меню с джойстика (CPU ещё крутит menu_loop) ============
// Мелодия меню играет дольше 1200 кадров, и всё это время menu_loop висит внутри
// play_audio_until_keypress. Клавиши работают потому, что ЛЮБАЯ клавиша рвёт мелодию; стик — потому
// что a8_anykey читает ещё и vec_joyraw. Без этого весь раздел молчал бы, а раскладка не менялась.
console.log("МЕНЮ: джойстик");
const JNAME = new Map([[JOY_R, "RIGHT"], [JOY_L, "LEFT"], [JOY_U, "UP"], [JOY_D, "DOWN"], [JOY_F1, "FIRE1"], [JOY_F2, "FIRE2"]]);
const frames = f => { for (let i = 0; i < f; i++) v06c.oneInterrupt(true); };
function joyStep(bits, name, idx, uim) {
  joy(...bits); frames(8);
  joy();        frames(8);
  const oi = rd(L.tmp_input_method), ui = rd(L.user_input_method);
  chk(oi === idx && ui === uim, `${name.padEnd(22)} -> tmp_input_method=${oi} (ждём ${idx}), user_input_method=${ui} (ждём ${uim})`);
  const b = bandCheck(idx);
  chk(b.fill === b.need && b.stale === 0, `   полоса подсветки переехала на строку ${idx + 1}: залито ${b.fill} из ${b.need}, чужих несовпадений ${b.stale}`);
}
press([]);                                   // клавиатура молчит: листает именно джойстик
joyStep([JOY_R], "RIGHT (вперёд)",   1, 4);
joyStep([JOY_D], "DOWN  (вперёд)",   2, 8);
joyStep([JOY_D], "DOWN  (по кругу)", 0, 0);
joyStep([JOY_L], "LEFT  (назад)",    2, 8);
joyStep([JOY_U], "UP    (назад)",    1, 4);
// АНТИДРЕБЕЗГ: menu_loop крутится много раз в кадр, а vec_joyraw обновляется раз в кадр. По уровню
// одно отклонение стика пролистало бы все три раскладки; фронт (vec_joyprv) даёт ровно один шаг.
joy(JOY_R); frames(60);
chk(rd(L.tmp_input_method) === 2, `удержание RIGHT 60 кадров = ОДИН шаг: tmp_input_method=${rd(L.tmp_input_method)} (ждём 2)`);
joy(); frames(8);
// FIRE сведена к клавише '0' в рядах ZX: меню обязано увидеть её как «0 START GAME».
press(["1"]); frames(25); press([]); frames(25);             // вернуться в раскладку 1
chk(rd(L.tmp_input_method) === 0, "клавиша '1' после джойстика работает по-прежнему");
chk(rd(L.vec_pal + 8) === 0xC0, "в меню vec_pal+8 = синий фон полосы (0xC0)");
wr(L.vec_joylck, 0);                         // замок обнулён: пусть его взведёт именно a8_menu_exit
joy(JOY_F1); frames(4);
chk((rd(L.vec_zxrows + 4) & 1) === 0, "FIRE1 прижимает клавишу '0' в ряду ZX 4");
chk((rd(L.vec_rptab + 0) & 1) === 1, "read_key(0) видит кнопку — «нажми любую клавишу» её примет");
frames(300);
chk(rd(L.vec_joylck) !== 0, `FIRE1 = старт игры: a8_menu_exit взвёл замок кнопок (vec_joylck=0x${rd(L.vec_joylck).toString(16)})`);
chk(rd(L.vec_pal + 8) !== 0xC0, `игра пошла: палитра комнаты вместо меню (vec_pal+8=0x${rd(L.vec_pal + 8).toString(16)})`);
// FIRE1 НАРОЧНО ОСТАЁТСЯ ЗАЖАТОЙ: замок проверяется первым же опросом ввода (часть 3J), потому что
// любой опрос с отпущенной кнопкой открыл бы его сам.

// ================= часть 2: раскладки =================
wr(PARK, 0xC3); wr(PARK + 1, PARK & 0xFF); wr(PARK + 2, PARK >> 8);
cpu.pc = PARK; cpu.sp = SPBASE; cpu.iff = true;
press([]); for (let f = 0; f < 3; f++) v06c.oneInterrupt(true);

function userInput(uim, keys, jbits) {
  wr(L.user_input_method, uim);
  wr(L.byte_5B23, 0); wr(L.byte_5B24, 0);   // конец игры: иначе check_user_input выходит сразу
  joy(...(jbits || []));
  press(keys); for (let f = 0; f < 3; f++) v06c.oneInterrupt(true);   // ISR набивает vec_kbmat и vec_joyraw
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
// ЗАМОК КНОПКИ. Игру только что запустили с зажатой FIRE1 (часть 1J) — прыжком она читаться НЕ
// должна, пока кнопку не отпустят. Идёт ПЕРВЫМ: замок открывает сам a8_in_joy, и любой следующий
// опрос с отпущенной кнопкой его уже снял бы.
console.log("ДЖОЙСТИК: замок кнопки после старта из меню");
chk(userInput(0, [], [JOY_F1]) === 0x00, "зажатая с меню FIRE1 прыжком НЕ читается");
chk(userInput(0, [], []) === 0x00, "кнопку отпустили — ввод пуст");
chk(userInput(0, [], [JOY_F1]) === 0x08, "нажали заново — прыжок");
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
// ============ часть 3J: джойстик в игре ============
const JT = [
  ["1 KEYBOARD", 0, [
    [[JOY_L], 0x01], [[JOY_R], 0x02], [[JOY_U], 0x04], [[JOY_F1], 0x08], [[JOY_F2], 0x10],
    [[JOY_D], 0x00],                                    // «вниз» в поворотных раскладках не заведено
    [[JOY_L, JOY_F1], 0x09], [[JOY_U, JOY_F2], 0x14], [[], 0x00],
  ]],
  ["2 CURSOR", 4, [
    [[JOY_L], 0x01], [[JOY_R], 0x02], [[JOY_U], 0x04], [[JOY_F1], 0x08], [[JOY_F2], 0x10],
    [[JOY_D], 0x00], [[JOY_R, JOY_U], 0x06], [[], 0x00],
  ]],
  ["3 DIRECTIONAL CONTROL", 8, [
    [[JOY_L], 0x01], [[JOY_R], 0x02], [[JOY_U], 0x04], [[JOY_D], 0x10],
    [[JOY_F1], 0x08], [[JOY_F2], 0x20],                 // «взять» в directional — бит 5, а не 4
    [[JOY_D, JOY_F2], 0x30], [[JOY_L, JOY_F1], 0x09], [[], 0x00],
  ]],
];
for (const [name, uim, cases] of JT) {
  console.log(`ДЖОЙСТИК, РЕЖИМ ${name} (user_input_method=${uim})`);
  for (const [jb, want] of cases) {
    const got = userInput(uim, [], jb);
    chk(got === want, `${(jb.map(b => JNAME.get(b)).join("+") || "покой").padEnd(12)} -> ${got.toString(2).padStart(6, "0")} (${show(got)}), ждём ${want.toString(2).padStart(6, "0")} (${show(want)})`);
  }
}
// ПАРАЛЛЕЛЬНО С КЛАВИАТУРОЙ: джойстик ничего не отменяет, биты только складываются.
console.log("ДЖОЙСТИК И КЛАВИАТУРА ОДНОВРЕМЕННО");
chk(userInput(0, ["Z"], [JOY_U]) === 0x05, "режим 1: клавиша Z + джойстик UP = влево+вперёд");
chk(userInput(0, ["Q"], [JOY_L]) === 0x09, "режим 1: клавиша Q + джойстик LEFT = влево+прыжок");
chk(userInput(4, ["<"], [JOY_F1]) === 0x09, "режим 2: стрелка влево + FIRE1 = влево+прыжок");
chk(userInput(8, ["0"], [JOY_L]) === 0x21, "режим 3: цифра 0 + джойстик LEFT = влево+взять(dir)");
chk(userInput(8, ["v"], [JOY_D]) === 0x10, "режим 3: стрелка вниз и DOWN дают один и тот же бит");
// КОНЕЦ ИГРЫ: ранний выход check_user_input идёт мимо джойстика (C = 0), иначе труп бы ходил.
wr(L.user_input_method, 0); wr(L.byte_5B23, 1); wr(L.byte_5B24, 0);
joy(JOY_L, JOY_F1); press([]); for (let f = 0; f < 3; f++) v06c.oneInterrupt(true);
cpu.iff = false; wr(SP + 1, PARK >> 8); wr(SP, PARK & 0xFF); cpu.sp = SP; cpu.pc = L.check_user_input;
for (let n = 0; n < 100000 && cpu.pc !== PARK; n++) cpu.instruction();
cpu.iff = true;
chk(rd(L.user_input) === 0x00, `конец игры: джойстик не читается (user_input=0x${rd(L.user_input).toString(16)})`);
wr(L.byte_5B23, 0);
// МУСОР НА ШИНЕ (порт 6 после замера покоя вдруг читается нулём): после нормировки «нажато всё»
// — игра была бы неуправляема. Проверка стоит на фронте vec_joy: биты 4 и 5 схема держит в
// единице, после xor с покоем там обязаны быть нули, иначе состояние считается пустым.
{ const _rd = io.input.bind(io); const save = io.input;
  io.input = p => ((p & 0xFF) === 0x06 ? 0x00 : _rd(p));
  chk(userInput(8, [], []) === 0x00, "порт 6 читается нулём при покое 0xFF (мусор) — считаем отпущенным");
  io.input = save; }

// РЯДЫ ZX: кнопка сведена к клавише '0' («0 START GAME» и «нажми любую клавишу»), направления
// в ряды НЕ лезут вовсе — иначе они цепляли бы клавиши меню и ложную паузу на ВК (ряд 0 Вектора).
console.log("ДЖОЙСТИК И РЯДЫ ZX");
const zxrows = () => [...Array(8)].map((_, r) => rd(L.vec_zxrows + r)).join(" ");
joy(); press([]); frames(4);
const rowsIdle = zxrows();
joy(JOY_F2); frames(4);
chk((rd(L.vec_zxrows + 4) & 1) === 0, "FIRE2 тоже прижимает '0' (кнопка = «любая клавиша»)");
chk((rd(L.vec_rptab + 0) & 1) === 1, "read_key(0) видит кнопку");
joy(); frames(4);
chk(zxrows() === rowsIdle, "кнопку отпустили — ряды ZX пересобраны, бит '0' вернулся");
chk((rd(L.vec_rptab + 0) & 1) === 0, "read_key(0) снова чист");
for (const b of [JOY_L, JOY_R, JOY_U, JOY_D]) {
  joy(b); frames(4);
  chk(zxrows() === rowsIdle, `${JNAME.get(b)} в ряды ZX не лезет (ни клавиш меню, ни ложной паузы на ВК)`);
}
joy(); press(["0"]); frames(4);
chk((rd(L.vec_zxrows + 4) & 1) === 0, "настоящая клавиша '0' работает по-прежнему");
press([]); frames(4);
chk(zxrows() === rowsIdle, "клавишу '0' отпустили — ряды вернулись");

// ЦЕНА vec_joy В ТАКТАХ (кадр покоя: ничего не нажато, ряды ZX не пересобирались).
{
  joy(); press([]); frames(4);
  cpu.iff = false; wr(SP + 1, PARK >> 8); wr(SP, PARK & 0xFF); cpu.sp = SP; cpu.pc = L.vec_joy;
  let cyc = 0, i8 = 0;
  for (let n = 0; n < 5000 && cpu.pc !== PARK; n++) { cpu.instruction(); cyc += cpu.vcycles; i8 += cpu.cpu_cycles; }
  cpu.iff = true;
  // ТАКТ ВЕКТОРА в модели vector06js = 4 на машинный цикл (ею же считает profile_vec.js и гейт
  // картинки), в скобках — «книжные» такты i8080. CALL стоит 24 (17) и в тело не входит.
  const CALL = 24, CALLI = 17;
  console.log(`ЦЕНА: vec_joy в кадре покоя ${cyc} + ${CALL} (call) = ${cyc + CALL} тактов Вектора ` +
              `(${i8} + ${CALLI} = ${i8 + CALLI} тактов i8080)`);
  // Бюджет 116: джойстик «П» нормирует чтение значением покоя (xor imm вместо cpl, +4 такта к
  // прежним 112 на порту 0x0E).
  chk(cyc + CALL <= 116, `цена vec_joy в ISR ${cyc + CALL} тактов Вектора за кадр (бюджет 116)`);
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
