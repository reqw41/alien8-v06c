#!/usr/bin/env node
// ГЕЙТ ПЛОСКОСТИ 2: в 0xC000-0xC7FF не должно попасть НИ ОДНОЙ записи.
//
// До этого захода страницы 0xC0..0xC7 были «защитной зоной»: туда сваливались мусорные
// атрибуты ZX (zxaram) и вылет печати за столбец 31 (в линейном буфере ZX он заворачивался
// в левый край следующей строки, в столбцовом буфере Вектора уходит за плоскость 1).
// Атрибуты вырезаны (a8_cut_attrs), печать обрезана (ps_cw в tools/a8_vec.py) — и теперь
// зона обязана быть МЁРТВОЙ: под цветной HUD плоскость 2 (0xC000-0xDFFF) нужна целиком под
// селектор белого, и любой байт, упавший в строки 32..223 её столбцов, побелит точку поля.
//
//   node tools/spillcheck_vec.js <rom> <sld> <итераций> [inputs.txt] [комнаты|all]
//
// Комнаты: «all» — все 128 из tools/a8_rooms.py (каждая своим прогоном, ~1 с на комнату),
// «48 137 39» — только эти, пусто — стартовая. Диапазон задаётся A8SPILL=lo-hi (шестнадцатеричн.,
// по умолчанию C000-C7FF). Печатает число записей и ТОП ПИСАТЕЛЕЙ по PC; код возврата 1,
// если запись была хоть одна.
//
// Почему PC, а не просто счётчик: писателей ровно два класса — цепочки print_sprite и заливка
// fill_window, и по PC сразу видно, чей клип отвалился.
//
// A8PSMAX=1 — ЗАПАС ДО КРАЯ: самый правый столбец, который печать заняла бы без клипа.
// A8PSSP=1  — ИНВАРИАНТ ЧТЕНИЯ СПРАЙТА: SP к метке ps_done обязан уйти ровно на длину
//             прочитанных строк. Смотреть его имеет смысл на сборке A8_PSCW=test (край
//             объявлен столбцом 30): в игре клип не срабатывает ни разу, и на обычной
//             сборке этот инвариант держится сам собой, ничего не доказывая. ЗАМЕРЕНО:
//             порча «не двигать SP за непрочитанный хвост» краснеет на A8_PSCW=test и
//             ПРОХОДИТ на обычной сборке — ровно поэтому test-сборка и нужна.
"use strict";
const fs = require("fs"), vm = require("vm"), cp = require("child_process");
const base = "/Users/boris/projects/vector06js";
const [ROM, SLD, NS, INPUTS, ROOMSA] = process.argv.slice(2);
const N = +NS || 300;
if (!ROM || !SLD) { console.error("нужно: <rom> <sld> <итераций> [inputs.txt] [комнаты|all]"); process.exit(2); }
const RANGE = (process.env.A8SPILL || "C000-C7FF").split("-").map(x => parseInt(x, 16));
const [LO, HI] = RANGE;

// ---- метки сборки ----
const L = {};
for (const l of fs.readFileSync(SLD, "latin1").split("\n")) {
  const p = l.split("|");
  if (p.length >= 8 && p[6] === "L") { const n = p[7].split(",")[1]; if (n && !(n in L)) L[n] = +p[5]; }
}
const lst = fs.readFileSync(ROM.replace(/\.r0m$/, ".lst"), "latin1").split("\n");
let SYNC = -1;
for (const l of lst) { const m = l.match(/^\s*\d+\+?\s+([0-9A-F]{4})\s.*\s+call\s+init_start_location/); if (m) { SYNC = parseInt(m[1], 16); break; } }
if (SYNC < 0) throw new Error("не нашёл call init_start_location в листинге");
// PC -> ближайшая метка сверху (для читаемого отчёта)
const LABS = Object.entries(L).filter(([, a]) => a >= 0x100).sort((a, b) => a[1] - b[1]);
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
const IMAGE = new Uint8Array(fs.readFileSync(ROM)).subarray(0, 0x10000);
const IRQDROP = !!process.env.A8_IRQDROP;

const inputs = {};
if (INPUTS && fs.existsSync(INPUTS)) for (const l of fs.readFileSync(INPUTS, "utf8").split("\n")) {
  const m = l.trim().match(/^(\d+)\s+(\S+)\s+(down|up)/i);
  if (m) (inputs[+m[1] + 1] = inputs[+m[1] + 1] || []).push([m[2].toLowerCase(), m[3].toLowerCase() === "down"]);
}

// ---- один прогон (своя машина на комнату: сброс состояния надёжнее доигрывания) ----
function run(room) {
  const memory = new ctx.Memory(), keyboard = new ctx.Keyboard(), timer = new ctx.I8253(), ay = new ctx.AY(),
        floppy = new (ctx.Floppy().FD1793)(), io = new ctx.IO(keyboard, timer, memory, ay, floppy);
  { const _rd = io.input.bind(io); io.input = p => ((p & 0xFF) === 0x0E ? 0xFF : _rd(p)); }   // джойстик: покой
  const cpu = new ctx.I8080(memory, io), tape = { advance: () => {}, sample: 0, reset: () => {} },
        v06c = new ctx.Vector06c(cpu, memory, io, ay, tape);
  v06c.bmp = new Uint32Array(576 * 288); v06c.displayFrame = () => {}; v06c.check_breakpoint = () => false; v06c.dbg = null;
  memory.init_from_array(IMAGE, 0); memory.detach_boot && memory.detach_boot();
  cpu.pc = 0; cpu.sp = 0x8000; cpu.iff = false;
  const rd = a => memory.bytes[memory.tobank(a & 0xffff)];
  const ow = memory.write.bind(memory), poke = (a, v) => ow(a & 0xffff, v & 0xff, false);
  // seed_3 += mem[seed_2]: гасим подмешивание байта памяти — иначе вердикт гейта зависит от
  // того, какой код лежит по адресу-счётчику, и «0 записей» перестаёт быть воспроизводимым.
  if (!process.env.A8NOGAG) {
    const s3 = L.seed_3 & 0xff, s3h = (L.seed_3 >> 8) & 0xff;
    const pat = [0x3A, s3, s3h, 0x86, 0x85, 0x84, 0x32, s3, s3h]; let at = -1;
    for (let a = 0x100; a < 0xF000 && at < 0; a++) { let ok = true; for (let i = 0; i < pat.length; i++) if (rd(a + i) !== pat[i]) { ok = false; break; } if (ok) at = a; }
    if (at < 0) throw new Error("не нашёл seed_3 += mem[seed_2]");
    ow(at + 3, 0x00, false);
  }
  // ввод: ряды ZX и матрица Вектора кладутся прямо в ячейки (независимо от тактов)
  const KEYS = { z: [0, 1], x: [0, 2], a: [1, 0], q: [2, 0], "0": [4, 0], space: [7, 0] };
  const VKEYS = { z: [7, 0x04], x: [7, 0x01], a: [4, 0x02], q: [6, 0x02], "0": [2, 0x01], space: [7, 0x80] };
  const rows = new Uint8Array(8).fill(0xFF), kbm = new Uint8Array(8);
  ow(L.vec_zxbuild, 0xC9, false); for (let r = 0; r < 8; r++) ow(L.vec_zxrows + r, 0xFF, false);
  ow(L.vec_scan, 0xC9, false);    for (let r = 0; r < 8; r++) ow(L.vec_kbmat + r, 0, false);
  const key = (k, down) => {
    const [vr, vb] = VKEYS[k]; if (down) kbm[vr] |= vb; else kbm[vr] &= ~vb; poke(L.vec_kbmat + vr, kbm[vr]);
    const [r, b] = KEYS[k]; if (down) rows[r] &= ~(1 << b); else rows[r] |= (1 << b); poke(L.vec_zxrows + r, rows[r]);
  };
  let phase = "menu", iter = 0, hits = 0; const byPC = new Map(); const first = [];
  // A8PSMAX=1 — ЗАПАС ДО КРАЯ: самый правый столбец, который печать заняла бы БЕЗ клипа.
  // Снимается на патче `ld (ps_end+1),a` (ровно один на вызов print_sprite): к этому моменту
  // B = страница столбца в буфере, а в иммедиате loc_D10F+1 уже лежит w-1 (ширина до клипа).
  const PSMAX = !!process.env.A8PSMAX; let psmax = -1, psn = 0; const psHist = new Map();
  // A8PSSP=1 — ИНВАРИАНТ ЧТЕНИЯ СПРАЙТА: цепочка читает данные ЧЕРЕЗ SP, и обрезанная по
  // столбцу 31 цепочка не дочитывает 2*(w-w') байт строки — за них SP двигает ps_fix. Проверка:
  // к метке ps_done (SP ещё в данных спрайта) SP обязан уйти ровно на 2*K*h от точки входа,
  // где K = w для выровненного пути и w-1 для сдвинутого, w — ширина ДО клипа из (ix+24),
  // h — высота окна. Ломается ровно тогда, когда ломается компенсация ps_fix; в игре клип не
  // срабатывает, поэтому смотреть этот инвариант имеет смысл на сборке A8_PSCW=test.
  const PSSP = !!process.env.A8PSSP; let spBad = 0, spN = 0, spWant = -1; const spFirst = [];
  memory.write = function (a, w, s) {
    a &= 0xffff;
    if ((PSMAX || PSSP) && a === L.ps_end + 1) {
      const right = (cpu.regs[0] - (L.vidbuf >> 8)) + rd(L.loc_D10F + 1);
      psn++; psHist.set(right, (psHist.get(right) || 0) + 1);
      if (right > psmax) psmax = right;
      if (PSSP) {
        const ix = rd(L.z80_ix) | (rd(L.z80_ix + 1) << 8);
        const wid = rd(ix + 24), h = (w - cpu.regs[1]) & 0xFF;
        const de = (cpu.regs[2] << 8) | cpu.regs[3];
        const K = (rd(L.a8_psx) & 7) ? wid - 1 : wid;   // сдвинутый путь читает на столбец меньше
        // ХВОСТ ПОСЛЕДНЕЙ СТРОКИ НЕ ДОСЫЛАЕТСЯ И НЕ ДОЛЖЕН: ps_fix висит на переходе К
        // СЛЕДУЮЩЕЙ строке (ps_jrow), то есть срабатывает h-1 раз. После цикла SP всё равно
        // возвращается из tmp_SP, а DE цело — недочитанные 2*(w-w') последней строки никому
        // не мешают. Зато если компенсация отвалится совсем, недобор будет в (h-1) раз больше.
        spWant = (de + 2 * (K * h - (wid - (rd(L.loc_D10F + 1) + 1)))) & 0xFFFF;
      }
    }
    if (a >= LO && a <= HI) {
      hits++; byPC.set(cpu.pc, (byPC.get(cpu.pc) || 0) + 1);
      if (first.length < 8) first.push({ iter, pc: cpu.pc, a, w });
    }
    if (phase === "menu" && cpu.pc === SYNC) {
      poke(L.seed_1, 0x34); poke(L.seed_1 + 1, 0x12); poke(L.seed_2, 0x78); poke(L.seed_2 + 1, 0x56); poke(L.seed_3, 0x9A);
      phase = "init";
    }
    if (room && phase === "init" && (a === L.graphic_objs_tbl + 8 || a === L.graphic_objs_tbl + 40)) w = room;
    if (a === L.curr_room_attrib && phase === "init" && w !== 0) { phase = "game"; key("0", false); }
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
    if (PSSP && cpu.pc === L.ps_done && spWant >= 0) {
      spN++;
      if (cpu.sp !== spWant) { spBad++; if (spFirst.length < 6) spFirst.push({ iter, sp: cpu.sp, want: spWant }); }
      spWant = -1;
    }
    steps++; frc += c; tacc += c;
    if (tacc > 1) { const tn = tacc >> 1; tacc -= tn * 2; timer.Count(tn); }
    if (cpu.last_opcode === 0xd3) io.commit();
  }
  return { iters: iter - startIter, hits, byPC, first, psmax, psn, psHist, spBad, spN, spFirst };
}

// ---- комнаты ----
let rooms = [0];
if (ROOMSA === "all") rooms = cp.execFileSync("python3", ["tools/a8_rooms.py"], { encoding: "utf8" }).trim().split(/\s+/).map(Number);
else if (ROOMSA) rooms = ROOMSA.trim().split(/[\s,]+/).map(Number);

console.log(`ГЕЙТ ПЛОСКОСТИ 2: диапазон ${LO.toString(16)}-${HI.toString(16)}, комнат ${rooms.length}, ` +
            `${N} итераций, сценарий ${INPUTS ? INPUTS.replace(/.*\//, "") : "покой"}`);
let total = 0, badRooms = 0; const allPC = new Map(); let PSMAX = -1, PSN = 0; const PSH = new Map();
let SPN = 0, SPBAD = 0; const SPSHOW = [];
for (const room of rooms) {
  const r = run(room);
  total += r.hits;
  for (const [pc, n] of r.byPC) allPC.set(pc, (allPC.get(pc) || 0) + n);
  if (r.psmax > PSMAX) PSMAX = r.psmax;
  PSN += r.psn; for (const [k, n] of r.psHist) PSH.set(k, (PSH.get(k) || 0) + n);
  SPN += r.spN; SPBAD += r.spBad;
  if (r.spBad && SPSHOW.length < 6) for (const f of r.spFirst) SPSHOW.push(`комната ${room || "стартовая"} итерация ${f.iter}: SP ${f.sp.toString(16)}, ждали ${f.want.toString(16)}`);
  if (r.hits) {
    badRooms++;
    console.log(`  комната ${room || "стартовая"}: ЗАПИСЕЙ ${r.hits} за ${r.iters} итераций`);
    for (const f of r.first)
      console.log(`    итерация ${f.iter} pc=${f.pc.toString(16)} (${nameOf(f.pc)}) ${f.a.toString(16)} <- ${f.w.toString(16)}`);
  }
}
if (PSN) {
  console.log(`ЗАПАС ДО КРАЯ: печатей ${PSN}, самый правый занятый столбец ${PSMAX} (край буфера — 31)`);
  console.log("  хвост распределения: " + [...PSH.entries()].sort((a, b) => b[0] - a[0]).slice(0, 6)
    .map(([c, n]) => `столбец ${c} x${n}`).join(", "));
}
if (process.env.A8PSSP) {
  console.log(`ЧТЕНИЕ СПРАЙТА ЧЕРЕЗ SP: печатей проверено ${SPN}, SP разошёлся с 2*w*h на ${SPBAD}`);
  for (const l of SPSHOW) console.log("  " + l);
  if (SPBAD) { console.log("КРАСНЫЙ: цепочка прочитала не ту длину строки — компенсация ps_fix сломана"); process.exit(1); }
  if (!SPN) { console.log("ПУСТАЯ ВЫБОРКА: печатей не было"); process.exit(1); }
}
if (total) {
  console.log("писатели (PC x записей):");
  for (const [pc, n] of [...allPC.entries()].sort((a, b) => b[1] - a[1]).slice(0, 12))
    console.log(`  ${pc.toString(16)} (${nameOf(pc)}) x${n}`);
  console.log(`КРАСНЫЙ: ${total} записей в ${LO.toString(16)}-${HI.toString(16)} из ${rooms.length} комнат (красных ${badRooms})`);
  process.exit(1);
}
console.log(`ЗЕЛЁНЫЙ: ${rooms.length} комнат по ${N} итераций — ни одной записи в ${LO.toString(16)}-${HI.toString(16)}`);
