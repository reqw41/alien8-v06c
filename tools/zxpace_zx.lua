-- zxpace.lua -- ЗАМЕР ТЕМПА оригинала Alien 8 (ZX 48K) в ПРОИЗВОЛЬНОЙ комнате.
-- Урезанная копия zx_lockstep.lua из alien8-research/zx-stand: журнал состояний не снимается
-- (нужен только номер кадра на каждой итерации), зато можно подменить стартовую комнату.
--
-- Подмена: init_start_location берёт номер из таблицы start_locations (0xCA9E, 4 байта
-- {19,78,136,215}) по индексу seed_1 & 3; seed_1 прибит к 0x34 -> индекс 0. Значит достаточно
-- писать нужный номер в 0xCA9E всё время меню — ровно как SEED_FIX. Никаких тапов на запись.
--
-- Переменные окружения: A8P_ROOM (номер комнаты, по умолчанию 19 = штатная),
--   A8P_OUT (файл вывода), A8P_ITERS (итераций, по умолчанию 300).
-- Запускать из каталога zx-stand (нужен alien8_orig_det.z80 и rompath); в его каталог НЕ пишем:
--   cd ~/projects/alien8-research/zx-stand \
--   A8P_ROOM=104 A8P_OUT=<repo>/build/zxpace_104.txt SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
--   mame spectrum -rompath . -dump alien8_orig_det.z80 -video none -sound none -nothrottle \
--     -seconds_to_run 180 -snapshot_directory <repo>/build/snaps -script <repo>/tools/zxpace_zx.lua

local ROOM  = tonumber(os.getenv("A8P_ROOM") or "19")
local OUT   = os.getenv("A8P_OUT") or "zxpace.txt"
local NITER = tonumber(os.getenv("A8P_ITERS") or "300")

local SEED_FIX = { [0x5B00]=0x34, [0x5B01]=0x12, [0x5B02]=0x78, [0x5B03]=0x56, [0x5B05]=0x9A }
local START_LOCATIONS = 0xCA9E

local m    = manager.machine
local cpu  = m.devices[":maincpu"]
local prog = cpu.spaces["program"]
local pcs  = cpu.state["PC"]

local FIELD = {}
local function keyfield(k)
  if FIELD[k] then return FIELD[k] end
  local line, tok = table.unpack(k == "0" and {"LINE4","0"} or {"LINE7","SPACE"})
  for name, f in pairs(m.ioport.ports[":"..line].fields) do
    if name:match("^%S+") == tok then FIELD[k] = f; return f end
  end
  error("поле не найдено: "..k)
end

local iter, frame = -1, 0
local started, in_room, done, stall = nil, false, false, false
local first_frame, last_frame, room_attr, room_frame = nil, nil, nil, nil
local frames_at = {}                    -- кадр каждой итерации
local finished = false

ROOM_TAP = prog:install_write_tap(0x5B0D, 0x5B0D, "a8_room", function(offset, data, mask)
  if started and not in_room and data ~= 0 then
    in_room = true; room_frame = frame; room_attr = data
  end
end)

ITER_TAP = prog:install_write_tap(0x5B03, 0x5B03, "a8_iter", function(offset, data, mask)
  if not in_room or done then return end
  iter = iter + 1
  if iter >= NITER then done = true; return end
  frames_at[#frames_at+1] = frame
  if not first_frame then first_frame = frame end
  last_frame = frame
end)

local function finish()
  if finished then return end
  finished = true
  local d = {}
  for i = 2, #frames_at do d[#d+1] = frames_at[i] - frames_at[i-1] end
  -- первая итерация окна — вход в комнату, исключается (как в profile_vec.js)
  local t = {}
  for i = 2, #d do t[#t+1] = d[i] end
  local sum, mn, mx = 0, 1e9, -1
  local hist = {}
  for _, x in ipairs(t) do
    sum = sum + x
    if x < mn then mn = x end
    if x > mx then mx = x end
    hist[x] = (hist[x] or 0) + 1
  end
  local sorted = {}
  for _, x in ipairs(t) do sorted[#sorted+1] = x end
  table.sort(sorted)
  local med = sorted[math.floor(#sorted/2)+1] or 0
  local mean = #t > 0 and sum/#t or 0
  local keys = {}
  for k in pairs(hist) do keys[#keys+1] = k end
  table.sort(keys)
  local hs = {}
  for _, k in ipairs(keys) do hs[#hs+1] = k..":"..hist[k] end
  local pat = {}
  for i = 1, math.min(60, #t) do pat[#pat+1] = t[i] < 10 and tostring(t[i]) or "+" end
  local s = string.format(
    "комната=%d  attr=%02X  итераций=%d  вход в комнату=кадр %s\n"..
    "длительность итерации без входа: среднее %.3f кадра = %.2f итер/с  мин %d макс %d медиана %d\n"..
    "гистограмма кадров: %s\nузор (первые 60): %s\n%s",
    ROOM, room_attr or 0, #frames_at, tostring(room_frame),
    mean, mean > 0 and 50.0/mean or 0, mn, mx, med,
    table.concat(hs, " "), table.concat(pat),
    stall and "!!! ОБРЫВ: игра вышла из главного цикла\n" or "")
  local fl = assert(io.open(OUT, "w")); fl:write(s); fl:close()
  io.write(s)
end

local function body()
  frame = frame + 1
  if frame == 100 then keyfield("SPACE"):set_value(1) end
  if frame == 110 then keyfield("SPACE"):set_value(0) end
  if not started and pcs.value >= 0x6000 then started = frame end
  if started and not in_room then
    local k = frame - started
    if k <= 165 then
      for a, v in pairs(SEED_FIX) do prog:write_u8(a, v) end
      prog:write_u8(START_LOCATIONS, ROOM)        -- подмена стартовой комнаты
    end
    if k == 150 then keyfield("0"):set_value(1) end
    if k == 165 then keyfield("0"):set_value(0) end
  end
  if in_room and last_frame and not done and frame - last_frame > 250 then
    stall = true; done = true
  end
  if done then done = false; finish(); m:exit() end
end

emu.register_frame_done(function()
  local ok, err = pcall(body)
  if not ok then print("ERR frame:", err) end
end)
