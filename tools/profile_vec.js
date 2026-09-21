#!/usr/bin/env node
// Профиль i8080-сборки Alien 8 по процедурам: такты и вызовы. Шагает по инструкциям на ядре vector06js.
//   node tools/profile_vec.js build/alien8_8080.r0m build/alien8_8080.sld <итераций> [inputs.txt]
// ВАЖНО (§14 рецепта): такты берутся из cpu.vcycles (слоты шины Вектора), а НЕ из cpu.instruction();
// ВИ53 тикает вдвое медленнее CPU — иначе секундомер бюджета di стоит и замер врёт.
"use strict";
const fs=require("fs"),vm=require("vm");
const base="/Users/boris/projects/vector06js";
const [ROM,SLD,NS,INPUTS]=process.argv.slice(2); const N=+NS||300;
const LAG=+(process.env.A8_LAG||1);
const IRQDROP=!!process.env.A8_IRQDROP;
const L={};
for(const l of fs.readFileSync(SLD,"latin1").split("\n")){const p=l.split("|");if(p.length>=8&&p[6]==="L"){const n=p[7].split(",")[1];if(n&&!(n in L))L[n]=+p[5];}}
const fn=Object.entries(L).filter(([n,a])=>!/^(loc_|\.|IL_|rk_|a8_vb_|rp_|vb_|ps_|fw_|bts_|us_|vdb_|vp_|sd_|usl_|cdo_|lo_|ov_|d_3467|u02_|u2d_|ady_|adz_|wno_|cpxy_|doi_|ino_|ae3_|fl_v|fl_h|fl_r|fl_n|fl_w|fl_c|mst_|msr_|mse|mc_|mf_|mvm_|msi_|mpt_|mt_|aml_|pa_l|pauk_)/.test(n)&&a>=0x80).sort((x,y)=>x[1]-y[1]);
const isHelper=fn.map(x=>/^il_/.test(x[0]));
const fa=fn.map(x=>x[1]), fnm=fn.map(x=>x[0]);
function idx(pc){let lo=0,hi=fa.length-1,r=-1;while(lo<=hi){const m=(lo+hi)>>1;if(fa[m]<=pc){r=m;lo=m+1;}else hi=m-1;}return r;}
const SEED2HI=L.seed_2+1, ROOM=L.curr_room_attrib, VKBD=L.vkbd;
const lst=fs.readFileSync(ROM.replace(/\.r0m$/,".lst"),"latin1").split("\n");
let SYNC=-1;for(const l of lst){const m=l.match(/^\s*\d+\+?\s+([0-9A-F]{4})\s.*\s+call\s+init_start_location/);if(m){SYNC=parseInt(m[1],16);break;}}
if(SYNC<0)throw new Error("не нашёл call init_start_location");
const g={};g.window=g;g.document={createElement:()=>fc(),getElementById:()=>fc()};
function fcx(){return{createImageData:()=>({data:new Uint8ClampedArray(4)}),putImageData:()=>{},getImageData:()=>({data:new Uint8ClampedArray(4)}),fillRect(){},drawImage(){}};}
function fc(){return{width:0,height:0,style:{},getContext:()=>fcx()};}
g.requestAnimationFrame=()=>0;g.setTimeout=()=>0;g.print=()=>0;g.console={log(){},debug(){},warn(){},error(){},info(){}};
const ctx=vm.createContext(g);
for(const f of ["i8080-js/i8080_trace.js","i8080-js/i8080_disasm.js","i8080-js/i8080.js","src/fili.js","src/ay.js","src/fd1793.js","src/fddimage.js","src/i8253.js","src/io.js","src/keyboard.js","src/memory.js","src/sound.js","src/tv.js"])
  vm.runInContext(fs.readFileSync(base+"/"+f,"utf8"),ctx,{filename:f});
const memory=new ctx.Memory(),keyboard=new ctx.Keyboard(),timer=new ctx.I8253(),ay=new ctx.AY(),
      floppy=new(ctx.Floppy().FD1793)(),io=new ctx.IO(keyboard,timer,memory,ay,floppy);
// ДЖОЙСТИК ВЕКТОРА (порт 0x0E, чтение) в vector06js СОБИРАЕТСЯ ИЗ МАТРИЦЫ (стрелки, пробел, W) —
// в стенде это подмешивало бы джойстик к каждому нажатию клавиши, чего на живом Векторе нет
// (там это отдельная микросхема). Подменяем чтение: по умолчанию покой, сценарий задаёт joy(...).
// Биты порта active-low: 0 RIGHT, 1 LEFT, 2 UP, 3 DOWN, 6 FIRE1, 7 FIRE2; биты 4,5 схема держит в 1.
const JOY_R=0x01, JOY_L=0x02, JOY_U=0x04, JOY_D=0x08, JOY_F1=0x40, JOY_F2=0x80, JOY_IDLE=0xFF;
let JOY = JOY_IDLE;
function joy(...bits){ JOY = JOY_IDLE; for(const b of bits) JOY &= ~b & 0xFF; return JOY; }
{ const _rd = io.input.bind(io); io.input = p => ((p & 0xFF) === 0x0E ? JOY : _rd(p)); }
const cpu=new ctx.I8080(memory,io),tape={advance:()=>{},sample:0,reset:()=>{}},v06c=new ctx.Vector06c(cpu,memory,io,ay,tape);
v06c.bmp=new Uint32Array(576*288);v06c.displayFrame=()=>{};v06c.check_breakpoint=()=>false;v06c.dbg=null;
memory.init_from_array(new Uint8Array(fs.readFileSync(ROM)).subarray(0,0x10000),0);memory.detach_boot&&memory.detach_boot();
cpu.pc=0;cpu.sp=0xBC00;cpu.iff=false;
if(VKBD!==undefined)for(let r=0;r<8;r++)memory.write(VKBD+r,0xFF,false);
const ow=memory.write.bind(memory); const poke=(a,v)=>ow(a&0xffff,v&0xff,false);
const KEYS={shift:[0,0],z:[0,1],x:[0,2],c:[0,3],v:[0,4],a:[1,0],s:[1,1],d:[1,2],f:[1,3],g:[1,4],q:[2,0],w:[2,1],e:[2,2],r:[2,3],t:[2,4],
  "1":[3,0],"2":[3,1],"3":[3,2],"4":[3,3],"5":[3,4],"0":[4,0],"9":[4,1],"8":[4,2],"7":[4,3],"6":[4,4],p:[5,0],o:[5,1],i:[5,2],u:[5,3],y:[5,4],
  enter:[6,0],l:[6,1],k:[6,2],j:[6,3],h:[6,4],space:[7,0],sym:[7,1],m:[7,2],n:[7,3],b:[7,4]};
const VKEYS={z:[7,0x04],x:[7,0x01],a:[4,0x02],q:[6,0x02],"0":[2,0x01],space:[7,0x80]};
const rows=new Uint8Array(8).fill(0xFF);
function key(k,down){
  if(VKBD===undefined){const [r,b]=VKEYS[k];if(down)keyboard.matrix[r]|=b;else keyboard.matrix[r]&=~b;return;}
  const [r,b]=KEYS[k];if(down)rows[r]&=~(1<<b);else rows[r]|=(1<<b);poke(VKBD+r,rows[r]);}
const inputs={}; if(INPUTS&&fs.existsSync(INPUTS))for(const l of fs.readFileSync(INPUTS,"utf8").split("\n")){const m=l.trim().match(/^(\d+)\s+(\S+)\s+(down|up)/i);if(m)(inputs[+m[1]+LAG]=inputs[+m[1]+LAG]||[]).push([m[2].toLowerCase(),m[3].toLowerCase()==="down"]);}
let FR=0,TOT=0,iterFr=[],iterCy=[];
// Цена ВХОДА в комнату (решение 4D): метрика — установившийся темп и ОТДЕЛЬНО вход.
// Ловушка: остаток «кадров − среднее×148» это в точности E + 1-я итерация, то есть
// работа комнаты, а не константа; отсюда и «21» в лёгкой 104 против 39 в остальных.
let entryFr=-1,entryAttr=-1;
let phase="menu",iter=0,steps=0,total=0; const cyc=new Float64Array(fa.length), calls=new Float64Array(fa.length), hcyc=new Float64Array(fa.length);
// Отдельные счётчики для интервала входа (от старта замера до 2-й вершины цикла), чтобы
// основная таблица «тактов/итер» оставалась байт в байт той же, что в старых логах.
const ecyc=new Float64Array(fa.length), ecalls=new Float64Array(fa.length), ehcyc=new Float64Array(fa.length);
// A8GAG=1: погасить seed_3 += mem[seed_2] (86 add a,(hl) -> 00 nop). Без этого две сборки
// с разной раскладкой кода играют РАЗНЫЙ сценарий и «тактов/итерацию» несравнимы (§14/§17.1).
if(process.env.A8GAG){ const rdb=a=>memory.bytes[memory.tobank(a&0xffff)];
  const s3=L.seed_3&0xff, s3h=(L.seed_3>>8)&0xff;
  const pat=[0x3A,s3,s3h,0x86,0x85,0x84,0x32,s3,s3h]; let at=-1;
  for(let a=0x100;a<0xF000&&at<0;a++){let ok=true;for(let i=0;i<pat.length;i++)if(rdb(a+i)!==pat[i]){ok=false;break;}if(ok)at=a;}
  if(at<0)throw new Error("не нашёл seed_3 += mem[seed_2]");
  ow(at+3,0x00,false); }
let roomSet=false;
memory.write=function(a,w,s){a&=0xffff;
  if(phase==="menu"&&cpu.pc===SYNC){poke(L.seed_1,0x34);poke(L.seed_1+1,0x12);poke(L.seed_2,0x78);poke(L.seed_2+1,0x56);poke(L.seed_3,0x9A);phase="init";}
  // A8ROOM=<байт>: подменить номер комнаты. Номер лежит в поле +8 объектов 0 и 1 и
  // пишется в init_start_location; retrieve_screen читает его позже (cp (ix+8)), поэтому
  // подменяем САМУ ЗАПИСЬ, пока не загружена первая комната (phase === "init").
  if(process.env.A8ROOM&&phase==="init"&&(a===L.graphic_objs_tbl+8||a===L.graphic_objs_tbl+40)){
    w=+process.env.A8ROOM;roomSet=true;}
  if(a===ROOM&&phase==="init"&&w!==0){phase="game";key("0",false);if(entryFr<0){entryFr=FR;entryAttr=w;}}
  if(a===SEED2HI&&phase==="game"){iter++;iterFr.push(FR);iterCy.push(TOT);for(const [k,d] of (inputs[iter]||[]))key(k,d);}
  return ow(a,w,s);};
for(let f=0;f<60;f++)v06c.oneInterrupt(true); key("0",true);
let guard=0; while(phase!=="game"&&guard++<3000)v06c.oneInterrupt(true);
if(phase!=="game")throw new Error("не дошли до комнаты");
const startIter=iter;
let ilTot=0,ilCalls=0,cur=-1,frc=0,tacc=0,lost=0,frames=0,hcyc_halt=0;
// Цена ограничителя темпа (vec_pace) отдельной строкой: код и halt порознь. Границы —
// от vec_pace до ближайшей метки за ним, не считая его внутренних (vp_*).
const PC0=L.vec_pace===undefined?-1:L.vec_pace;
const PCE=PC0<0?-1:Math.min(...Object.entries(L).filter(([n,a])=>a>PC0&&!/^vp_/.test(n)).map(([n,a])=>a));
let pcCode=0,pcHalt=0;
// Тело ISR: скан клавиатуры (vec_scan) зовут и настоящее прерывание (vec_isr), и догон (vec_cu).
// Число тел за прогон обязано равняться числу кадров — иначе ограничитель темпа и ввод отстают.
const VSCAN=L.vec_scan,VISR=L.vec_isr;
let scans=0,isrs=0,lastScanFr=0,maxScanGap=0;
while(iter-startIter<N&&steps<3e8){
  if(frc>=59904){frc-=59904;frames++;FR++;if(!cpu.iff)lost++;
    // A8_IRQDROP=1: МОДЕЛЬ ЖЕЛЕЗА. Кадровое прерывание Вектора НЕ защёлкивается: если обратный
    // ход пришёлся на di, кадр потерян НАСОВСЕМ. Без этого флага запрос ставится всегда (как
    // держит его vector06js) и любой замер «сколько стоит потеря кадра» вакуумный.
    if(!(IRQDROP&&!cpu.iff)){v06c.irq=true;v06c.checkInterrupt();}}
  const pc=cpu.pc;
  if(pc===VSCAN){scans++;const gp=FR-lastScanFr;if(gp>maxScanGap)maxScanGap=gp;lastScanFr=FR;}
  if(pc===VISR)isrs++;
  const c=(cpu.instruction(),cpu.vcycles);steps++;total+=c;TOT+=c;frc+=c;
  if(cpu.last_opcode===0x76)hcyc_halt+=c;
  if(PC0>=0&&pc>=PC0&&pc<PCE){if(cpu.last_opcode===0x76)pcHalt+=c;else pcCode+=c;}
  tacc+=c;if(tacc>1){const tn=tacc>>1;tacc-=tn*2;timer.Count(tn);}
  if(cpu.last_opcode===0xd3)io.commit();
  let i=idx(pc);if(i>=0){if(isHelper[i]){ilTot+=c;if(pc===fa[i])ilCalls++;if(cur>=0){cyc[cur]+=c;hcyc[cur]+=c;}}else{cur=i;cyc[i]+=c;if(pc===fa[i])calls[i]++;}
    if(iter<=1){ecyc[i]+=c;if(pc===fa[i])ecalls[i]++;if(isHelper[i])ehcyc[i]+=c;}}}
const iters=iter-startIter;
console.log(`IX/IY-хелперы: ${(ilTot/iters).toFixed(0)} тактов/итер (${(100*ilTot/total).toFixed(1)} % всех тактов), вызовов ${(ilCalls/iters).toFixed(1)}/итер, ${(ilTot/Math.max(1,ilCalls)).toFixed(1)} такта на обращение`);
console.log(`итераций ${iters}, инструкций ${steps}, тактов ${total}, тактов/итерацию ${(total/iters).toFixed(0)} (${(3000000/(total/iters)).toFixed(1)} итер/с на 3 МГц)`);
console.log(`кадров ${frames}, обратный ход пришёлся на di: ${lost} (${(100*lost/frames).toFixed(1)} %${IRQDROP?", A8_IRQDROP=1: эти кадры ПОТЕРЯНЫ":""}); в halt ${(hcyc_halt/iters).toFixed(0)} тактов/итер (${(100*hcyc_halt/total).toFixed(1)} %)`);
console.log(`тело ISR: ${scans} (настоящих ISR ${isrs}, догонов ${scans-isrs}) при ${frames} кадрах — недостача ${frames-scans}; макс. интервал между сканами клавиатуры ${maxScanGap} кадров`);
if(PC0>=0)console.log(`ограничитель темпа: ${(pcCode/iters).toFixed(0)} тактов/итер кода + ${(pcHalt/iters).toFixed(0)} тактов/итер halt (${(100*(pcCode+pcHalt)/total).toFixed(1)} % всего)`);
// Разброс длительности итерации в кадрах — метрика СГЛАЖЕННОСТИ темпа (§19 рецепта KL).
// Первая итерация окна — вход в комнату (десятки кадров), она исключается: иначе среднее и СКО врут.
// ЛОВУШКА: «не равны медиане» сама по себе не говорит ничего. У ограничителя эта доля равна доле
// «длинных» шагов Брезенхэма и узор РЕГУЛЯРНЫЙ; без него доля меньше, но разброс случайный.
// Смотреть надо на пару «мин/макс» и на узор.
{ const d=[];for(let i=1;i<iterFr.length;i++)d.push(iterFr[i]-iterFr[i-1]);
  const dc=[];for(let i=1;i<iterCy.length;i++)dc.push((iterCy[i]-iterCy[i-1])/59904);
  const w=d.slice(-N),wc=dc.slice(-N);
  if(w.length>1){ const t=w.slice(1),tc=wc.slice(1);
    const sr=[...t].sort((a,b)=>a-b),med=sr[sr.length>>1];
    const off=t.filter(x=>x!==med).length;
    const mean=t.reduce((a,b)=>a+b,0)/t.length,meanc=tc.reduce((a,b)=>a+b,0)/tc.length;
    const sd=Math.sqrt(tc.reduce((a,b)=>a+(b-meanc)*(b-meanc),0)/tc.length);
    const h={};for(const x of t)h[x]=(h[x]||0)+1;
    const FPS=3000000/59904;
    console.log(`длительность итерации без входа в комнату (${t.length} итер), кадров: среднее ${mean.toFixed(3)} (= ${(FPS/mean).toFixed(2)} итер/с) мин ${Math.min(...t)} макс ${Math.max(...t)} медиана ${med}, не равны медиане ${(100*off/t.length).toFixed(1)} %`);
    console.log(`  по тактам (в кадрах): среднее ${meanc.toFixed(3)} мин ${Math.min(...tc).toFixed(3)} макс ${Math.max(...tc).toFixed(3)} СКО ${sd.toFixed(3)}`);
    console.log(`  гистограмма кадров: ${Object.keys(h).map(Number).sort((a,b)=>a-b).map(k=>k+":"+h[k]).join(" ")}`);
    console.log(`  узор (первые 60): ${t.slice(0,60).map(x=>x<10?x:"+").join("")}`); } }
// Интервал «запись атрибута комнаты -> первая вершина главного цикла» — ровно то, что
// печатает ZX-стенд (zx-stand/zx_idle600.log:2 «кадр входа в комнату=393 (attr 03)
// первая итерация=кадр 398», там 5 кадров). Наш отсчёт стартует сразу после записи
// атрибута (её делает прогрев, FR там ещё 0), так что интервал сравним один в один.
{ if(entryFr>=0&&iterFr.length){
    console.log(`кадр входа в комнату=${entryFr} (attr ${entryAttr.toString(16).toUpperCase().padStart(2,"0")})  первая итерация=кадр ${iterFr[0]}  интервал=${iterFr[0]-entryFr} кадров`);
    if(iterCy.length>1)console.log(`вход в комнату: до 1-й вершины ${iterFr[0]} кадров (${iterCy[0].toFixed(0)} тактов) + 1-я итерация ${iterFr[1]-iterFr[0]} кадров (${(iterCy[1]-iterCy[0]).toFixed(0)} тактов) = ${iterFr[1]} кадров (${iterCy[1].toFixed(0)} тактов)`);
  } }
const rows_=[];for(let i=0;i<fa.length;i++)if(cyc[i]>0)rows_.push([fnm[i],cyc[i],(i+1<fa.length?fa[i+1]:0x10000)-fa[i],calls[i],hcyc[i]]);
rows_.sort((a,b)=>b[1]-a[1]);
console.log("процедура                          тактов%   тактов/итер  байт  вызовов/итер  из них IX-хелперы%");
let acc=0;for(const [n,c,sz,cl,hc] of rows_.slice(0,+(process.env.A8TOP||40))){acc+=c;console.log(`${n.padEnd(34)} ${(100*c/total).toFixed(1).padStart(6)}%  ${(c/iters).toFixed(0).padStart(10)}  ${String(sz).padStart(5)}  ${(cl/iters).toFixed(1).padStart(8)}  ${hc>0?(100*hc/c).toFixed(0)+'%':''}`);}
console.log(`(топ = ${(100*acc/total).toFixed(1)} %)`);
// Таблица процедур ВХОДА в комнату (A8_ENTRY=1): кто съедает те самые ~39 кадров.
if(process.env.A8_ENTRY&&iterCy.length>1){
  const eTot=iterCy[1]; const er=[];
  for(let i=0;i<fa.length;i++)if(ecyc[i]>0)er.push([fnm[i],ecyc[i],(i+1<fa.length?fa[i+1]:0x10000)-fa[i],ecalls[i],ehcyc[i]]);
  er.sort((a,b)=>b[1]-a[1]);
  console.log(`процедуры ВХОДА в комнату (E + 1-я итерация = ${iterFr[1]} кадров, ${eTot.toFixed(0)} тактов):`);
  console.log("процедура                          тактов%   тактов      байт  вызовов  из них IX-хелперы%");
  let eacc=0;for(const [n,c,sz,cl,hc] of er.slice(0,+(process.env.A8TOP||40))){eacc+=c;console.log(`${n.padEnd(34)} ${(100*c/eTot).toFixed(1).padStart(6)}%  ${c.toFixed(0).padStart(8)}  ${String(sz).padStart(5)}  ${cl.toFixed(1).padStart(7)}  ${hc>0?(100*hc/c).toFixed(0)+'%':''}`);}
  console.log(`(топ входа = ${(100*eacc/eTot).toFixed(1)} %)`);
}
