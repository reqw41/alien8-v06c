#!/usr/bin/env node
// ГЕЙТ ПИКСЕЛЕЙ 16-ЦВЕТНОЙ ЗАСТАВКИ (итоговый релиз, tools/a8_pack.py).
//
//   node tools/splashpix_vec.js [релиз.r0m [src/alien8_splash16.bin]]
//   A8SP_FRAMES=40,8500 (кадры проверки после сброса), A8SP_PPM=build/splash16_emu (снимок кадра
//   в <префикс>_<кадр>.ppm), A8SP_MD5=<md5 bmp> — сверить и контрольную сумму кадра эмулятора.
//
// На каждом кадре (клавиш нет, идёт мелодия):
//  1. ПАМЯТЬ: четыре плоскости 0x8000..0xFFFF == выход конвертера (tools/a8_splash.py) байт в байт,
//     включая нули строк вне картинки (бордюр и поля экрана — индекс 0);
//  2. ПАЛИТРА: 16 записей палитры эмулятора (io.Palette, то, что реально защёлкнуто) == палитра
//     конвертера, по аппаратному индексу p0<<3|p1<<2|p2<<1|p3;
//  3. КАДР (bmp эмулятора 576x288, точка Вектора = 2 точки bmp): картинка 256x192 на своём месте
//     совпадает с тем, что даёт конвертер (индекс из плоскостей -> цвет палитры), ВСЁ остальное
//     (поля 0..31/224..255 и бордюр) — цвет индекса 0. Место картинки ищется один раз по кадру.
// Печатает md5 bmp (эталон для отчёта); код 1 при любом расхождении.
"use strict";
const fs = require("fs"), crypto = require("crypto");
const E = require("./vec_emu");
const ROM = process.argv[2] || "build/alien8_release.r0m";
const PIC = new Uint8Array(fs.readFileSync(process.argv[3] || "src/alien8_splash16.bin"));
const FR = (process.env.A8SP_FRAMES || "40,8500").split(",").map(Number);
if (PIC.length !== 4 * 8192 + 16) { console.log("конвертер: не 32784 Б"); process.exit(2); }
const PAL = PIC.subarray(4 * 8192);
const W = 576, H = 288;
// ожидаемая картинка: индекс точки (x, y) 256x192, y = 0 — верх
const idx = new Uint8Array(256 * 192);
for (let y = 0; y < 192; y++) for (let x = 0; x < 256; x++) {
  const a = (x >> 3) * 256 + (223 - y), m = 0x80 >> (x & 7);
  let k = 0;
  for (let p = 0; p < 4; p++) if (PIC[p * 8192 + a] & m) k |= 8 >> p;
  idx[y * 256 + x] = k;
}
const col = k => E.palColor(PAL[k]);
const m = E.mk(ROM);
let bad = 0, X0 = -1, Y0 = -1;
const fail = s => { console.log("КРАСНЫЙ: " + s); bad++; };
for (const F of FR) {
  while (m.frames < F) m.frame();
  // 1
  let nm = 0, first = "";
  for (let a = 0; a < 0x8000; a++) if (m.rd(0x8000 + a) !== PIC[a]) { nm++; if (!first) first = (0x8000 + a).toString(16); }
  // 2
  const P = m.palette(); let np = 0;
  for (let k = 0; k < 16; k++) if ((P[k] >>> 0) !== col(k)) np++;
  // 3
  const bmp = m.v06c.bmp;
  if (X0 < 0) {                         // место картинки: первая строка bmp, где точки как в строке 0
    search: for (let y = 0; y + 192 <= H; y++) for (let x = 0; x + 512 <= W; x++) {
      let ok = true;
      for (let i = 0; i < 256 && ok; i++) ok = (bmp[y * W + x + 2 * i] >>> 0) === col(idx[i]) && (bmp[y * W + x + 2 * i + 1] >>> 0) === col(idx[i]);
      if (ok) { X0 = x; Y0 = y; break search; }
    }
  }
  let nb = 0, nbord = 0;
  if (X0 >= 0) {
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const v = bmp[y * W + x] >>> 0, py = y - Y0, px = (x - X0) >> 1;
      if (py >= 0 && py < 192 && x >= X0 && px < 256) { if (v !== col(idx[py * 256 + px])) nb++; }
      else if (v !== col(0)) nbord++;
    }
  }
  const md5 = crypto.createHash("md5").update(Buffer.from(bmp.buffer, bmp.byteOffset, bmp.byteLength)).digest("hex");
  let nz = 0; for (let i = 0; i < idx.length; i++) if (idx[i]) nz++;
  console.log(`кадр ${F}: плоскости против конвертера — расхождений ${nm}${first ? " (первое " + first + ")" : ""}; ` +
              `палитра — ${np} из 16; картинка в bmp ${X0 >= 0 ? `с (${X0},${Y0})` : "НЕ НАЙДЕНА"}: точек мимо ${nb}, ` +
              `поля/бордюр не цвета индекса 0 — ${nbord}; точек не индекса 0 ${nz}; md5 bmp ${md5}`);
  if (nm) fail(`кадр ${F}: плоскости разошлись с конвертером`);
  if (np) fail(`кадр ${F}: палитра разошлась с конвертером`);
  if (X0 < 0) fail(`кадр ${F}: картинки конвертера в кадре нет`);
  if (nb || nbord) fail(`кадр ${F}: кадр эмулятора разошёлся с картинкой конвертера`);
  if (process.env.A8SP_MD5 && md5 !== process.env.A8SP_MD5) fail(`кадр ${F}: md5 кадра ${md5} != ${process.env.A8SP_MD5}`);
  if (process.env.A8SP_PPM) {
    const hdr = Buffer.from(`P6 ${W} ${H} 255\n`), px = Buffer.alloc(W * H * 3);
    for (let i = 0; i < W * H; i++) { const v = bmp[i] >>> 0; px[3 * i] = v & 0xFF; px[3 * i + 1] = (v >> 8) & 0xFF; px[3 * i + 2] = (v >> 16) & 0xFF; }
    fs.writeFileSync(`${process.env.A8SP_PPM}_${F}.ppm`, Buffer.concat([hdr, px]));
  }
}
console.log(bad ? `ГЕЙТ ПИКСЕЛЕЙ ЗАСТАВКИ КРАСНЫЙ: нарушений ${bad}` : "гейт пикселей заставки зелёный");
process.exit(bad ? 1 : 0);
