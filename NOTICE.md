# Attribution, Licensing & Upstream Source Record

## Licence

**Twenty** (`TWNT`) and **Twenty FX** (`TWFX`) by Stampman3000 are distributed under the **GNU Affero General Public License v3.0 (or later)** (`AGPL-3.0-or-later`), matching the upstream licence of Audio Tools AT20V. See [LICENSE](LICENSE) for the full licence text.

## Upstream Source Attribution

- **Original project:** Audio Tools **AT20V** (open-source Korg MS-20 recreation)
- **Author / Maintainer:** Audio Tools (`palmereta/audio_tools`)
- **MPC Adaptation Author / Port Packager:** `Stampman3000` (`Twenty` / `Twenty FX`)
- **Upstream repository:** https://github.com/palmereta/audio_tools
- **Official website & manual:** https://audiotools.com.ar/at20v/
- **Pinned upstream commit:** `b30b959` (`main`, tag `lacquer-v1.0.4`, AT20V v1.0.7)
- **Trademark notice:** Korg and MS-20 are registered trademarks of KORG Inc. Neither Audio Tools nor Twenty is affiliated with or endorsed by KORG Inc.

## SDK & Tooling Dependencies

- **Official Akai MPC Plugin Builder SDK** (`inmusic-software/mpc-plugin-builder-sdk`, commit `a5949cf`, MIT Licence):
  - Used for `framework/mpc_plugin.h`, `framework/mpc_vst2_abi.h`, `framework/mpc_resources.h`, `tools/build.py`, `tools/validate.py`, `tools/package.py`, and `tools/host-sim/host_sim.cpp`.
- **Open MPC Community Documentation** (`open-mpc/mpc-vst-plugins`, commit `1af05b9`, MIT Licence):
  - Referenced for verified MPC OS 3.10.1 hardware UI/TUI constraints, Gen1 ARMv7 Cortex-A17 performance budgets, and touch-patching worker patterns.

## Modifications Made to Upstream AT20V DSP (`dsp/`)

All core synthesis equations, calibration curves, nonlinear filter solvers, envelopes, oscillators, ESP YIN pitch tracker, vocoder, delay, and Dattorro plate reverb are preserved verbatim from AT20V (`0.00e+00` bit-exact reference match):

1. `dsp/Common.h`, `Blep.h`, `Fx.h`, `Korg35.h`, `Modules.h`, `Oscillators.h`, `Layout.h`: copied verbatim from upstream `audio_tools/shared/dsp/` and `audio_tools/plugins/at20v/Source/dsp/` (zero JUCE dependencies).
2. `dsp/Oversampling.h`: added `maxFrames` parameter to `Decimator::prepare` / `Interpolator::prepare` (default `1024`, reducing per-instance work-buffer RAM for standalone MPC) and added `reset()`. FIR filter tap coefficients and math are unchanged.
3. `dsp/Engine.h`:
   - Updated layout include path to `#include "Layout.h"`.
   - Preallocated 8× oversampling buffers (`maxBlock * 8 + 8`) and pre-designed both 4× and 8× `Decimator`/`Interpolator` chains inside `Engine::prepare()`, adding `setOversamplingRealtime(int)` so switching 4× ↔ 8× on MPC performs zero heap allocations on the audio thread.
   - Added `playingVoiceCount()` telemetry helper for the Page 1 voice-activity indicator.
4. `dsp/PatchRouter.h`, `bridge/*`, `plugins/*`, `tools/*`: newly authored AGPLv3 MPC host adapter, 35-jack touch-patching router, preset converter, procedural MS-20 UI artwork generator, and MPC `TUI.json`/`Q-Links.json` skin generator.

## Graphics & UI Assets

All PNG panel faceplates, knob filmstrips, jack sockets, cable plugs, LEDs, buttons, and control-wheel sprites shipped in `skins/` are procedurally generated from original Python/Pillow source (`tools/gen_ui_assets.py`) under GNU AGPLv3, inspired by the 1978 Korg MS-20 and Audio Tools AT20V panel layout.
