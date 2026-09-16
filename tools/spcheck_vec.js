#!/usr/bin/env node
// ЗАМЕР ГЛУБИНЫ СТЕКА (§17.4 рецепта Knight Lore). Сколько байт под SP реально занимает
// игра — это и есть цена буфера, который надо зарезервировать под стеком при переезде
// переменных в нижний регион.
//
//   node tools/spcheck_vec.js <rom> <sld> <итераций> [inputs.txt] [комнаты|all]
//
// База стека берётся ИЗ ОБРАЗА: загрузчик на 0x0000 — `di` (0xF3) + `ld sp,imm` (0x31 lo hi),
// то есть стенд не держит адрес числом и переживает переезд раскладки.
//
// ЧТО СЧИТАЕТСЯ СТЕКОМ. У Alien 8 SP трижды уходит НЕ в стек:
//   * `ld sp,hl` в print_sprite — чтение спрайта через pop (SP в данных спрайта);
//   * `ld sp,hl` в нативных столбцовых процедурах — вывод через push (SP в видеопамяти);
//   * `ld sp,0x8000` в update_sprite_loop — ВРЕМЕННЫЙ стек, но у Alien 8 он с той же базы,
//     что и главный (у Knight Lore — `ld sp,seed_1`), поэтому одного буфера хватает обоим.
// Поэтому считаются только значения SP в окне (база-0x1000, база] — всё остальное к цене
// буфера отношения не имеет.
//
// ФАЗЫ: «загрузка/меню» (от сброса до входа в первую комнату — там же заставка, меню,
// выбор раскладки) и «игра». Печатаются обе: глубина меню бывает больше игровой.
//
// ГЕЙТ: код 1, если глубина дошла до зарезервированного под стеком буфера. Размер буфера
// берётся ИЗ ЛИСТИНГА: (база SP) - (потолок кода нижнего региона из ASSERT'а). A8SP_LIMIT=N
// задаёт его вручную.
// A8SP_TOP=k  — сколько самых глубоких точек печатать (по умолчанию 6).
// A8SP_LIVES=n — положить n жизней при входе в комнату. Нужно, чтобы сценарий гибели
//   дошёл до GAME OVER (иначе за 600 итераций жизни не кончаются, а экран «GAME OVER»
//   с разбором рейтинга — отдельная ветка вызовов). Стенд печатает, добрался ли до неё.
"use strict";
const fs = require("fs"), vm = require("vm"), cp = require("child_process");
const base = "/Users/boris/projects/vector06js";
const [ROM, SLD, NS, INPUTS, ROOMSA] = process.argv.slice(2);
const N = +NS || 300;
if (!ROM || !SLD) { console.error("нужно: <rom> <sld> <итераций> [inputs.txt] [комнаты|all]"); process.exit(2); }
let LIMIT = +(process.env.A8SP_LIMIT || 0);   // 0 = взять из сборки (см. ниже)
const TOPN = +(process.env.A8SP_TOP || 6);
const IRQDROP = !!process.env.A8_IRQDROP;

// ---- метки сборки ----
const L = {};
for (const l of fs.readFileSync(SLD, "latin1").split("\n")) {
  const p = l.split("|");
  if (p.length >= 8 && p[6] === "L") { const n = p[7].split(",")[1]; if (n && !(n in L)) L[n] = +p[5]; }
}
const IMAGE = new Uint8Array(fs.readFileSync(ROM)).subarray(0, 0x10000);
if (IMAGE[0] !== 0xF3 || IMAGE[1] !== 0x31) throw new Error("загрузчик на 0x0000 не `di / ld sp,imm` — база стека не читается");
const SPBASE = IMAGE[2] | (IMAGE[3] << 8);
const WINDOW = 0x1000;   // ниже этого SP уже не стек, а данные спрайта / видеопамять

const lst = fs.readFileSync(ROM.replace(/\.r0m$/, ".lst"), "latin1").split("\n");
let SYNC = -1;
for (const l of lst) { const m = l.match(/^\s*\d+\+?\s+([0-9A-F]{4})\s.*\s+call\s+init_start_location/); if (m) { SYNC = parseInt(m[1], 16); break; } }
if (SYNC < 0) throw new Error("не нашёл call init_start_location в листинге");
// ЗАРЕЗЕРВИРОВАННЫЙ БУФЕР — ИЗ СБОРКИ, а не числом: это (база SP) - (потолок кода нижнего
// региона), то есть ровно то место, куда стеку можно расти, не сев на код.
if (!LIMIT) {
  // ЛОВУШКА: листинг выше прочитан как latin1 (так адреса разбираются проще), и комментарий
  // по-русски в нём — мусор. Для поиска по тексту читаем его отдельно как utf8.
  for (const l of fs.readFileSync(ROM.replace(/\.r0m$/, ".lst"), "utf8").split("\n")) {
    const m = l.match(/ASSERT \$ <= (0x[0-9a-fA-F]+)\s*;\s*нижний регион не должен дорасти до стека/);
    if (m) { LIMIT = SPBASE - parseInt(m[1], 16); break; }
  }
  if (!LIMIT) console.log("предупреждение: в листинге нет ASSERT'а потолка кода — гейт по глубине выключен");
}
const LABS = Object.entries(L).filter(([, a]) => a >= 0x40).sort((a, b) => a[1] - b[1]);
function nameOf(pc) {
  let lo = 0, hi = LABS.length - 1, r = null;
  while (lo <= hi) { const m = (lo + hi) >> 1; if (LABS[m][1] <= pc) { r = LABS[m]; lo = m + 1; } else hi = m - 1; }
  return r ? `${r[0]}+0x${(pc - r[1]).toString(16)}` : "?";
}

// ---- эмулятор ----
const g = {}; g.window = g; g.document = { createElement: () => fc(), getElementById: () => fc() };
function fcx() { return { createImageData: () => ({ data: new Uint8ClampedArray(4) }), putImageData: () => {}, getImageData: () => ({ data: new Uint8ClampedArray(4) }), fillRect() {}, drawImage() {} }; }
function fc() { return { width: 0, height: 0, style: {}, getContext: () => fcx() }; }
g.requestAnimationFrame = () => 0; g.setTimeout = () => 0; g.print = () => 0;
g.console = { log() {}, debug() {}, warn() {}, error() {}, info() {} };
const ctx = vm.createContext(g);
for (const f of ["i8080-js/i8080_trace.js", "i8080-js/i8080_disasm.js", "i8080-js/i8080.js", "src/fili.js", "src/ay.js", "src/fd1793.js", "src/fddimage.js", "src/i8253.js", "src/io.js", "src/keyboard.js", "src/memory.js", "src/sound.js", "src/tv.js"])
  vm.runInContext(fs.readFileSync(base + "/" + f, "utf8"), ctx, { filename: f });

const inputs = {};
if (INPUTS && fs.existsSync(INPUTS)) for (const l of fs.readFileSync(INPUTS, "utf8").split("\n")) {
  const m = l.trim().match(/^(\d+)\s+(\S+)\s+(down|up)/i);
  if (m) (inputs[+m[1] + 1] = inputs[+m[1] + 1] || []).push([m[2].toLowerCase(), m[3].toLowerCase() === "down"]);
}

// ---- один прогон ----
function run(room) {
  const memory = new ctx.Memory(), keyboard = new ctx.Keyboard(), timer = new ctx.I8253(), ay = new ctx.AY(),
        floppy = new (ctx.Floppy().FD1793)(), io = new ctx.IO(keyboard, timer, memory, ay, floppy);
  { const _rd = io.input.bind(io); io.input = p => ((p & 0xFF) === 0x0E ? 0xFF : _rd(p)); }   // джойстик: покой
  const cpu = new ctx.I8080(memory, io), tape = { advance: () => {}, sample: 0, reset: () => {} },
        v06c = new ctx.Vector06c(cpu, memory, io, ay, tape);
  v06c.bmp = new Uint32Array(576 * 288); v06c.displayFrame = () => {}; v06c.check_breakpoint = () => false; v06c.dbg = null;
  memory.init_from_array(IMAGE, 0); memory.detach_boot && memory.detach_boot();
  cpu.pc = 0; cpu.sp = SPBASE; cpu.iff = false;
  const rd = a => memory.bytes[memory.tobank(a & 0xffff)];
  const ow = memory.write.bind(memory), poke = (a, v) => ow(a & 0xffff, v & 0xff, false);
  // seed_3 += mem[seed_2]: гасим, иначе сценарий зависит от того, какой код лежит по
  // адресу-счётчику, и замер не воспроизводится между раскладками.
  if (!process.env.A8NOGAG) {
    const s3 = L.seed_3 & 0xff, s3h = (L.seed_3 >> 8) & 0xff;
    const pat = [0x3A, s3, s3h, 0x86, 0x85, 0x84, 0x32, s3, s3h]; let at = -1;
    for (let a = 0x100; a < 0xF000 && at < 0; a++) { let ok = true; for (let i = 0; i < pat.length; i++) if (rd(a + i) !== pat[i]) { ok = false; break; } if (ok) at = a; }
    if (at < 0) throw new Error("не нашёл seed_3 += mem[seed_2]");
    ow(at + 3, 0x00, false);
  }
  // ввод — через МАТРИЦУ ЖЕЛЕЗА: vec_scan не заглушается, чтобы стек ISR был настоящим
  const VKEYS = { z: [7, 0x04], x: [7, 0x01], a: [4, 0x02], q: [6, 0x02], "0": [2, 0x01], space: [7, 0x80], enter: [3, 0x10] };
  const key = (k, down) => { const v = VKEYS[k]; if (!v) return; const [r, b] = v; if (down) keyboard.matrix[r] |= b; else keyboard.matrix[r] &= ~b; };

  let phase = "menu", iter = 0;
  // ЗАМЕР: минимум SP в окне (SPBASE-WINDOW, SPBASE], раздельно по фазам
  const deep = { menu: { min: SPBASE, pc: 0 }, game: { min: SPBASE, pc: 0 } };
  const hist = new Map();   // глубина -> сколько раз (по фазе игры)
  const spots = new Map();  // PC -> максимальная достигнутая там глубина
  const seen = {};   // побывали ли в ключевых экранах (game_over, display_menu, lose_life)
  const WATCH = {}; for (const n of ["game_over", "display_menu", "lose_life", "start_menu"]) if (L[n] !== undefined) WATCH[L[n]] = n;
  const _instr = cpu.instruction.bind(cpu);
  cpu.instruction = function () {
    const r = _instr();
    const w = WATCH[cpu.pc]; if (w) seen[w] = (seen[w] || 0) + 1;
    const sp = cpu.sp;
    if (sp <= SPBASE && sp > SPBASE - WINDOW) {
      const d = deep[phase === "game" ? "game" : "menu"];
      if (sp < d.min) { d.min = sp; d.pc = cpu.pc; }
      const dep = SPBASE - sp;
      if (phase === "game") hist.set(dep, (hist.get(dep) || 0) + 1);
      const s = spots.get(cpu.pc) || 0; if (dep > s) spots.set(cpu.pc, dep);
    }
    return r;
  };

  memory.write = function (a, w, s) {
    a &= 0xffff;
    if (phase === "menu" && cpu.pc === SYNC) {
      poke(L.seed_1, 0x34); poke(L.seed_1 + 1, 0x12); poke(L.seed_2, 0x78); poke(L.seed_2 + 1, 0x56); poke(L.seed_3, 0x9A);
      phase = "init";
    }
    if (room && phase === "init" && (a === L.graphic_objs_tbl + 8 || a === L.graphic_objs_tbl + 40)) w = room;
    if (a === L.curr_room_attrib && phase === "init" && w !== 0) {
      phase = "game"; key("0", false);
      if (process.env.A8SP_LIVES && L.lives !== undefined) poke(L.lives, +process.env.A8SP_LIVES);
    }
    if (a === L.seed_2 + 1 && phase === "game") { iter++; for (const [k, d] of (inputs[iter] || [])) key(k, d); }
    return ow(a, w, s);
  };
  for (let f = 0; f < 60; f++) v06c.oneInterrupt(true);
  key("0", true);
  let guard = 0; while (phase !== "game" && guard++ < 3000) v06c.oneInterrupt(true);
  if (phase !== "game") throw new Error(`комната ${room || "стартовая"}: не дошли до комнаты`);
  const startIter = iter; let steps = 0, frc = 0, tacc = 0;
  while (iter - startIter < N && steps < 3e8) {
    if (frc >= 59904) { frc -= 59904; if (!(IRQDROP && !cpu.iff)) { v06c.irq = true; v06c.checkInterrupt(); } }
    const c = (cpu.instruction(), cpu.vcycles);
    steps++; frc += c; tacc += c;
    if (tacc > 1) { const tn = tacc >> 1; tacc -= tn * 2; timer.Count(tn); }
    if (cpu.last_opcode === 0xd3) io.commit();
  }
  return { iters: iter - startIter, deep, hist, spots, seen };
}

// ---- комнаты ----
let rooms = [0];
if (ROOMSA === "all") rooms = cp.execFileSync("python3", ["tools/a8_rooms.py"], { encoding: "utf8" }).trim().split(/\s+/).map(Number);
else if (ROOMSA) rooms = ROOMSA.trim().split(/[\s,]+/).map(Number);

console.log(`ГЛУБИНА СТЕКА: база SP = 0x${SPBASE.toString(16)} (из загрузчика), комнат ${rooms.length}, ` +
            `${N} итераций, сценарий ${INPUTS ? INPUTS.replace(/.*\//, "") : "покой"}`);
let dMenu = 0, dGame = 0, pcMenu = 0, pcGame = 0, roomMenu = 0, roomGame = 0;
const HIST = new Map(), SPOTS = new Map(), SEEN = {};
for (const room of rooms) {
  const r = run(room);
  const dm = SPBASE - r.deep.menu.min, dg = SPBASE - r.deep.game.min;
  if (dm > dMenu) { dMenu = dm; pcMenu = r.deep.menu.pc; roomMenu = room; }
  if (dg > dGame) { dGame = dg; pcGame = r.deep.game.pc; roomGame = room; }
  for (const [k, n] of r.hist) HIST.set(k, (HIST.get(k) || 0) + n);
  for (const [pc, d] of r.spots) { const s = SPOTS.get(pc) || 0; if (d > s) SPOTS.set(pc, d); }
  for (const k in r.seen) SEEN[k] = (SEEN[k] || 0) + r.seen[k];
  if (rooms.length > 1 && (dm > 0 || dg > 0))
    console.log(`  комната ${room}: меню ${dm} Б, игра ${dg} Б`);
}
console.log(`загрузка/меню: ${dMenu} Б (0x${(SPBASE - dMenu).toString(16)}), глубже всего на pc=${pcMenu.toString(16)} (${nameOf(pcMenu)})${rooms.length > 1 ? `, комната ${roomMenu}` : ""}`);
console.log(`игра:          ${dGame} Б (0x${(SPBASE - dGame).toString(16)}), глубже всего на pc=${pcGame.toString(16)} (${nameOf(pcGame)})${rooms.length > 1 ? `, комната ${roomGame}` : ""}`);
console.log("побывали: " + (Object.keys(SEEN).length ? Object.entries(SEEN).map(([k, n]) => `${k} x${n}`).join(", ") : "— (ни меню, ни гибели, ни GAME OVER)"));
const DEEP = Math.max(dMenu, dGame);
console.log(`ИТОГ: максимальная глубина ${DEEP} Б`);
console.log("самые глубокие точки (PC -> глубина):");
for (const [pc, d] of [...SPOTS.entries()].sort((a, b) => b[1] - a[1]).slice(0, TOPN))
  console.log(`  ${d.toString().padStart(4)} Б  ${pc.toString(16)} (${nameOf(pc)})`);
{
  const ks = [...HIST.keys()].sort((a, b) => b - a).slice(0, 8);
  console.log("хвост распределения глубины в игре: " + ks.map(k => `${k} Б x${HIST.get(k)}`).join(", "));
}
if (LIMIT) {
  if (DEEP >= LIMIT) { console.log(`КРАСНЫЙ: глубина ${DEEP} Б дошла до зарезервированных ${LIMIT} Б`); process.exit(1); }
  console.log(`ЗЕЛЁНЫЙ: ${DEEP} Б из ${LIMIT} зарезервированных (запас ${LIMIT - DEEP} Б)`);
}
