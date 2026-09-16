#!/usr/bin/env node
// ЦВЕТНОЙ снимок экрана Alien 8 на Векторе: четыре плоскости + палитра vec_pal -> PNG,
// плюс текстовый дамп плоскостей для гейта tools/hudcolor.py.
//
//   node tools/hudshot_vec.js build/alien8_vec.r0m build/alien8_vec.sld <итераций> [out.png]
//
// Ключи окружения:
//   A8ROOM=<n>      комната (то же, что у zxpix_vec.js и ZXSCR_ROOM стенда ZX)
//   A8HS_FRAMES=<n> снимок через n КАДРОВ от сброса, не дожидаясь комнаты (меню, заставка)
//   A8HS_JP=метка[@кадров]  после прогона перейти на метку и покрутить кадры — так снимаются
//                   экраны, до которых игрой не доехать за разумное время (game_over, финал)
//   A8HS_DUMP=файл  текстовый дамп плоскостей (строка = "<строка памяти> p<N> <256 символов>")
//                   и палитры; A8HS_ROWS=r0,r1 — какие строки ПАМЯТИ (по умолчанию 32,223)
//   A8HS_SCALE=<n>  масштаб PNG (2), A8HS_PLANE=0..3 — показать одну плоскость ч/б
//   A8HS_FILM=префикс       ПЛЁНКА: дамп плоскостей на КАЖДОМ кадре окна A8HS_FILMFR=a,b[,шаг]
//                   в <префикс>_<кадр>.txt (формат A8HS_DUMP). Так ловятся дефекты ПЕРЕХОДОВ:
//                   один кадр «после» о том, что было в середине, не говорит ничего
//   A8HS_LIVES=1    бессмертие (жизни держатся на 5): длинные прогоны
//   A8HS_KEYS=файл  расписание клавиш по КАДРАМ, формат tools/shot_vec.js
//   A8HS_INPUTS=файл  расписание клавиш по ИТЕРАЦИЯМ — файлы стенда ZX (inputs_death137.txt
//                   и т.п.), тот же сдвиг на итерацию, что у zxpix_vec.js
//   A8HS_MAXF=<кадров> предел по КАДРАМ (на экранах GAME OVER/меню итерации стоят, и предел
//                   по итерациям сам не сработает)
//   A8HS_DIE=<итер> положить lives = 0 на этой итерации: гибель уводит в НАСТОЯЩИЙ game_over
//                   и дальше на экран RE-PROGRAMMING — вся дорога своя, без прыжка A8HS_JP
//
// Экран Вектора: адрес байта = плоскость + (столбец<<8) + строка памяти; строка памяти 255 —
// ВЕРХ кадра. Картинка порта лежит в строках 32..223 (строка = 223 - строка ZX).
// Индекс палитры = p0<<3|p1<<2|p2<<1|p3 (p0 = 0x8000, p1 = 0xA000, p2 = 0xC000, p3 = 0xE000),
// байт палитры — %BBGGGRRR. Плоскость 2 здесь и есть СЕЛЕКТОР БЕЛОГО HUD.
"use strict";
const fs=require("fs"),vm=require("vm"),zlib=require("zlib");
const base="/Users/boris/projects/vector06js";
const [ROM,SLD,NS,OUT]=process.argv.slice(2); const N=+NS||300;
if(!ROM||!SLD){console.error("нужно: <rom> <sld> <итераций> [out.png]");process.exit(2);}
const L={};
for(const l of fs.readFileSync(SLD,"latin1").split("\n")){const p=l.split("|");
  if(p.length>=8&&p[6]==="L"){const n=p[7].split(",")[1];if(n&&!(n in L))L[n]=+p[5];}}
const SEED2HI=L.seed_2+1, ROOM=L.curr_room_attrib;
const lst=fs.readFileSync(ROM.replace(/\.r0m$/,".lst"),"latin1").split("\n");
let SYNC=-1;for(const l of lst){const m=l.match(/^\s*\d+\+?\s+([0-9A-F]{4})\s.*\s+call\s+init_start_location/);if(m){SYNC=parseInt(m[1],16);break;}}
if(SYNC<0)throw new Error("не нашёл call init_start_location в листинге");
const g={};g.window=g;g.document={createElement:()=>fc(),getElementById:()=>fc()};
function fcx(){return{createImageData:()=>({data:new Uint8ClampedArray(4)}),putImageData:()=>{},getImageData:()=>({data:new Uint8ClampedArray(4)}),fillRect(){},drawImage(){}};}
function fc(){return{width:0,height:0,style:{},getContext:()=>fcx()};}
g.requestAnimationFrame=()=>0;g.setTimeout=()=>0;g.print=()=>0;g.console={log(){},debug(){},warn(){},error(){},info(){}};
const ctx=vm.createContext(g);
for(const f of ["i8080-js/i8080_trace.js","i8080-js/i8080_disasm.js","i8080-js/i8080.js","src/fili.js","src/ay.js","src/fd1793.js","src/fddimage.js","src/i8253.js","src/io.js","src/keyboard.js","src/memory.js","src/sound.js","src/tv.js"])
  vm.runInContext(fs.readFileSync(base+"/"+f,"utf8"),ctx,{filename:f});
const memory=new ctx.Memory(),keyboard=new ctx.Keyboard(),timer=new ctx.I8253(),ay=new ctx.AY(),
      floppy=new(ctx.Floppy().FD1793)(),io=new ctx.IO(keyboard,timer,memory,ay,floppy);
// Джойстик Вектора (порт 0x0E) в vector06js собирается из матрицы — подменяем чтение покоем.
{ const _rd=io.input.bind(io); io.input=p=>((p&0xFF)===0x0E?0xFF:_rd(p)); }
const cpu=new ctx.I8080(memory,io),tape={advance:()=>{},sample:0,reset:()=>{}},
      v06c=new ctx.Vector06c(cpu,memory,io,ay,tape);
v06c.bmp=new Uint32Array(576*288);v06c.displayFrame=()=>{};v06c.check_breakpoint=()=>false;v06c.dbg=null;
memory.init_from_array(new Uint8Array(fs.readFileSync(ROM)).subarray(0,0x10000),0);memory.detach_boot&&memory.detach_boot();
cpu.pc=0;cpu.sp=0x8000;cpu.iff=false;
const VKEYS={a:[4,0x02],b:[4,0x04],c:[4,0x08],d:[4,0x10],e:[4,0x20],f:[4,0x40],g:[4,0x80],
  h:[5,0x01],i:[5,0x02],j:[5,0x04],k:[5,0x08],l:[5,0x10],m:[5,0x20],n:[5,0x40],o:[5,0x80],
  p:[6,0x01],q:[6,0x02],r:[6,0x04],s:[6,0x08],t:[6,0x10],u:[6,0x20],v:[6,0x40],w:[6,0x80],
  x:[7,0x01],y:[7,0x02],z:[7,0x04],space:[7,0x80],
  "0":[2,0x01],"1":[2,0x02],"2":[2,0x04],"3":[2,0x08],"4":[2,0x10],"5":[2,0x20],"6":[2,0x40],"7":[2,0x80],
  "8":[3,0x01],"9":[3,0x02],vk:[0,0x04],left:[0,0x10],up:[0,0x20],right:[0,0x40],down:[0,0x80]};
function key(k,down){const e=VKEYS[k];if(!e)throw new Error("нет клавиши "+k);
  if(down)keyboard.matrix[e[0]]|=e[1];else keyboard.matrix[e[0]]&=~e[1];}
const plan={};
if(process.env.A8HS_KEYS&&fs.existsSync(process.env.A8HS_KEYS))
  for(const l of fs.readFileSync(process.env.A8HS_KEYS,"utf8").split("\n")){
    const m=l.trim().match(/^(\d+)\s+(\S+)\s+(down|up)/i);
    if(m)(plan[+m[1]]=plan[+m[1]]||[]).push([m[2].toLowerCase(),m[3].toLowerCase()==="down"]);}
// Расписание стенда ZX по ИТЕРАЦИЯМ (тот же сдвиг +1, что в zxpix_vec.js).
const inputs={};
if(process.env.A8HS_INPUTS&&fs.existsSync(process.env.A8HS_INPUTS))
  for(const l of fs.readFileSync(process.env.A8HS_INPUTS,"utf8").split("\n")){
    const m=l.trim().match(/^(\d+)\s+(\S+)\s+(down|up)/i);
    if(m)(inputs[+m[1]+1]=inputs[+m[1]+1]||[]).push([m[2].toLowerCase(),m[3].toLowerCase()==="down"]);}
const DIE=+(process.env.A8HS_DIE||0);
const ow=memory.write.bind(memory);
const rdb=a=>memory.bytes[memory.tobank(a&0xffff)];
const PLANES=[0x8000,0xA000,0xC000,0xE000];
// Строка `state` — ПОРТОВЫЕ ФЛАГИ, по которым гейт узнаёт экран без панели ТОЧНО, а не на глаз:
// byte_5B24 != 0 — экран «RE-PROGRAMMING» (сборка робота после GAME OVER): игровой цикл уходит
// на loc_A741 в обход sub_AD66, display_panel и colour_something, то есть панели на экране нет
// и атрибуты ZX там остались от clr_attr (0x42).
function dumpPlanes(file,r0,r1){
  const out=["state b5B24 "+rdb(L.byte_5B24)+" rsi "+rdb(L.render_status_info)
             +" attr "+rdb(L.curr_room_attrib)+" lives "+rdb(L.lives),
             "pal "+[...Array(16)].map((_,i)=>rdb(L.vec_pal+i).toString(16).padStart(2,"0")).join(" ")];
  for(let mrow=r1;mrow>=r0;mrow--){
    const t=["","","",""];
    for(let col=0;col<32;col++)for(let pl=0;pl<4;pl++){
      const b=rdb(PLANES[pl]+(col<<8)+mrow);
      for(let bit=7;bit>=0;bit--)t[pl]+=((b>>bit)&1)?"#":".";}
    for(let pl=0;pl<4;pl++)out.push(String(mrow).padStart(3)+" p"+pl+" "+t[pl]);}
  fs.writeFileSync(file,out.join("\n")+"\n");}
// ПЛЁНКА: кадры окна пишутся ПРЯМО ПО ХОДУ прогона — состояние экрана в середине перехода
// иначе не достать (к концу его уже перерисовали).
const FILM=process.env.A8HS_FILM;
let FLO=0,FHI=-1,FST=1,filmN=0;
if(FILM){const m=(process.env.A8HS_FILMFR||"0,1000000").split(",");FLO=+m[0];FHI=+m[1];FST=+(m[2]||1);}
let phase="menu",iter=0;
memory.write=function(a,w,s){a&=0xffff;
  if(phase==="menu"&&cpu.pc===SYNC){ow(L.seed_1,0x34,false);ow(L.seed_1+1,0x12,false);
    ow(L.seed_2,0x78,false);ow(L.seed_2+1,0x56,false);ow(L.seed_3,0x9A,false);phase="init";}
  if(process.env.A8ROOM&&phase==="init"&&(a===L.graphic_objs_tbl+8||a===L.graphic_objs_tbl+40))
    w=+process.env.A8ROOM;
  if(a===ROOM&&phase==="init"&&w!==0){phase="game";key("0",false);}
  if(a===SEED2HI&&phase==="game"){iter++;
    if(process.env.A8HS_LIVES)ow(L.lives,5,false);
    if(DIE&&iter===DIE)ow(L.lives,0,false);          // последняя жизнь: следующая гибель = GAME OVER
    for(const [k,d] of (inputs[iter]||[]))key(k,d);}
  return ow(a,w,s);};
function frame(f){for(const [k,d] of (plan[f]||[]))key(k,d);v06c.oneInterrupt(true);
  if(FILM&&f>=FLO&&f<=FHI&&(f-FLO)%FST===0){dumpPlanes(FILM+"_"+String(f).padStart(5,"0")+".txt",32,223);filmN++;}}
let frames=0;
for(;frames<60;frames++)frame(frames);
if(process.env.A8HS_FRAMES){                        // снимок по кадрам: меню, заставка
  const N2=+process.env.A8HS_FRAMES;
  for(;frames<N2;frames++)frame(frames);
}else{
  key("0",true);
  let guard=0; while(phase!=="game"&&guard++<6000)frame(frames++);
  if(phase!=="game")throw new Error("не дошли до комнаты");
  const it0=iter;
  const MAXF=+(process.env.A8HS_MAXF||0);       // предел по КАДРАМ: на экране без игры итерации стоят
  while(iter-it0<N&&frames<200000&&(!MAXF||frames<MAXF))frame(frames++);
}
// A8HS_JP=метка[@кадров] — перейти на метку (game_over, финал) и покрутить кадры.
// Стек как у игры: SP = seed_1 (тот же символический адрес, что в загрузчике порта).
if(process.env.A8HS_JP){const m=process.env.A8HS_JP.split("@"),lbl=m[0],nf=+(m[1]||300);
  if(L[lbl]===undefined)throw new Error("A8HS_JP: нет метки "+lbl);
  cpu.pc=L[lbl];cpu.sp=L.seed_1;
  for(let f=0;f<nf;f++)frame(frames++);
  console.log(`A8HS_JP: ${lbl}, ${nf} кадров`);}

const rd=rdb, PLANE=PLANES;
const pal=[];for(let i=0;i<16;i++){const w=rd(L.vec_pal+i);
  pal.push([(w&0x07)<<5,(w&0x38)<<2,(w&0xc0)]);}   // %BBGGGRRR -> RGB
const palhex=[...Array(16)].map((_,i)=>rd(L.vec_pal+i).toString(16).padStart(2,"0"));
console.log("vec_pal: "+palhex.map((h,i)=>i.toString(16)+"="+h).join(" "));

if(process.env.A8HS_DUMP){
  let r0=32,r1=223; if(process.env.A8HS_ROWS){const m=process.env.A8HS_ROWS.split(",");r0=+m[0];r1=+m[1];}
  const out=["pal "+palhex.join(" ")];
  for(let mrow=r1;mrow>=r0;mrow--){
    const s=["","","",""];
    for(let col=0;col<32;col++)for(let pl=0;pl<4;pl++){
      const b=rd(PLANE[pl]+(col<<8)+mrow);
      for(let bit=7;bit>=0;bit--)s[pl]+=((b>>bit)&1)?"#":".";}
    for(let pl=0;pl<4;pl++)out.push(String(mrow).padStart(3)+" p"+pl+" "+s[pl]);}
  fs.writeFileSync(process.env.A8HS_DUMP,out.join("\n")+"\n");
  console.log("дамп плоскостей -> "+process.env.A8HS_DUMP);}

// ---- PNG: вся картинка (строки памяти 32..223 = 192 строки ZX) ----
const SCALE=+(process.env.A8HS_SCALE||2), ONLY=process.env.A8HS_PLANE!==undefined?+process.env.A8HS_PLANE:-1;
const W=256,H=192,IW=W*SCALE,IH=H*SCALE,img=Buffer.alloc(IW*IH*3);
for(let y=0;y<H;y++){const mrow=223-y;
  for(let col=0;col<32;col++){
    const b=PLANE.map(p=>rd(p+(col<<8)+mrow));
    for(let bit=7;bit>=0;bit--){
      let c;
      if(ONLY>=0){const v=((b[ONLY]>>bit)&1)?255:0;c=[v,v,v];}
      else{const idx=(((b[0]>>bit)&1)<<3)|(((b[1]>>bit)&1)<<2)|(((b[2]>>bit)&1)<<1)|((b[3]>>bit)&1);c=pal[idx];}
      const x=col*8+(7-bit);
      for(let dy=0;dy<SCALE;dy++)for(let dx=0;dx<SCALE;dx++){
        const o=((y*SCALE+dy)*IW+x*SCALE+dx)*3;img[o]=c[0];img[o+1]=c[1];img[o+2]=c[2];}}}}
const raw=Buffer.alloc(IH*(IW*3+1));
for(let y=0;y<IH;y++){raw[y*(IW*3+1)]=0;img.copy(raw,y*(IW*3+1)+1,y*IW*3,(y+1)*IW*3);}
let TBL=null;function crc32(buf){if(!TBL){TBL=new Int32Array(256);
  for(let n=0;n<256;n++){let c=n;for(let k=0;k<8;k++)c=c&1?0xEDB88320^(c>>>1):c>>>1;TBL[n]=c;}}
  let c=0xFFFFFFFF;for(const b of buf)c=TBL[(c^b)&0xFF]^(c>>>8);return (c^0xFFFFFFFF)>>>0;}
function chunk(type,data){const len=Buffer.alloc(4);len.writeUInt32BE(data.length);
  const td=Buffer.concat([Buffer.from(type,"latin1"),data]);const crc=Buffer.alloc(4);
  crc.writeUInt32BE(crc32(td)>>>0);return Buffer.concat([len,td,crc]);}
const ihdr=Buffer.alloc(13);ihdr.writeUInt32BE(IW,0);ihdr.writeUInt32BE(IH,4);ihdr[8]=8;ihdr[9]=2;
const png=Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk("IHDR",ihdr),
  chunk("IDAT",zlib.deflateSync(raw)),chunk("IEND",Buffer.alloc(0))]);
const out=OUT||"build/hudshot.png";fs.writeFileSync(out,png);
if(FILM)console.log(`плёнка: ${filmN} кадров -> ${FILM}_*.txt`);
console.log(`итераций ${iter}, кадров ${frames}, комната ${process.env.A8ROOM||"(старт)"} -> ${out} (${IW}x${IH})`);
