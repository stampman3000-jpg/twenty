Global rules: also follow ~/agents/AGENTS.md (Johnny's shared rules for all agents).

# AGENTS.md

Twenty and Twenty FX are a public MPC port of Audio Tools AT20V (an MS-20-style synth). Stampman3000 did the MPC port. The synthesis DSP stays Audio Tools' work. Licence is AGPL-3.0-or-later. `README.md` is the page for people. The long module map is `docs/ARCHITECTURE.md`. This file is the map and the rules.

Two plugins, one engine:

- Twenty, UID `TWNT`, instrument. `plugins/at20_mpc/`.
- Twenty FX, UID `TWFX`, effect. `plugins/at20_fx/`.

`docs/ARCHITECTURE.md` still says the ids `AT20` and `AT2F`. The ids the MPC saves are the ones in `plugin.json`. Leave `TWNT` and `TWFX` as they are.

## Layout

- `dsp/` — the portable AT20V engine (`Engine.h`, `Korg35.h`, `Oscillators.h`, `PatchRouter.h`, `Fx.h`, and the rest).
- `bridge/` — parameters, the MPC adapter (`AT20Plugin.h`), and generated presets.
- `plugins/at20_mpc/`, `plugins/at20_fx/` — SDK projects and skins.
- `third_party/audio_tools` — the upstream checkout the comparison test reads. Clone with `--recurse-submodules`.
- `tests/` — DSP validation, the upstream comparison, the CPU bench, and the VST patchbay test.
- `tools/build_all.sh`, `tools/run_tests.sh`, and the three Python art scripts.
- `docs/VALIDATION.md` — the measured CPU notes. `screenshots/`, `tested.json`, `LICENSE`, `NOTICE.md`.

## Build and test

Set `MPC_SDK` to a checkout of `inmusic-software/mpc-plugin-builder-sdk`. The scripts stop if `$MPC_SDK/tools/build.py` is missing.

```bash
./tools/build_all.sh
./tools/run_tests.sh
```

`build_all.sh` draws skins, builds both plugins native plus ARM32 plus ARM64, and writes zips under `dist/`.

`run_tests.sh` always compiles `tests/validate_dsp.cpp` and `tests/bench_cpu.cpp` with `clang++` into `build_tests/`. The upstream comparison runs only when `third_party/audio_tools/plugins/at20v/Source` is present. host_sim and the VST link test run only when `$MPC_SDK/.sdk-tools/host_sim` exists, and they need the native `.dylib` files from a build. A green run with those pieces missing has not checked the packaged plugin.

## Gotchas

- Do not retune `dsp/` unless the owner asked for a sound fix. Re-run `./tools/run_tests.sh`, including the upstream comparison, after any DSP edit.
- The audio thread must not allocate or take a lock. Host parameter notices stay on the background notifier, not inside `process`.
- MPC touch ignores a fully transparent hit target. Jack plates stay at a tiny non-zero alpha. That is in `docs/ARCHITECTURE.md`. Leave it.
- `.gitignore` ignores `*.png` except `screenshots/*.png`. Do not force-add skin PNGs or `dist/`.

## Release

`plugin.json` says version `1.0.0`. Tag `v1.0.0` is already published.

- Ship both plugins, each with arm32 and arm64, from `tools/build_all.sh`.
- Do not commit `dist/`, `build/`, `build_tests/`, `*.zip`, `*.so`, or `*.dylib`.
- Never delete, replace, or re-upload a published release zip. A fix is a new version beside the old one, tagged on the commit that built it.
- Keep the AGPL-3.0-or-later licence and the Audio Tools credit. A catalogue listing also follows the shared rules, including Gen2 in `pluginList-arm-64bit`.
- This repo is public. No home address, no personal email, no private files. Commits are `Stampman3000 <stampman3000@gmail.com>`. Do not rewrite history.
