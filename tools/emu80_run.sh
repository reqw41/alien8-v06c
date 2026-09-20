#!/bin/sh
# Запуск сборки Alien 8 в Emu80 (порт MCP 19786, чтобы не делить 19785 с Knight Lore).
#   tools/emu80_run.sh        — build/alien8_vec.r0m на платформе vector (i8080)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP=~/projects/emu80v4/Emu80qt-mcp.app/Contents/MacOS
TMP="${TMPDIR:-/tmp}/a8_emu80"; mkdir -p "$TMP"
pkill -f "Emu80qt-mcp.*alien8" 2>/dev/null || true
PLAT=vector; IMG=alien8_vec.r0m
cp "$ROOT/build/$IMG" "$TMP/$IMG"
cd "$APP"
QT_PLUGIN_PATH=/opt/homebrew/share/qt/plugins EMU80_MCP_PORT=19786 nohup ./Emu80qt-mcp --platform $PLAT --run "$TMP/$IMG" >"$TMP/emu80.log" 2>&1 &
echo "Emu80 запущен: $PLAT $IMG (MCP порт 19786)"
