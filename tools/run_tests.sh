#!/bin/bash
# Runs the full AT20 MPC validation, upstream bit-exact comparison, CPU benchmark, and host_sim suite.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MPC_SDK="${MPC_SDK:-}"
AT20V_UPSTREAM="${AT20V_UPSTREAM:-$ROOT/third_party/audio_tools}"

BUILD_TMP="$ROOT/build_tests"
mkdir -p "$BUILD_TMP"

echo "== 1/4: DSP, Patchbay & 56-Preset Validation Suite =="
clang++ -std=c++17 -O2 -Wall -Wextra "$ROOT/tests/validate_dsp.cpp" -o "$BUILD_TMP/validate_dsp"
"$BUILD_TMP/validate_dsp"

if [ -d "$AT20V_UPSTREAM/plugins/at20v/Source" ]; then
  echo ""
  echo "== 2/4: Upstream AT20V Reference vs Ported AT20 MPC Comparison =="
  clang++ -std=c++17 -O2 -Ddh=dh_ref -c -I"$AT20V_UPSTREAM/plugins/at20v/Source" -I"$AT20V_UPSTREAM/shared/dsp" \
    "$ROOT/tests/ref_renderer.cpp" -o "$BUILD_TMP/ref_renderer.o"
  clang++ -std=c++17 -O2 -Ddh=dh_port -c "$ROOT/tests/port_renderer.cpp" -o "$BUILD_TMP/port_renderer.o"
  clang++ -std=c++17 -O2 "$ROOT/tests/compare_upstream.cpp" \
    "$BUILD_TMP/ref_renderer.o" "$BUILD_TMP/port_renderer.o" -o "$BUILD_TMP/compare_upstream"
  "$BUILD_TMP/compare_upstream"
fi

echo ""
echo "== 3/4: CPU Performance Benchmark =="
clang++ -std=c++17 -O2 -Wall -Wextra "$ROOT/tests/bench_cpu.cpp" -o "$BUILD_TMP/bench_cpu"
"$BUILD_TMP/bench_cpu"

if [ -x "$MPC_SDK/.sdk-tools/host_sim" ]; then
  echo ""
  echo "== 4/5: End-to-End VST2 Patchbay & Effect Integration Test =="
  clang++ -std=c++17 -O2 -Wall -Wextra -I"$MPC_SDK/framework" "$ROOT/tests/test_vst_patchbay.cpp" -o "$BUILD_TMP/test_vst_patchbay"
  "$BUILD_TMP/test_vst_patchbay" \
    "$ROOT/plugins/at20_mpc/build/native/twenty.dylib" \
    "$ROOT/plugins/at20_fx/build/native/twenty-fx.dylib"

  echo ""
  echo "== 5/5: Official Akai SDK host_sim Verification =="
  "$MPC_SDK/.sdk-tools/host_sim" "$ROOT/plugins/at20_mpc/build/native/twenty.dylib" test \
    --wav "$BUILD_TMP/at20_mpc_test.wav"
  "$MPC_SDK/.sdk-tools/host_sim" "$ROOT/plugins/at20_fx/build/native/twenty-fx.dylib" test \
    --wav "$BUILD_TMP/at20_fx_test.wav"
fi
