#!/bin/bash
# Reproducible full build & packaging script for AT20 MPC and AT20 FX.
# Requires the official Akai MPC Plugin Builder SDK (set MPC_SDK or use default).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MPC_SDK="${MPC_SDK:-}"

if [ ! -f "$MPC_SDK/tools/build.py" ]; then
  echo "ERROR: Official Akai MPC Plugin Builder SDK not found at: $MPC_SDK" >&2
  echo "Clone https://github.com/inmusic-software/mpc-plugin-builder-sdk and set MPC_SDK=/path/to/sdk" >&2
  exit 1
fi

echo "== 1/4: Generating UI artwork & MPC skins =="
python3 "$ROOT/tools/gen_ui_assets.py"
python3 "$ROOT/tools/gen_skins.py"
python3 "$ROOT/tools/render_preview.py"

echo "== 2/4: Building AT20 MPC (native + ARM32 + ARM64 + validate) =="
python3 "$MPC_SDK/tools/build.py" "$ROOT/plugins/at20_mpc"

echo "== 3/4: Building AT20 FX (native + ARM32 + ARM64 + validate) =="
python3 "$MPC_SDK/tools/build.py" "$ROOT/plugins/at20_fx"

echo "== 4/4: Packaging deployable ZIP bundles =="
mkdir -p "$ROOT/dist"
python3 "$MPC_SDK/tools/package.py" "$ROOT/plugins/at20_mpc" --out "$ROOT/dist"
python3 "$MPC_SDK/tools/package.py" "$ROOT/plugins/at20_fx" --out "$ROOT/dist"

echo ""
echo "Deployable folders:"
echo "  $ROOT/plugins/at20_mpc/build/Stampman3000 - VST - Twenty"
echo "  $ROOT/plugins/at20_fx/build/Stampman3000 - VST - Twenty FX"
echo "Deployable ZIPs:"
ls -lh "$ROOT/dist"/*.zip
