#!/usr/bin/env node
// ГЕЙТ «ПАЛИТРА МЕНЯЕТСЯ ТОЛЬКО НА ЧЁРНОМ ЭКРАНЕ» (и он же — замерщик последовательности).
//
//   A8_IRQDROP=1 node tools/palseq_vec.js build/alien8_vec.r0m build/alien8_vec.sld \
//        <итераций> [inputs1.txt[,inputs2.txt...]]
//   A8PALTRACE=1 ...   — печатать последовательность ПО КАДРАМ вокруг каждой смены комнаты
//
// ЧТО ЗА ДЕФЕКТ. На Векторе экран (плоскость 0) перерисовывается столбцами ~2.4 кадра, а цвет
// комнаты — это ПАЛИТРА, она меняется мгновенно и целиком. Поэтому любая запись палитры в кадре,
// когда на экране что-то есть, — это ПЕРЕКРАСКА УЖЕ НАРИСОВАННОЙ КАРТИНКИ, и владелец видит
// смену цвета не в тот момент: либо старая комната вспыхивает новым цветом, либо новая комната
// появляется в старом и цвет догоняет её через два кадра. На ZX этого нет: там clear_scrn гасит
// пиксели, а атрибуты (colour_something) ложатся на чёрный экран до update_screen.
//
// КРИТЕРИЙ (нарушение = кадр, в котором):
//   1) записи палитры 8..15 (цвет комнаты: индекс 8..15 = точка в плоскости 0 есть) отличаются
//      от прошлого кадра, И
//   2) плоскость 0 в окне строк 32..223 всех 32 столбцов НЕ ПУСТА (есть ненулевой байт).
// ИСКЛЮЧЕНИЕ (одно, доказанное исходником ZX): перекраска ТОЙ ЖЕ комнаты. На пути «собран
// кусок головоломки» (src/alien8_zx.asm, loc_AFF8: мигание атрибутами -> curr_room_attrib := 7 ->
// colour_something) оригинал МЕНЯЕТ ЦВЕТ КОМНАТЫ, НЕ СТИРАЯ ЭКРАН, — это эффект, а не дефект.
// Признак: curr_room_attrib изменился, а номер комнаты (graphic_objs_tbl+8) с прошлой полной
// перерисовки — нет. Такие кадры печатаются отдельной строкой и нарушением не считаются.
//
// ВЫБОРКА. Гейт обязан увидеть не меньше трёх смен комнаты и одной гибели — иначе он ничего не
// проверил и КРАСНЕЕТ (пустая выборка). По умолчанию гоняются два сценария стенда:
// inputs_walk.txt (четыре комнаты) и inputs_alive.txt (гибель в стартовой).
//
// A8GAG. Как в profile_vec.js: seed_3 += mem[seed_2] гасится, иначе две сборки с разной
// раскладкой кода играют РАЗНЫЙ сценарий и последовательности «до/после» несравнимы.
"use strict";
const fs=require("fs"),vm=require("vm");
const base="/Users/boris/projects/vector06js";
const HOME=process.env.HOME+"/projects/alien8-research/zx-stand/";
const [ROM,SLD,NS,INPA]=process.argv.slice(2); const N=+NS||600;
if(!ROM||!SLD){console.error("нужно: <rom> <sld> [итераций] [inputs1.txt,inputs2.txt]");process.exit(2);}
const LAG=+(process.env.A8_LAG||1);
const IRQDROP=!!process.env.A8_IRQDROP;
const TRACE=!!process.env.A8PALTRACE;
const SCEN=(INPA||(HOME+"inputs_walk.txt,"+HOME+"inputs_alive.txt")).split(",").filter(Boolean);

// ---- метки ----
const L={};
for(const l of fs.readFileSync(SLD,"latin1").split("\n")){const p=l.split("|");if(p.length>=8&&p[6]==="L"){const n=p[7].split(",")[1];if(n&&!(n in L))L[n]=+p[5];}}
const SEED2HI=L.seed_2+1, ROOMATTR=L.curr_room_attrib, VKBD=L.vkbd, OBJ=L.graphic_objs_tbl;
const lst=fs.readFileSync(ROM.replace(/\.r0m$/,".lst"),"latin1").split("\n");
let SYNC=-1;for(const l of lst){const m=l.match(/^\s*\d+\+?\s+([0-9A-F]{4})\s.*\s+call\s+init_start_location/);if(m){SYNC=parseInt(m[1],16);break;}}
if(SYNC<0)throw new Error("не нашёл call init_start_location");
if(L.us_sp===undefined)throw new Error("нет метки us_sp (конец update_screen)");
// карта наблюдаемых PC: 1 clear_scrn, 2 update_screen (вход), 3 update_screen (ret), 4 clear_scrn_buffer,
// 5 vec_set_pal, 6 colour_something, 7 lose_life, 8 vec_wipe0 (может не быть — до правки)
const WPC=new Uint8Array(0x10000);
const put=(n,c)=>{if(L[n]!==undefined)WPC[L[n]]=c;};
put("clear_scrn",1);put("update_screen",2);WPC[L.us_sp-1]=3;put("clear_scrn_buffer",4);
put("vec_set_pal",5);put("colour_something",6);put("lose_life",7);put("vec_wipe0",8);
const EVCH=["","C","U","u","B","P","L","D","W"];   // буквы событий в трассе

// ---- ядро vector06js ----
const g={};g.window=g;g.document={createElement:()=>fc(),getElementById:()=>fc()};
function fcx(){return{createImageData:()=>({data:new Uint8ClampedArray(4)}),putImageData:()=>{},getImageData:()=>({data:new Uint8ClampedArray(4)}),fillRect(){},drawImage(){}};}
function fc(){return{width:0,height:0,style:{},getContext:()=>fcx()};}
g.requestAnimationFrame=()=>0;g.setTimeout=()=>0;g.print=()=>0;g.console={log(){},debug(){},warn(){},error(){},info(){}};
const ctx=vm.createContext(g);
for(const f of ["i8080-js/i8080_trace.js","i8080-js/i8080_disasm.js","i8080-js/i8080.js","src/fili.js","src/ay.js","src/fd1793.js","src/fddimage.js","src/i8253.js","src/io.js","src/keyboard.js","src/memory.js","src/sound.js","src/tv.js"])
  vm.runInContext(fs.readFileSync(base+"/"+f,"utf8"),ctx,{filename:f});
const memory=new ctx.Memory(),keyboard=new ctx.Keyboard(),timer=new ctx.I8253(),ay=new ctx.AY(),
      floppy=new(ctx.Floppy().FD1793)(),io=new ctx.IO(keyboard,timer,memory,ay,floppy);
{ const _rd=io.input.bind(io); io.input=p=>((p&0xFF)===0x0E?0xFF:_rd(p)); }   // джойстик в покое
// ПАЛИТРА: на живом Векторе запись порта 0x0C защёлкивается цветом под лучом, то есть индексом
// из порта 0x02 (кайма). Растр в стенде не крутится, поэтому защёлку моделируем сами — ровно так,
// как её делает ISR порта (§4.17 рецепта): индекс = последняя запись 0x02, значение = запись 0x0C.
const PAL=new Uint8Array(16);
let palIdx=0, palWrites=0;
{ const _out=io.output.bind(io);
  io.output=(p,w)=>{p&=0xFF;if(p===0x02)palIdx=w&0x0F;else if(p===0x0C){PAL[palIdx]=w&0xFF;palWrites++;}return _out(p,w);}; }
const cpu=new ctx.I8080(memory,io),tape={advance:()=>{},sample:0,reset:()=>{}},v06c=new ctx.Vector06c(cpu,memory,io,ay,tape);
v06c.bmp=new Uint32Array(576*288);v06c.displayFrame=()=>{};v06c.check_breakpoint=()=>false;v06c.dbg=null;
const IMG=new Uint8Array(fs.readFileSync(ROM)).subarray(0,0x10000);
const rd=a=>memory.bytes[memory.tobank(a&0xffff)];
const KEYS={shift:[0,0],z:[0,1],x:[0,2],c:[0,3],v:[0,4],a:[1,0],s:[1,1],d:[1,2],f:[1,3],g:[1,4],q:[2,0],w:[2,1],e:[2,2],r:[2,3],t:[2,4],
  "1":[3,0],"2":[3,1],"3":[3,2],"4":[3,3],"5":[3,4],"0":[4,0],"9":[4,1],"8":[4,2],"7":[4,3],"6":[4,4],p:[5,0],o:[5,1],i:[5,2],u:[5,3],y:[5,4],
  enter:[6,0],l:[6,1],k:[6,2],j:[6,3],h:[6,4],space:[7,0],sym:[7,1],m:[7,2],n:[7,3],b:[7,4]};
const VKEYS={z:[7,0x04],x:[7,0x01],a:[4,0x02],q:[6,0x02],"0":[2,0x01],space:[7,0x80]};

// плоскость 0: окно строк 32..223 всех 32 столбцов (то же окно, что пишет update_screen)
function plane0nz(){let n=0;
  for(let c=0;c<32;c++){const b=0x8000+c*256;for(let y=32;y<224;y++)if(rd(b+y))n++;}
  return n;}
const palStr=()=>{let s="";for(let i=15;i>=8;i--)s+=PAL[i].toString(16).padStart(2,"0");return s;};

const res={rooms:0,deaths:0,frames:0,bad:[],excs:[],scen:[]};

function run(inputsFile,tag){
  memory.init_from_array(IMG,0);memory.detach_boot&&memory.detach_boot();
  cpu.pc=0;cpu.sp=0xBC00;cpu.iff=false;PAL.fill(0);palIdx=0;
  for(let r=0;r<8;r++)keyboard.matrix[r]=0;
  const ow=memory.write.bind(memory); const poke=(a,v)=>ow(a&0xffff,v&0xff,false);
  if(VKBD!==undefined)for(let r=0;r<8;r++)ow(VKBD+r,0xFF,false);
  const rows=new Uint8Array(8).fill(0xFF);
  const key=(k,down)=>{if(VKBD===undefined){const v=VKEYS[k];if(!v)return;const [r,b]=v;if(down)keyboard.matrix[r]|=b;else keyboard.matrix[r]&=~b;return;}
    const [r,b]=KEYS[k];if(down)rows[r]&=~(1<<b);else rows[r]|=(1<<b);poke(VKBD+r,rows[r]);};
  { const s3=L.seed_3&0xff,s3h=(L.seed_3>>8)&0xff;         // A8GAG всегда: сценарий обязан быть тот же
    const pat=[0x3A,s3,s3h,0x86,0x85,0x84,0x32,s3,s3h];let at=-1;
    for(let a=0x100;a<0xF000&&at<0;a++){let ok=true;for(let i=0;i<pat.length;i++)if(rd(a+i)!==pat[i]){ok=false;break;}if(ok)at=a;}
    if(at<0)throw new Error("не нашёл seed_3 += mem[seed_2]");ow(at+3,0x00,false);}
  const inputs={};
  if(inputsFile&&fs.existsSync(inputsFile))for(const l of fs.readFileSync(inputsFile,"utf8").split("\n")){
    const m=l.trim().match(/^(\d+)\s+(\S+)\s+(down|up)/i);if(m)(inputs[+m[1]+LAG]=inputs[+m[1]+LAG]||[]).push([m[2].toLowerCase(),m[3].toLowerCase()==="down"]);}
  let phase="menu",iter=0,attrChg=false;
  memory.write=function(a,w,s){a&=0xffff;
    if(phase==="menu"&&cpu.pc===SYNC){poke(L.seed_1,0x34);poke(L.seed_1+1,0x12);poke(L.seed_2,0x78);poke(L.seed_2+1,0x56);poke(L.seed_3,0x9A);phase="init";}
    if(a===ROOMATTR&&phase==="init"&&w!==0){phase="game";key("0",false);}
    if(a===ROOMATTR&&phase==="game"&&w!==rd(a))attrChg=true;   // сменился цвет комнаты (в т.ч. light-year)
    if(a===SEED2HI&&phase==="game"){iter++;for(const [k,d] of (inputs[iter]||[]))key(k,d);}
    return ow(a,w,s);};
  for(let f=0;f<60;f++)v06c.oneInterrupt(true); key("0",true);
  let guard=0; while(phase!=="game"&&guard++<3000)v06c.oneInterrupt(true);
  if(phase!=="game")throw new Error("не дошли до комнаты: "+tag);

  const start=iter; let steps=0,frc=0,tacc=0,fr=0;
  let ev=0, prevPal=palStr(), room=rd(OBJ+8), shownRoom=room, roomChg=0, deaths=0;
  let lastChgFr=0, log=[], bad=0, exc=0;   // окно трассы: с нулевого кадра (вход в первую комнату)
  const flush=()=>{if(TRACE&&log.length){for(const s of log)console.log(s);log=[];}};
  while(iter-start<N&&steps<6e8){
    if(frc>=59904){frc-=59904;fr++;
      if(!(IRQDROP&&!cpu.iff)){v06c.irq=true;v06c.checkInterrupt();}
      // ---- срез кадра ----
      const p=palStr(), nz=plane0nz(), r=rd(OBJ+8);
      if(r!==room){room=r;roomChg++;lastChgFr=fr;}
      const chg=(p!==prevPal);
      let mark="";
      if(chg){
        if(nz>0){
          // перекраска той же комнаты (light-year): картинка на экране — ТЕКУЩЕЙ комнаты,
          // а curr_room_attrib поменялся сам. Оригинал ZX делает ровно это (loc_AFF8).
          if(room===shownRoom&&attrChg){mark="ПЕРЕКРАСКА ТОЙ ЖЕ КОМНАТЫ (light-year, законно)";exc++;
            res.excs.push(`${tag}: кадр ${fr}, итерация ${iter}, комната ${room}, ${prevPal}->${p}`);}
          else{mark="НАРУШЕНИЕ: палитра сменилась на НЕПУСТОМ экране";bad++;
            res.bad.push(`${tag}: кадр ${fr}, итерация ${iter}, комната ${room} (на экране ${shownRoom}), `+
                         `непустых байт ${nz}, палитра ${prevPal} -> ${p}`);}
        } else mark="палитра на ЧЁРНОМ экране — законно";
        attrChg=false;
      }
      if(TRACE){
        // окно вокруг смены комнаты: печатаем только кадры С СОБЫТИЕМ (вызов процедуры вывода
        // или смена палитры) — между ними кадр в кадр одно и то же, и список не читается
        const inWin=((fr-lastChgFr)<=80&&(ev!==0||fr===lastChgFr))||chg;
        const evs=[];for(let i=1;i<=8;i++)if(ev&(1<<i))evs.push(EVCH[i]);
        if(inWin)log.push(`  ${tag} кадр ${String(fr).padStart(5)} итер ${String(iter).padStart(4)}`+
          ` комн ${String(room).padStart(3)} pal8..15 ${p} байт ${String(nz).padStart(5)}`+
          ` [${evs.join("")||"-"}] ${mark}`);
        if(log.length>400)flush();
      }
      if(ev&(1<<3))shownRoom=room;     // update_screen дошёл до ret: на экране картинка этой комнаты
      if(ev&(1<<3))attrChg=false;
      prevPal=p; ev=0; res.frames++;
    }
    const w=WPC[cpu.pc]; if(w){ev|=1<<w;if(w===7){deaths++;lastChgFr=fr;}}   // гибель тоже открывает окно трассы
    const c=(cpu.instruction(),cpu.vcycles);steps++;frc+=c;
    tacc+=c;if(tacc>1){const tn=tacc>>1;tacc-=tn*2;timer.Count(tn);}
    if(cpu.last_opcode===0xd3)io.commit();
  }
  flush();
  res.rooms+=roomChg;res.deaths+=deaths;
  res.scen.push(`${tag}: итераций ${iter-start}, кадров ${fr}, смен комнаты ${roomChg}, гибелей ${deaths}, `+
                `нарушений ${bad}, законных перекрасок ${exc}`);
}

for(const s of SCEN)run(s,s.replace(/.*\//,"").replace(/^inputs_/,"").replace(/\.txt$/,""));

console.log(`палитра: записей порта 0x0C ${palWrites}, кадров ${res.frames}`);
for(const s of res.scen)console.log("  "+s);
if(res.excs.length){console.log(`законных перекрасок той же комнаты: ${res.excs.length}`);
  for(const s of res.excs.slice(0,10))console.log("  "+s);}
if(res.rooms<3||res.deaths<1){
  console.log(`ПУСТАЯ ВЫБОРКА: смен комнаты ${res.rooms} (нужно >= 3), гибелей ${res.deaths} (нужно >= 1)`);
  process.exit(1);}
if(res.bad.length){
  console.log(`КРАСНЫЙ: палитра сменилась при непустом экране в ${res.bad.length} кадрах`);
  for(const s of res.bad.slice(0,20))console.log("  "+s);
  process.exit(1);}
console.log(`ЗЕЛЁНЫЙ: ${res.frames} кадров, ${res.rooms} смен комнаты, ${res.deaths} гибелей — `+
            `каждая запись палитры пришлась на пустую плоскость 0`);
