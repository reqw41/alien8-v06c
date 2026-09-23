#!/usr/bin/env node
// Гейт МЕЛОДИЙ против данных: все шесть мелодий из src/msx_tunes_vi53.bin проигрываются
// плеером Вектора, а по кадрам сверяется эффективный делитель каждого счётчика ВИ53.
//
//   node tools/tunecheck_vec.js build/alien8_vec.r0m build/alien8_vec.sld
//
// Эталон — decode() из tools/a8_tune_c64.py на блобе из каталога (данные, не модель MSX):
// голос A -> счётчик 1 (порт 0x0A), голос B -> счётчик 2 (порт 0x09), голос C пуст.
// Семантика Вектора: управляющее слово БЕЗ делителя (0x76/0xB6) останавливает счётчик =
// тишина (делитель 0 в эталоне); запись LSB+MSB загружает делитель (режим 3, меандр).
// Плеер обязан играть РОВНО «длину в кадрах» из каталога и потом заглушить счётчики 1,2;
// счётчик 0 (секундомер бюджета di, порт 0x0B) плеер трогать не должен — любое обращение
// к 0x0B или управляющие слова счётчика 0 (0x36/0x30) в мелодию = провал.
// Мелодии в игре блокирующие (как на MSX): стенд вызывает play_audio с DE = msx_hdr_*
// (адрес байта каталога) и меткой возврата в стеке — ровно так, как зовёт игра.
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
for (const t of ["play_audio", "msx_tunenum"]) if (L[t] === undefined) { console.log("нет метки " + t); process.exit(2); }

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
// джойстик порта 0x0E в vector06js собирается из матрицы — в стенде не нужен (покой)
{ const _rd = io.input.bind(io); io.input = p => ((p & 0xFF) === 0x0E ? 0xFF : _rd(p)); }
const cpu = new ctx.I8080(memory, io), tape = { advance: () => {}, sample: 0, reset: () => {} },
      v06c = new ctx.Vector06c(cpu, memory, io, ay, tape);
v06c.bmp = new Uint32Array(576 * 288); v06c.displayFrame = () => {}; v06c.check_breakpoint = () => false; v06c.dbg = null;
// БАЗА СТЕКА — ИЗ ОБРАЗА (загрузчик 0x0000: `di` + `ld sp,imm`)
const IMG = new Uint8Array(fs.readFileSync(ROM)).subarray(0, 0x10000);
if (IMG[0] !== 0xF3 || IMG[1] !== 0x31) throw new Error("загрузчик не `di / ld sp,imm` — база стека не читается");
const SPBASE = IMG[2] | (IMG[3] << 8);
memory.init_from_array(IMG, 0);
memory.detach_boot && memory.detach_boot();
cpu.pc = 0; cpu.sp = SPBASE; cpu.iff = false;
if (L.vkbd !== undefined) for (let r = 0; r < 8; r++) memory.write(L.vkbd + r, 0xFF, false);

// ---- тап на порты ВИ53: (порт, значение) в порядке исполнения ----
let taps = [];
{ const _wr = io.output.bind(io);
  io.output = (p, v) => { if ((p & 0xFF) >= 0x08 && (p & 0xFF) <= 0x0B) taps.push(p & 0xFF, v); return _wr(p, v); }; }
// eff[счётчик] — делитель после всех записей кадра; 0 = молчит. applyTaps — как c64tune_vec.js
const eff = [0, 0, 0], rx = [0, 0, 0], pend = [0, 0, 0];
function applyTaps() {
  for (let i = 0; i < taps.length; i += 2) {
    const p = taps[i], v = taps[i + 1];
    if (p === 0x08) {
      const c = v >> 6;
      if ((v & 0x30) !== 0) { eff[c] = 0; rx[c] = 0; pend[c] = 0; } // управляющее без делителя = стоп
    } else {
      const c = 0x0B - p;
      if (rx[c] === 0) { pend[c] = v; rx[c] = 1; }
      else { eff[c] = ((v << 8) | pend[c]) & 0xFFFF; rx[c] = 0; }
    }
  }
}

// ---- эталон: decode() блоба из каталога (данные), кадры x [c1, c2] ----
const REF = JSON.parse(cp.execFileSync("python3", ["-c", `
import sys, json, struct
sys.path.insert(0, "tools")
import a8_tune_c64 as T
d = open("src/msx_tunes_vi53.bin", "rb").read()
n = struct.unpack_from("<H", d, 0)[0]
out = {}
for i in range(n):
    off, fr = struct.unpack_from("<HH", d, 2 + 4 * i)
    end = struct.unpack_from("<H", d, 2 + 4 * (i + 1))[0] if i + 1 < n else len(d)
    rows = T.decode(d[off:end], fr)
    assert len(rows) == fr
    out[str(i)] = [[r[0], r[1]] for r in rows]
print(json.dumps(out))
`], { encoding: "utf8" }));

const SENT = 0x0038;   // метка возврата: RST 38h (в игру не попадём — ловим PC)
// --- довести игру до комнаты (как остальные гейты): vec_isr работает по таблицам ---
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

let bad = 0, lost = 0;
for (let ti = 0; ti < TUNES.length; ti++) {
  const nm = TUNES[ti], ref = REF[String(ti)];
  cpu.sp = SPBASE;
  ow(L.msx_play, 0, false); ow(L.msx_tunenum, 0xFF, false);   // перехват: заряд определяем по записи 1
  cpu.memory_write_word(cpu.sp - 2, SENT, true); cpu.sp -= 2;
  cpu.set_rp(2, L["msx_hdr_" + nm]);      // DE = адрес байта каталога
  cpu.pc = L.play_audio;
  let frames = 0, frc = 0, tacc = 0, steps = 0;
  const seq = [];                          // eff[1],eff[2] по кадрам начиная с первого тика
  let started = false, c0bad = 0;
  while (cpu.pc !== SENT && steps < 2e8) {
    if (frc >= 59904) {
      frc -= 59904;
      if (started) {
        applyTaps(); seq.push([eff[1], eff[2]]);
        // счётчик 0 легально трогают: vec_isr (перезарядка 0xFFFF каждый кадр), vec_boot
        // (слово режима 0x30 один раз), vec_cu (команда защёлки 0x00 на 0x08) и vcu_lost
        // (перезарядка секундомера любыми байтами в 0x0B — только в кадре с защёлкой).
        // Плеер не имеет права писать в счётчик 0 ничего: его баг c=0 даёт слово 0x36
        // на 0x08 и байты делителя в 0x0B в кадре БЕЗ защёлки vec_cu.
        let latched = false;
        for (let i = 0; i < taps.length; i += 2)
          if (taps[i] === 0x08 && taps[i + 1] === 0x00) latched = true;
        for (let i = 0; i < taps.length; i += 2) {
          const p = taps[i], v = taps[i + 1];
          if (p === 0x0B && v !== 0xFF && !latched) c0bad++;
          if (p === 0x08 && (v >> 6) === 0 && v !== 0x30 && v !== 0x00) c0bad++;
        }
      }
      taps = [];
      frames++;
      if (!cpu.iff) lost++;
      v06c.irq = true; v06c.checkInterrupt();
    }
    const c = (cpu.instruction(), cpu.vcycles);
    steps++; frc += c; tacc += c;
    if (tacc > 1) { const tn = tacc >> 1; tacc -= tn * 2; timer.Count(tn); }
    if (cpu.last_opcode === 0xd3) io.commit();
    if (!started && memory.read(L.msx_tunenum, false) === ti && memory.read(L.msx_play, false) === 1) {
      // кадр заряда: счётчики заглушены, сравнение начинается со следующего кадра
      started = true; eff[1] = eff[2] = 0; rx[1] = rx[2] = pend[1] = pend[2] = 0;
    }
  }
  if (cpu.pc !== SENT) { console.log(`${nm}: НЕ ВЕРНУЛАСЬ за ${steps} инструкций`); bad++; continue; }
  if (memory.read(L.msx_tunenum, false) !== ti) { console.log(`${nm}: msx_tunenum = ${memory.read(L.msx_tunenum, false)}`); bad++; continue; }
  // 1) длина: ровно «кадров» тиков из каталога (допуск 1 кадр фазы входа — как старый гейт)
  const dlen = frames - ref.length;
  if (Math.abs(dlen) > 1) { console.log(`${nm}: кадров ${frames}, в каталоге ${ref.length}, расхождение ${dlen}`); bad++; continue; }
  // 2) делители по кадрам против decode() блоба
  let mism = 0, shown = 0, phase = 0;
  for (let i = 0; i < ref.length; i++) {
    const a = seq[i + 1] || [0, 0], b = seq[i + 2] || [0, 0], r = ref[i];   // сдвиг фазы 1 или 2
    if (i === 0) {
      if (a[0] === r[0] && a[1] === r[1]) phase = 1;
      else if (b[0] === r[0] && b[1] === r[1]) phase = 2;
      else { console.log(`${nm}: кадр 0 не совпал ни с какой фазой: seq=${a}/${b} ref=${r}`); bad++; shown = 9; break; }
    }
    const got = (phase === 1 ? a : b);
    if (got[0] !== r[0] || got[1] !== r[1]) {
      mism++;
      if (shown < 3) { shown++; console.log(`  ${nm} кадр ${i}: счётчики ${got.join(',')} , эталон ${r.join(',')}`); }
    }
  }
  if (shown < 9 && mism) bad++;
  // 3) после возврата счётчики 1,2 заглушены; в счётчик 0 плеер не писал
  applyTaps();                             // остаток записей последнего кадра (глушение)
  let s12 = eff[1] === 0 && eff[2] === 0;
  if (c0bad) { console.log(`${nm}: ПЛЕЕР ТРОГАЛ счётчик 0 (${c0bad} записей: порт 0x0B / слова 0x32..0x36)`); bad++; }
  if (!s12) { console.log(`${nm}: после возврата счётчики 1/2 не заглушены (eff=${eff[1]},${eff[2]})`); bad++; }
  console.log(`${nm}\tкадров ${frames} (каталог ${ref.length}), сверено ${ref.length} x 2 счётчика,` +
              ` расхождений ${mism}, фаза ${typeof phase === "number" ? phase : "?"}`);
  taps = [];
}
console.log("---");
console.log(`потеряно кадров (обратный ход на di): ${lost}`);
console.log(bad ? `РАСХОЖДЕНИЙ: ${bad}` : `все ${TUNES.length} мелодии совпали с decode() блоба по всем кадрам`);
process.exit(bad ? 1 : 0);
