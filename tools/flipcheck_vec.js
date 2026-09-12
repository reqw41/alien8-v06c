#!/usr/bin/env node
// ГЕЙТ разворота спрайтов: ХОЛОДНЫЕ вызовы vflip_sprite_data по ВСЕМ спрайтам сборки и ВСЕМ
// четырём ориентациям (включая V-разворот, которого нет ни в одном сценарном гейте: замер
// tools/flipstat_vec.js даёт 0.00 V-разворотов на шести комнатах), результат сверяется с
// НЕЗАВИСИМОЙ моделью на JS. Сверяются байты ПО ВОЗВРАЩЁННОМУ DE — так гейт не зависит от
// того, разворачивает ли сборка мастера на месте или отдаёт копию из кэша.
//   node tools/flipcheck_vec.js build/alien8_vec.r0m build/alien8_vec.sld
// Коды возврата: 0 — совпало, 1 — расхождение или пустая выборка.
// A8FLIPBUG=1 — НЕГАТИВНЫЙ КОНТРОЛЬ: портит проверку H-разворота в коде (`and 0x40` -> `and 0x00`),
// гейт обязан упасть.
//
// Список спрайтов — по СИМВОЛАМ spr_* из .sld (77 штук), а НЕ по указателям sprite_tbl:
// в таблице есть записи, которые игра не использует, и разворот по ним портит чужую память.
"use strict";
const fs=require("fs"),vm=require("vm");
const base="/Users/boris/projects/vector06js";
const [ROM,SLD]=process.argv.slice(2);
const L={};
for(const l of fs.readFileSync(SLD,"latin1").split("\n")){const p=l.split("|");if(p.length>=8&&p[6]==="L"){const n=p[7].split(",")[1];if(n&&!(n in L))L[n]=+p[5];}}
const g={};g.window=g;g.document={createElement:()=>fc(),getElementById:()=>fc()};
function fcx(){return{createImageData:()=>({data:new Uint8ClampedArray(4)}),putImageData:()=>{},getImageData:()=>({data:new Uint8ClampedArray(4)}),fillRect(){},drawImage(){}};}
function fc(){return{width:0,height:0,style:{},getContext:()=>fcx()};}
g.requestAnimationFrame=()=>0;g.setTimeout=()=>0;g.print=()=>0;g.console={log(){},debug(){},warn(){},error(){},info(){}};
const ctx=vm.createContext(g);
for(const f of ["i8080-js/i8080_trace.js","i8080-js/i8080_disasm.js","i8080-js/i8080.js","src/fili.js","src/ay.js","src/fd1793.js","src/fddimage.js","src/i8253.js","src/io.js","src/keyboard.js","src/memory.js","src/sound.js","src/tv.js"])
  vm.runInContext(fs.readFileSync(base+"/"+f,"utf8"),ctx,{filename:f});
const memory=new ctx.Memory(),keyboard=new ctx.Keyboard(),timer=new ctx.I8253(),ay=new ctx.AY(),
      floppy=new(ctx.Floppy().FD1793)(),io=new ctx.IO(keyboard,timer,memory,ay,floppy);
const cpu=new ctx.I8080(memory,io),tape={advance:()=>{},sample:0,reset:()=>{}},v06c=new ctx.Vector06c(cpu,memory,io,ay,tape);
v06c.bmp=new Uint32Array(576*288);v06c.displayFrame=()=>{};v06c.check_breakpoint=()=>false;v06c.dbg=null;
const IMG=new Uint8Array(fs.readFileSync(ROM)).subarray(0,0x10000);
memory.init_from_array(IMG,0);memory.detach_boot&&memory.detach_boot();
const rd=a=>memory.read(a&0xffff,false), wr=(a,v)=>memory.write(a&0xffff,v&0xff,false);
const VFSD=L.vflip_sprite_data, IXC=L.z80_ix, OBJ=L.graphic_objs_tbl, VKBD=L.vkbd, REV=0xF100;
function die(msg){console.error("ГЕЙТ РАЗВОРОТА: "+msg);process.exit(1);}
if(VFSD===undefined||IXC===undefined||OBJ===undefined)die("нет меток vflip_sprite_data/z80_ix/graphic_objs_tbl");

// --- прогон до комнаты: таблицу бит-реверса на 0xF100 строит build_lookup_tbls ---
cpu.pc=0;cpu.sp=0xBC00;cpu.iff=false;
if(VKBD!==undefined)for(let r=0;r<8;r++)wr(VKBD+r,0xFF);
const lst=fs.readFileSync(ROM.replace(/\.r0m$/,".lst"),"latin1").split("\n");
let SYNC=-1;for(const l of lst){const m=l.match(/^\s*\d+\+?\s+([0-9A-F]{4})\s.*\s+call\s+init_start_location/);if(m){SYNC=parseInt(m[1],16);break;}}
if(SYNC<0)die("не нашёл call init_start_location");
const ow=memory.write.bind(memory);
let phase="menu";
const KROW=4,KBIT=0;                                      // «0» в виртуальной матрице
memory.write=function(a,w,s){a&=0xffff;
  if(phase==="menu"&&cpu.pc===SYNC)phase="init";
  if(a===L.curr_room_attrib&&phase==="init"&&w!==0){phase="game";if(VKBD!==undefined)ow(VKBD+KROW,0xFF,false);}
  return ow(a,w,s);};
for(let f=0;f<60;f++)v06c.oneInterrupt(true);
if(VKBD!==undefined)ow(VKBD+KROW,0xFF&~(1<<KBIT),false); else keyboard.matrix[2]|=1;
let guard=0;while(phase!=="game"&&guard++<3000)v06c.oneInterrupt(true);
if(phase!=="game")die("не дошли до комнаты");
memory.write=ow;

// независимая модель бит-реверса; таблица в памяти обязана ей соответствовать
const rev=new Uint8Array(256);
for(let i=0;i<256;i++){let r=0;for(let b=0;b<8;b++)if(i&(1<<b))r|=0x80>>b;rev[i]=r;}
for(let i=0;i<256;i++)if(rd(REV+i)!==rev[i])die(`reverse_bits_table на ${REV.toString(16)} не похожа на бит-реверс (байт ${i})`);

// НЕГАТИВНЫЙ КОНТРОЛЬ: испортить проверку H-разворота (`and 0x40` -> `and 0x00`) в теле разворота
if(process.env.A8FLIPBUG){
  let at=-1;for(let a=VFSD;a<VFSD+0x200;a++)if(rd(a)===0xE6&&rd(a+1)===0x40){at=a;break;}
  if(at<0)die("негативный контроль: не нашёл `and 0x40` в теле разворота");
  wr(at+1,0x00);console.log(`НЕГАТИВНЫЙ КОНТРОЛЬ: ${(at).toString(16).toUpperCase()} and 0x40 -> and 0x00`);
}

// --- выборка: символы spr_* ---
// spr_00 (w=0) отсеивается самим flip_sprite (пустой спрайт), spr_28 имеет h=1: у исходного
// Z80-кода V-разворот при h<2 уходит в 256 итераций и портит память (в игре не случается),
// поэтому такие спрайты в выборку не берём — сверять с моделью там нечего.
const spr=[];
for(const [n,a] of Object.entries(L)) if(/^spr_[0-9A-Fa-f]+$/.test(n)){
  const w=IMG[a]&0x0F,h=IMG[a+1];
  if(w===0||h<2||h>64)continue;
  if(!spr.some(x=>x[1]===a))spr.push([n,a]);}
spr.sort((x,y)=>x[1]-y[1]);
if(spr.length<20)die(`подозрительно мало спрайтов в выборке: ${spr.length} (гейт вакуумный)`);

// --- модель: чистая функция от исходных байтов и требуемой ориентации ---
function model(bytes,want){
  const w=bytes[0]&0x0F,h=bytes[1],cur=bytes[0]&0xC0,rw=2*w;
  let rows=[];for(let r=0;r<h;r++)rows.push(Array.from(bytes.slice(2+r*rw,2+(r+1)*rw)));
  let flag=cur;
  if((cur^want)&0x80){rows.reverse();flag^=0x80;}
  if((cur^want)&0x40){
    rows=rows.map(row=>{const out=new Array(rw);
      for(let p=0;p<w;p++){out[2*p]=rev[row[2*(w-1-p)]];out[2*p+1]=rev[row[2*(w-1-p)+1]];}return out;});
    flag^=0x40;}
  const out=new Uint8Array(2+rw*h);out[0]=(bytes[0]&0x3F)|flag;out[1]=h;
  for(let r=0;r<h;r++)out.set(rows[r],2+r*rw);
  return out;}

// --- холодный вызов ---
const RETA=0x0002;
let bad=0,calls=0,flips=0;
function call1(name,de,want){
  const w=IMG[de]&0x0F,h=IMG[de+1],n=2+2*w*h;
  for(let i=0;i<n;i++)wr(de+i,IMG[de+i]);              // ХОЛОДНОЕ состояние: байты из образа
  const before=new Uint8Array(n);for(let i=0;i<n;i++)before[i]=rd(de+i);
  wr(IXC,OBJ&0xff);wr(IXC+1,OBJ>>8);
  wr(OBJ+7,(rd(OBJ+7)&0x3F)|want);
  wr(0xBFFE,RETA&0xff);wr(0xBFFF,RETA>>8);cpu.sp=0xBFFE;
  cpu.set_rp(2,de);                                     // DE
  cpu.pc=VFSD;cpu.iff=false;
  let steps=0;while(cpu.pc!==RETA&&steps++<400000)cpu.instruction();
  if(cpu.pc!==RETA)die(`${name}: разворот не вернулся (w=${w} h=${h}, ориентация ${want.toString(16)}), pc=${cpu.pc.toString(16)}`);
  const dst=cpu.de();
  calls++; if((before[0]&0xC0)!==want)flips++;
  const exp=model(before,want);
  for(let i=0;i<n;i++){const got=rd(dst+i);
    if(got!==exp[i]){
      if(bad<8)console.error(`${name} @${de.toString(16).toUpperCase()} (w=${w} h=${h}) ${(before[0]&0xC0).toString(16)}->${want.toString(16)}: `+
        `байт ${i} по адресу ${(dst+i).toString(16).toUpperCase()} = ${got.toString(16)}, ждали ${exp[i].toString(16)}`);
      bad++;break;}}
}
// две волны: каждая ориентация из ХОЛОДНОГО состояния (мастер восстанавливается перед вызовом)
for(const [n,a] of spr) for(const want of [0x00,0x40,0x80,0xC0]) call1(n,a,want);
// и цепочкой (без восстановления): ориентации по кругу — ловит накопленное состояние
function chain(name,de,seq){
  const w=IMG[de]&0x0F,h=IMG[de+1],n=2+2*w*h;
  for(let i=0;i<n;i++)wr(de+i,IMG[de+i]);
  let cur=new Uint8Array(n);for(let i=0;i<n;i++)cur[i]=IMG[de+i];
  for(const want of seq){
    const exp=model(cur,want);
    wr(IXC,OBJ&0xff);wr(IXC+1,OBJ>>8);wr(OBJ+7,(rd(OBJ+7)&0x3F)|want);
    wr(0xBFFE,RETA&0xff);wr(0xBFFF,RETA>>8);cpu.sp=0xBFFE;
    cpu.set_rp(2,de);cpu.pc=VFSD;cpu.iff=false;
    let steps=0;while(cpu.pc!==RETA&&steps++<400000)cpu.instruction();
    if(cpu.pc!==RETA)die(`${name}: цепочка не вернулась`);
    const dst=cpu.de();calls++;if((cur[0]&0xC0)!==want)flips++;
    for(let i=0;i<n;i++){const got=rd(dst+i);
      if(got!==exp[i]){if(bad<8)console.error(`${name} цепочка -> ${want.toString(16)}: байт ${i} = ${got.toString(16)}, ждали ${exp[i].toString(16)}`);bad++;break;}}
    cur=exp;}
}
for(const [n,a] of spr) chain(n,a,[0x40,0x00,0x80,0xC0,0x40,0x80,0x00,0xC0,0x00]);
if(bad)die(`РАСХОЖДЕНИЙ ${bad} на ${calls} вызовах (спрайтов ${spr.length})`);
console.log(`разворот: СОВПАДЕНИЕ, спрайтов ${spr.length}, вызовов ${calls}, из них с настоящим разворотом ${flips}`);
process.exit(0);
