#!/usr/bin/env node
// ГЕЙТ ПИКСЕЛЕЙ ПРОТИВ ОРИГИНАЛА ZX. Все прочие гейты картинки (render_gate) сравнивают сборку
// с ПРЕДЫДУЩЕЙ РЕВИЗИЕЙ — дефект вывода, живущий с этапа 4, проходит их насквозь. Здесь судья —
// сам ZX: дамп видеопамяти оригинала (zx-stand/zx_screen.lua) против плоскости 0 Вектора,
// снятые на ОДНОЙ И ТОЙ ЖЕ границе итерации (запись старшего байта seed_2).
//
//   node tools/zxpix_vec.js build/alien8_vec.r0m build/alien8_vec.sld <итераций> \
//        <inputs.txt> <zx_screen_<сценарий>.bin> [zx_states.bin] [метка]
//
// Журнал состояний по умолчанию — <zx_screen>.st.bin (его пишет тот же lua).
//
// ПЕРЕСЧЁТ АДРЕСА. Буфер/экран Вектора столбцовые: адрес = 0x8000 + столбец*256 + (32 + Y),
// Y растёт ВВЕРХ (calc_screen_buffer_addr в tools/a8_vec.py). У оригинала тот же Y приходит
// в BC_to_Attr_In_DE, где экранная строка считается от (~B): строка ZX = 191 - Y. Значит
//   строка Вектора (младший байт) = 32 + Y = 32 + (191 - r) = 223 - r,
// где r — пиксельная строка ZX (0 = верх). Отсюда:
//   ZX 0x4000 + ((r&0xC0)<<5) + ((r&7)<<8) + ((r&0x38)<<2) + c   <->   Вектор 0x8000 + c*256 + (223-r)
// Бит 7 в обоих — левый пиксель, байты спрайтов порт берёт у ZX как есть.
//
// СЦЕНАРИЙ ОБЯЗАН БЫТЬ ТОТ ЖЕ. Два условия, каждое проверяется прогоном:
//  1) Случайность. Игра подмешивает в seed_3 байт памяти по адресу-счётчику seed_2
//     (0x5678+iter): на ZX это её собственные переменные и код, на Векторе по этим адресам
//     лежит ДРУГОЕ. Гасить байт (A8GAG) здесь нельзя — гашение уводит сборку от настоящей
//     игры ZX. Поэтому стенд работает ОРАКУЛОМ, как lockstep_vec.js: первую запись seed_3
//     после границы итерации он подменяет значением из журнала состояний ZX. Это подмена
//     ровно того байта, который на Векторе физически другой, и ничего больше.
//  2) Ввод. Кладётся на границе итерации (vec_zxrows + vec_kbmat), со сдвигом +1 итерация,
//     как в screendiff_vec.js: иначе сборки с разным темпом читают клавиши в разные кадры.
// Проверка обоих условий — сверка тех же 1928 байт переменных, что и у локстепа: гейт
// печатает число разошедшихся итераций состояния и КРАСНЕЕТ, если они разошлись (сравнивать
// пиксели разных сценариев бессмысленно).
//
// МАСКИ (единственные осознанные различия, всё остальное — дефект):
//  1) Знакоместо, где по атрибутам ZX ЧЕРНИЛА = ФОН: пиксели там физически невидимы
//     (грабля §10 рецепта KL, штрихи sub_AD66). Маскируется, только если Вектор там НЕ
//     РИСУЕТ (байт 0): если Вектор что-то вывел, это видно на экране — и это дефект.
//  2) Итерация 1 (ключ --skip1, по умолчанию включён): на экране ещё меню, а меню порт
//     законно переписал (шесть строк вместо восьми, полоса подсветки) — то же правило,
//     что у render_gate.sh.
//
// Ключи окружения: A8PNG=<итерация|first> — выложить build/zxpix_<метка>_<N>.png «ZX | Вектор | XOR»;
// A8WATCH=lo-hi — печатать PC писателя по адресам (приём из screendiff_vec.js);
// A8_IRQDROP=1 — модель железа (прерывание не защёлкивается); A8MAXPNG — не нужен.
"use strict";
const fs=require("fs"),vm=require("vm"),cp=require("child_process");
const base="/Users/boris/projects/vector06js";
const [ROM,SLD,NS,INPUTS,ZXSCR,ZXSTA,TAGA]=process.argv.slice(2); const N=+NS||600;
if(!ROM||!SLD||!ZXSCR){console.error("нужно: <rom> <sld> <итераций> <inputs.txt> <zx_screen.bin> [zx_states.bin] [метка]");process.exit(2);}
const ZXST=ZXSTA||ZXSCR.replace(/\.bin$/,".st.bin");
const TAG=TAGA||ZXSCR.replace(/.*\//,"").replace(/^zx_screen_/,"").replace(/\.bin$/,"");
const WATCH=process.env.A8WATCH?process.env.A8WATCH.split("-").map(x=>parseInt(x,16)):null; let wn=0;
const SKIP1=process.env.A8NOSKIP1?0:1;

// ---- дампы ZX ----
const PIX=6144, ATR=768, SREC=PIX+ATR, VREC0=1928;
if(!fs.existsSync(ZXSCR))throw new Error("нет дампа экрана ZX: "+ZXSCR);
const zxs=fs.readFileSync(ZXSCR); const zxN=Math.floor(zxs.length/SREC);
if(zxN===0)throw new Error("дамп экрана ZX пуст: "+ZXSCR);
const zxv=fs.existsSync(ZXST)?fs.readFileSync(ZXST):null;
if(!zxv)throw new Error("нет журнала состояний ZX: "+ZXST+" (нужен и как оракул случайности, и как доказательство сценария)");

// ---- метки сборки ----
const L={};
for(const l of fs.readFileSync(SLD,"latin1").split("\n")){const p=l.split("|");if(p.length>=8&&p[6]==="L"){const n=p[7].split(",")[1];if(n&&!(n in L))L[n]=+p[5];}}
const SEED2HI=L.seed_2+1, ROOM=L.curr_room_attrib, VKBD=L.vkbd, SEED3=L.seed_3;
const VARS0=L.seed_1, VARS1=L.a8_vars_end, VREC=VARS1-VARS0;
if(VREC!==VREC0)throw new Error(`блок переменных ${VREC} Б, а в журнале ZX ${VREC0}`);
const lst=fs.readFileSync(ROM.replace(/\.r0m$/,".lst"),"latin1").split("\n");
let SYNC=-1;for(const l of lst){const m=l.match(/^\s*\d+\+?\s+([0-9A-F]{4})\s.*\s+call\s+init_start_location/);if(m){SYNC=parseInt(m[1],16);break;}}
if(SYNC<0)throw new Error("не нашёл call init_start_location в листинге");
// указатели: их значения зависят от раскладки памяти, сверять с ZX нельзя (тот же список, что в lockstep_vec.js)
const PTRS=["tmp_SP","gfxbase_8x8","tmp_objects_to_draw","render_obj_1","render_obj_2","block_type_tbl_base","word_5B34"];
const IGN=new Set();for(const n of PTRS){const o=L[n]-VARS0;IGN.add(o);IGN.add(o+1);}
const names=Object.entries(L).filter(([n,a])=>a>=VARS0&&a<VARS1).sort((x,y)=>x[1]-y[1]);
const nameOf=off=>{let best="?";for(const [n,a] of names){if(a-VARS0<=off)best=n+"+"+(off-(a-VARS0));}return best;};
// БИТЫ СОСТОЯНИЯ, КОТОРЫМ РАЗРЕШЕНО ОТЛИЧАТЬСЯ (каждый — с доказательством, а не «на всякий случай»).
//   user_input бит 5. На ZX он взводится, если нажата ЛЮБАЯ клавиша рядов 1,2,5,6 или Z X C V
//   SYM M N B (`read_key 0x7E and 0x1E` / `read_key 0x99` в keyboard:), то есть почти любая буква.
//   Порт читает раскладку прямо из матрицы Вектора (a8_vec_input), и бит 5 там ставят только цифры
//   раскладки 3 DIRECTIONAL. В раскладке 1 (user_input_method = 0, с которой идут все сценарии)
//   бит 5 НИКТО НЕ ЧИТАЕТ: единственный его читатель — chk_pickup_drop/handle_left_right под
//   `bit 3,(user_input_method)`, а он в этой раскладке нулевой. Доказательство не рассуждением,
//   а прогоном: с этой маской 600 итераций трёх сценариев совпадают с ZX во ВСЕХ остальных
//   1927 байтах — если бы бит что-то менял, разъехалось бы и остальное.
const STBITS=new Map([[L.user_input-VARS0,0x20]]);

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
// джойстик Вектора (порт 0x0E): в vector06js собирается из матрицы — подменяем на покой
{ const _rd=io.input.bind(io); io.input=p=>((p&0xFF)===0x0E?0xFF:_rd(p)); }
const cpu=new ctx.I8080(memory,io),tape={advance:()=>{},sample:0,reset:()=>{}},v06c=new ctx.Vector06c(cpu,memory,io,ay,tape);
v06c.bmp=new Uint32Array(576*288);v06c.displayFrame=()=>{};v06c.check_breakpoint=()=>false;v06c.dbg=null;
memory.init_from_array(new Uint8Array(fs.readFileSync(ROM)).subarray(0,0x10000),0);memory.detach_boot&&memory.detach_boot();
cpu.pc=0;cpu.sp=0x8000;cpu.iff=false;
const rd=a=>memory.bytes[memory.tobank(a&0xffff)];
const ow=memory.write.bind(memory); const poke=(a,v)=>ow(a&0xffff,v&0xff,false);

// ---- ввод: ряды ZX + матрица Вектора, кладутся на границе итерации (как в screendiff_vec.js) ----
const KEYS={z:[0,1],x:[0,2],a:[1,0],q:[2,0],"0":[4,0],space:[7,0]}; const rows=new Uint8Array(8).fill(0xFF);
const VKEYS={z:[7,0x04],x:[7,0x01],a:[4,0x02],q:[6,0x02],"0":[2,0x01],space:[7,0x80]};
const ZXROWS=(VKBD===undefined&&L.vec_zxbuild!==undefined)?L.vec_zxrows:undefined;
const KBMAT=(ZXROWS!==undefined&&L.vec_scan!==undefined)?L.vec_kbmat:undefined;
if(ZXROWS!==undefined){memory.write(L.vec_zxbuild,0xC9,false);
  for(let r=0;r<8;r++)memory.write(ZXROWS+r,0xFF,false);}
const kbm=new Uint8Array(8);
if(KBMAT!==undefined){memory.write(L.vec_scan,0xC9,false);
  for(let r=0;r<8;r++)memory.write(KBMAT+r,0,false);}
function key(k,down){
  if(VKBD===undefined&&ZXROWS===undefined){const [r,b]=VKEYS[k];if(down)keyboard.matrix[r]|=b;else keyboard.matrix[r]&=~b;return;}
  if(KBMAT!==undefined){const [vr,vb]=VKEYS[k];if(down)kbm[vr]|=vb;else kbm[vr]&=~vb;poke(KBMAT+vr,kbm[vr]);}
  const [r,b]=KEYS[k];if(down)rows[r]&=~(1<<b);else rows[r]|=(1<<b);poke((VKBD!==undefined?VKBD:ZXROWS)+r,rows[r]);}
const inputs={};
if(INPUTS&&fs.existsSync(INPUTS))for(const l of fs.readFileSync(INPUTS,"utf8").split("\n")){
  const m=l.trim().match(/^(\d+)\s+(\S+)\s+(down|up)/i);if(m)(inputs[+m[1]+1]=inputs[+m[1]+1]||[]).push([m[2].toLowerCase(),m[3].toLowerCase()==="down"]);}

// ---- сравнение картинки ----
// ZX-адрес пикселя: строка r (0 = верх), столбец c
const zxaddr=new Int32Array(192*32);
for(let r=0;r<192;r++)for(let c=0;c<32;c++)zxaddr[r*32+c]=((r&0xC0)<<5)+((r&7)<<8)+((r&0x38)<<2)+c;
const VECADDR=(r,c)=>0x8000+c*256+(223-r);

let firstIter=-1,firstBytes=0,badIters=0,totalBad=0,stBad=0,stFirst=-1;
const stHist=new Map();   // смещение в блоке переменных -> на скольких итерациях разошлось
const maskedHits={n:0};          // сколько раз маска «чернила = фон» спасла расхождение
const worst={iter:-1,n:0};
const PNGWANT=process.env.A8PNG||"";
let pngDone=false;

function compare(iter,zxoff){
  const pix=zxs.subarray(zxoff,zxoff+PIX), atr=zxs.subarray(zxoff+PIX,zxoff+SREC);
  let bad=0; const where=[];
  for(let r=0;r<192;r++){
    const cell=(r>>3)*32;
    for(let c=0;c<32;c++){
      const z=pix[zxaddr[r*32+c]], v=rd(VECADDR(r,c));
      if(z===v)continue;
      const a=atr[cell+c];
      if((a&7)===((a>>3)&7)){         // чернила = фон: на ZX пиксели невидимы
        if(v===0){maskedHits.n++;continue;}   // Вектор там ничего не рисует — законно
      }
      bad++; if(where.length<12)where.push({r,c,z,v,a:atr[cell+c]});
    }
  }
  return {bad,where};
}

function dumpPNG(iter,zxoff){
  const pix=zxs.subarray(zxoff,zxoff+PIX);
  const W=256*3+16,H=192; const img=new Uint8Array(W*H).fill(64);
  for(let r=0;r<192;r++)for(let c=0;c<32;c++){
    const z=pix[zxaddr[r*32+c]], v=rd(VECADDR(r,c)), x=z^v;
    for(let k=0;k<8;k++){
      const b=7-k;
      img[r*W+c*8+k]=(z>>b)&1?255:0;
      img[r*W+256+8+c*8+k]=(v>>b)&1?255:0;
      img[r*W+512+16+c*8+k]=(x>>b)&1?255:0;
    }
  }
  const pgm=`build/zxpix_${TAG}_${iter}.pgm`, png=pgm.replace(/\.pgm$/,".png");
  fs.writeFileSync(pgm,Buffer.concat([Buffer.from(`P5\n${W} ${H}\n255\n`),Buffer.from(img)]));
  try{cp.execFileSync("python3",["tools/pgm2png.py",pgm,png]);console.log(`картинка «ZX | Вектор | XOR» -> ${png}`);}
  catch(e){console.log(`картинка -> ${pgm} (pgm2png не отработал: ${e.message})`);}
}

// ---- прогон ----
let phase="menu",iter=0,cmp=0,seed3pend=-1;
memory.write=function(a,w,s){a&=0xffff;
  if(WATCH&&a>=WATCH[0]&&a<=WATCH[1]&&wn++<30)console.log(`WATCH iter ${iter} pc=${cpu.pc.toString(16)} ${a.toString(16)} <- ${w.toString(16)} (was ${memory.read(a,false).toString(16)})`);
  if(phase==="menu"&&cpu.pc===SYNC){poke(L.seed_1,0x34);poke(L.seed_1+1,0x12);poke(L.seed_2,0x78);poke(L.seed_2+1,0x56);poke(L.seed_3,0x9A);phase="init";}
  if(a===ROOM&&phase==="init"&&w!==0){phase="game";key("0",false);}
  // ОРАКУЛ СЛУЧАЙНОСТИ: первая запись seed_3 после границы итерации = результат
  // `seed_3 += mem[seed_2] + L + H`, где mem[seed_2] на Векторе физически другой байт.
  // Подменяем результат значением ZX следующей записи журнала.
  if(a===SEED3&&seed3pend>=0){w=seed3pend;seed3pend=-1;}
  if(a===SEED2HI&&phase==="game"){
    iter++;
    // 1) состояние: тот ли сценарий
    if(iter<=zxN){
      const z=zxv.subarray((iter-1)*VREC,iter*VREC);
      const dif=i=>(z[i]^rd(VARS0+i))&~(STBITS.get(i)||0);
      let bad=0;for(let i=0;i<VREC;i++)if(!IGN.has(i)&&dif(i)){bad++;stHist.set(i,(stHist.get(i)||0)+1);}
      if(bad){stBad++;if(stFirst<0){stFirst=iter;
        const d=[];for(let i=0;i<VREC&&d.length<12;i++)if(!IGN.has(i)&&dif(i))d.push(`${nameOf(i)}(+${i.toString(16)}): zx=${z[i].toString(16)} vec=${rd(VARS0+i).toString(16)}`);
        console.log(`СОСТОЯНИЕ разошлось на итерации ${iter} (сценарии разные, пиксели сравнивать нельзя):\n  `+d.join("\n  "));}}
    }
    // 2) пиксели
    if(iter<=zxN&&iter>SKIP1){
      const {bad,where}=compare(iter,(iter-1)*SREC);
      cmp++;
      if(bad){badIters++;totalBad+=bad;
        if(bad>worst.n){worst.n=bad;worst.iter=iter;}
        if(firstIter<0){firstIter=iter;firstBytes=bad;
          console.log(`ПЕРВОЕ РАСХОЖДЕНИЕ ПИКСЕЛЕЙ: итерация ${iter}, байт ${bad}`);
          for(const w2 of where)console.log(`  столбец ${w2.c} (x=${w2.c*8}), строка ZX ${w2.r} (Вектор ${223-w2.r}): zx=${w2.z.toString(2).padStart(8,"0")} vec=${w2.v.toString(2).padStart(8,"0")} attr=${w2.a.toString(16)}`);
          if(PNGWANT==="first"||+PNGWANT===iter){dumpPNG(iter,(iter-1)*SREC);pngDone=true;}}
      }
      if(!pngDone&&+PNGWANT===iter){dumpPNG(iter,(iter-1)*SREC);pngDone=true;}
    }
    // 3) ввод этой итерации
    for(const [k,d] of (inputs[iter]||[]))key(k,d);
    // 4) оракул на следующую запись seed_3
    if(iter<zxN)seed3pend=zxv[iter*VREC+5];
  }
  return ow(a,w,s);};

for(let f=0;f<60;f++)v06c.oneInterrupt(true); key("0",true);
let guard=0; while(phase!=="game"&&guard++<3000)v06c.oneInterrupt(true);
if(phase!=="game")throw new Error("не дошли до комнаты");
const startIter=iter; let steps=0,frc=0,tacc=0;
const IRQDROP=!!process.env.A8_IRQDROP;
while(iter-startIter<N&&steps<6e8){if(frc>=59904){frc-=59904;if(!(IRQDROP&&!cpu.iff)){v06c.irq=true;v06c.checkInterrupt();}}
  const c=(cpu.instruction(),cpu.vcycles);steps++;frc+=c;tacc+=c;if(tacc>1){const tn=tacc>>1;tacc-=tn*2;timer.Count(tn);}if(cpu.last_opcode===0xd3)io.commit();}

// ---- вердикт ----
console.log(`сценарий ${TAG}: итераций ${iter}, сравнено ${cmp} (из ${Math.min(N,zxN)}, итерация 1 ${SKIP1?"пропущена (меню)":"включена"})`);
console.log(`состояние: расхождений итераций ${stBad}${stFirst>0?`, первое на ${stFirst}`:""}`);
if(stHist.size){const top=[...stHist.entries()].sort((a,b)=>b[1]-a[1]).slice(0,10);
  console.log("  ячейки: "+top.map(([o,n])=>`${nameOf(o)}(+${o.toString(16)}) x${n}`).join(", "));}
console.log(`маска «чернила = фон» (Вектор не рисует): ${maskedHits.n} байт за прогон`);
if(cmp===0){console.log("ПУСТАЯ ВЫБОРКА: сравнивать было нечего");process.exit(1);}
if(stBad){console.log("КРАСНЫЙ: сценарий Вектора разошёлся с ZX — пиксельный вердикт недействителен");process.exit(1);}
if(badIters){
  console.log(`КРАСНЫЙ: пиксели разошлись на ${badIters} итерациях из ${cmp}, всего ${totalBad} байт; первая ${firstIter} (${firstBytes} Б), худшая ${worst.iter} (${worst.n} Б)`);
  process.exit(1);}
console.log(`ЗЕЛЁНЫЙ: ${cmp} итераций пиксель в пиксель с оригиналом ZX`);
