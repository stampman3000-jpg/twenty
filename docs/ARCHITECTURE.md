# AT20 MPC — Technical Architecture & Source-to-Feature Inventory

## 1. Overview

**AT20 MPC** is a standalone Akai MPC VST2 instrument adaptation of Audio Tools **AT20V** (a complete Korg MS-20 synthesis recreation), accompanied by **AT20 FX**, an identical-DSP insert effect variant that exposes MPC's live stereo audio track input directly to the MS-20 External Signal Processor (ESP), Vocoder, and `EXT SIGNAL IN`.

Both plugins are built from a single portable C++17 codebase using the official Akai MPC Plugin Builder SDK (`mpc_plugin.h`), producing native test builds plus 32-bit ARM (`arm-linux-gnueabihf`, Cortex-A17 NEON, glibc 2.31) and 64-bit ARM (`aarch64-linux-gnu`, Cortex-A55, glibc 2.31) standalone MPC binaries.

## 2. Module Separation

| Layer | Directory / Files | Responsibility |
|---|---|---|
| **Portable AT20V DSP Engine** | `dsp/{Common,Blep,Oversampling,Fx,Korg35,Modules,Oscillators,Layout,Engine}.h` | Zero-JUCE, pure C++17 port of AT20V's exact voice, filters, oscillators, envelopes, MG, S/H, MVCA, ESP, polyphony, unison, analog drift, 4×/8× FIR oversampling, vocoder, delay, and Dattorro plate reverb. |
| **Patchbay Routing Controller** | `dsp/PatchRouter.h` | Complete 35-jack (15 inputs, 20 outputs) routing graph, normalled defaults, 6 repeating AT20V cable colours across 12 numbered bus slots (`1`–`9`, `A`–`C`), multi-out fan-out, single-in rule, interactive tap-to-patch FSM, and binary chunk serialization. |
| **Parameter / Preset / State Bridge** | `bridge/{AT20Params.h, AT20Presets.generated.h}` | 182 frozen parameters (Param 0 = harmless Main Volume; 84 automatable musical & patch params; 98 non-automatable UI/telemetry params), physical unit display formatters, and all 56 factory presets (Init + all 55 AT20V JSON presets). |
| **MPC Host Adapter** | `bridge/AT20Plugin.h`, `plugins/{at20_mpc,at20_fx}/` | `mpc::Plugin` subclass supporting `AT20Plugin<false>` (`AT20 MPC`, UID `AT20`) and `AT20Plugin<true>` (`AT20 FX`, UID `AT2F`). Zero audio-thread allocations/locks, 64-sample sub-block MIDI & smoothing, host transport sync, in-place stereo audio input handling, and 30 ms background UI notifier thread. |
| **Touchscreen Artwork & Skins** | `tools/{gen_ui_assets.py, gen_skins.py, render_preview.py}` -> `skins/` | Procedural 4×-supersampled matte-black brushed MS-20 faceplates (`1280×628`), fluted knob filmstrips, 28-frame chrome jack + coloured plug filmstrip, glowing red LEDs, knurled wheel, `TUI.json`, and `Q-Links.json`. |
| **Validation & Benchmarks** | `tests/{validate_dsp.cpp, compare_upstream.cpp, ref_renderer.cpp, port_renderer.cpp, bench_cpu.cpp}` | Bit-exact upstream reference comparison (`0.00e+00` error), 20-check DSP & patchbay test suite, 56-preset stability sweep, and 18-scenario MPC CPU benchmark. |

## 3. Source-to-Feature Inventory

| AT20V Upstream Feature | Upstream Source | AT20 MPC Port Location | MPC Notes |
|---|---|---|---|
| VCO1 (Tri/Saw/Pulse/Noise, PWM, 32'–4') | `Source/dsp/Oscillators.h` | `dsp/Oscillators.h` | Exact PolyBLEP/PolyBLAMP ramp core |
| VCO2 (Saw/Sq/Narrow/Ring, ±1 oct, 16'–2') | `Source/dsp/Oscillators.h` | `dsp/Oscillators.h` | Exact XOR ring mod (`-vco1Pulse * vco2Sq`) |
| White & Paul Kellet Pink Noise | `Source/dsp/Oscillators.h` | `dsp/Oscillators.h` | Exact coefficients & output levels |
| Korg35 (Rev 1) & LM13600 OTA (Rev 2) HPF/LPF | `Source/dsp/Korg35.h` | `dsp/Korg35.h` | Exact 6-iter Newton TPT Sallen-Key, 6 dB/oct HPF, 12 dB/oct LPF, Rev1 asymmetry & diode drive |
| EG1 (D-A-H-R) & EG2 (H-A-D-S-R) | `Source/dsp/Modules.h` | `dsp/Modules.h` | Exact RC overshoot curves & live Hold timer |
| Modulation Generator (Free + Host Tempo Sync) | `Source/dsp/Modules.h`, `Engine.h` | `dsp/Modules.h`, `Engine.h` | 1:80 ramp/pulse symmetry, 11 BPM-locked divisions via `ctx.transport` |
| Sample & Hold, Mod VCA, S-Trig Hysteresis | `Source/dsp/Modules.h` | `dsp/Modules.h` | Exact 1.5 V / 2.5 V S-trig thresholds |
| 35-Jack Patchbay (Normalled + Feedback) | `Source/dsp/Engine.h`, `PanelView.cpp` | `dsp/Engine.h`, `PatchRouter.h` | 1-sample feedback delay, ±15 V rails, colour-coded numbered plugs + tap-to-patch + direct editor |
| External Signal Processor (Preamp/BPF/YIN/Env/Trig) | `Source/dsp/Modules.h` | `dsp/Modules.h` | Live stereo track audio in `AT20 FX`; selectable Audio In / Synth Self / Noise in `AT20 MPC` |
| Polyphony (Mono..12), Unison (1–4), Drift, Spread | `Source/dsp/Engine.h` | `dsp/Engine.h` | Exact voice stealing, High/Low/Last mono priority, legato/retrigger, per-voice analog drift |
| 4× / 8× Kaiser Half-Band Oversampling | `shared/dsp/Oversampling.h` | `dsp/Oversampling.h`, `Engine.h` | Preallocated 4× & 8× chains for zero-alloc live switching |
| 8–20 Band Vocoder, Ping-Pong Delay, Plate Reverb | `shared/dsp/Fx.h` | `dsp/Fx.h` | Exact 4-pole TPT SVF vocoder, tempo-synced delay, Dattorro plate reverb |
| 55 Factory Presets + Init (Normal Setting) | `assets/presets/*.json` | `bridge/AT20Presets.generated.h` | 56 VST2 built-in programs in `AT20 MPC`; 22 audio-in/FX/self-playing programs (`Filter FX` first) in `AT20 FX` |
| Control Wheel & Momentary Switch | `KeyboardView.h`, `PluginProcessor.cpp` | `bridge/AT20Plugin.h` + Page 2 UI | Driven by Page 2 Wheel/Pushbutton AND MIDI Pitch Bend / CC1 / CC64 |

## 4. MPC Platform Adaptations & Documented Host Differences

1. **External Audio Input Routing (`AT20 MPC` vs `AT20 FX`):**
   Akai MPC's VST2 host feeds silence (or zero input channels) to `instrument` plugins, and routes live stereo track audio (in-place) only to `effect` plugins (which in turn do not receive MIDI). To preserve 100% of AT20V's ESP and Vocoder capabilities:
   - **`AT20 MPC`** (Instrument, 0 in / 2 out, full MIDI) adds an `Ext Audio` source selector (`Audio In`, `Synth Self`, `Noise`) so users can drive the ESP and Vocoder from internal self-feedback or noise right inside an instrument track, while keeping standard MIDI synthesis and full patchbay operation.
   - **`AT20 FX`** (Effect, 2 in / 2 out, in-place stereo) runs the exact same AT20V engine on any MPC audio, drum, or submix track so live external audio feeds the ESP preamp/BPF/YIN F-V/envelope follower/trigger extractor, `EXT SIGNAL IN`, and the 8–20 band Vocoder (defaulting to `Filter FX` at Program 0).
2. **Patchbay Interaction on MPC Touchscreen:**
   MPC's scripted UI (`TUI.json`) cannot draw arbitrary dynamic Bezier patch cables. Instead, Page 2 preserves all 35 jacks at their exact relative MS-20 hardware positions with the complete printed signal-flow schematic, using a 28-frame jack/plug filmstrip with 6 repeating AT20V cable colours and numbered bus badges (`1`–`9`, `A`–`C`) plus gold selection halos and amber compatible-target highlights. Every jack is tappable directly on the faceplate AND mirrored in an integrated Direct Route Editor on the right edge of Page 2.
3. **MIDI Output:**
   MPC's VST2 host discards MIDI output sent by plugins; therefore AT20V's desktop `MIDI Out` selector is omitted from the MPC panel.
4. **MPC Hardware UI Safeguards:**
   - All filmstrips stay well below MPC's 16,384 px vertical texture limit (max 4,940 px).
   - Transparent jack touch hit-plates use `alpha = 4/255` (never `0`, which disables touch on MPC).
   - Button taps are debounced (240 ms) against MPC's double-tap delivery quirk, and host parameter notifications run on a 30 ms worker thread (never synchronously inside `setParameter` or `process`).
   - Avoids `MenuOverlay` and `NonZero` handle modifiers (documented broken for external VST2s on MPC OS 3.10.1).
