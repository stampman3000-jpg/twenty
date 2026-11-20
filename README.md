# Twenty & Twenty FX

Ported to MPC by Stampman3000. All synthesis DSP is Audio Tools' AT20V (github.com/palmereta/audio_tools), unchanged; I only did the MPC port.

A standalone Akai MPC adaptation by **Stampman3000** of **Audio Tools AT20V** (`palmereta/audio_tools`), the open-source Korg MS-20 semi-modular synthesis recreation, built on the official Akai MPC Plugin Builder SDK.

Distributed under **GNU AGPL-3.0-or-later** — see [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).

---

## Highlights

- **Authentic AT20V DSP Engine (`>100 dB` SNR reference parity across all circuits):**
  - Dual PolyBLEP/PolyBLAMP oscillators (`VCO 1` Triangle/Saw/PWM/Noise, `VCO 2` Saw/Square/Narrow Pulse/XOR Ring Mod)
  - Both early **Korg35 (Rev 1)** and later **LM13600 OTA (Rev 2)** 6 dB/oct HPF and 12 dB/oct LPF nonlinear TPT Sallen-Key filters with implicit Newton solver, asymmetric signal-dependent cutoff shift, mixer-driven saturation, and accurate self-oscillation
  - RC-curve **EG1** (Delay/Attack/Release) and **EG2** (Hold/Attack/Decay/Sustain/Release), morphing **MG** with host tempo sync (11 divisions), **Sample & Hold**, **Modulation VCA**, White & Pink noise, Hz/V linear portamento
  - Full **External Signal Processor (ESP)** with preamp, 12 dB/oct bandpass filter, YIN pitch-to-CV (Hz/V) tracker, envelope follower, and Schmitt S-trig extractor
  - **Polyphony** (Mono, 2, 4, 6, 8, 12 voices), **Unison** (1–4) with detune & stereo spread, **Analog Drift**, **2× / 4× / 8×** Kaiser half-band oversampling (default `4×`, zero-allocation live switching)
  - **Vocoder** (8/12/16/20 4-pole TPT bands with formant shift, Q, sibilance, attack/release), tempo-synced ping-pong **Stereo Delay**, and Dattorro **Plate Reverb**
- **Two Standalone MPC Plugins (ARM32 + ARM64, 100% Sub-Tab Q-Link Coverage):**
  - **`Stampman3000 - VST - Twenty`** (Instrument, UID `TWNT`): full MIDI synth with all 56 factory presets (`Init (Normal)` + all 55 AT20V presets) and selectable `Ext Audio` source (`Audio In`, `Synth Self`, `Noise`) for self-modulating ESP/Vocoder patches.
  - **`Stampman3000 - VST - Twenty FX`** (Effect, UID `TWFX`): live stereo insert effect routing track audio directly into the ESP, `EXT SIGNAL IN`, Korg35/OTA filters, and Vocoder, with 22 FX/Vocoder/Audio-In/Self-Playing presets (`Filter FX` at Program 0).
- **Three Faithful Vintage MS-20 Touchscreen Pages (`1280 × 628`):**
  1. **`SYNTH`** — Complete left-panel MS-20 synth faceplate, fluted dark rotary knobs, red `MG`/`EG1` LEDs, subtle VCA status display, and Main Volume.
  2. **`PATCH`** — Full 35-jack MS-20 patchbay preserving original socket positions & signal-flow block diagram, tap-to-patch with 6 AT20V cable colours & numbered route badges (`1`–`9`, `A`–`C`), compatible-target highlighting, integrated Direct Route Editor, Control Wheel, Momentary Switch, and complete bottom ESP section.
  3. **`EXT`** — Voice & Performance, Analogue/System, Stereo Delay, Plate Reverb, and Vocoder modules in matching matte-black MS-20 styling.

---

## Installing on Akai MPC Standalone

Requires **MPC OS 3.10.1 or later** (supports both 32-bit Gen1 MPC One / Live / Live II / X / Key 61 / Key 37 / Force and 64-bit Gen2 MPC Live III / XL).

1. Enable external plugins on your MPC:
   **Preferences → Enhancements (Beta)** → enable **Enable Enhancements** and **External Plugin Support**.
2. Copy one or both deployable plugin folders (or unzip from `dist/`) into a folder named **`VST2 Plugins`** at the root of an SD card, USB drive, or internal drive:
   - `<drive>/VST2 Plugins/Stampman3000 - VST - Twenty/`
   - `<drive>/VST2 Plugins/Stampman3000 - VST - Twenty FX/`
3. Restart your MPC. Load **Twenty** from **External Plugins** on a Plugin track, or **Twenty FX** as an Insert Effect on an Audio/Drum/Submix track.

---

## Building & Testing

Clone with the Audio Tools submodule (pinned at `b30b959`). Comparison tests and preset generation read it from `third_party/audio_tools`.

```bash
git clone --recurse-submodules https://github.com/stampman3000-jpg/twenty.git
```

Set `MPC_SDK` to a checkout of the Akai MPC Plugin Builder SDK, then:

```bash
# Build artwork, skins, native + ARM32 + ARM64 binaries, validate & package ZIPs
chmod +x tools/build_all.sh tools/run_tests.sh
./tools/build_all.sh

# Run DSP validation, upstream bit-exact comparison, CPU benchmark & host_sim
./tools/run_tests.sh
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the complete module map and MPC host notes, and [docs/VALIDATION.md](docs/VALIDATION.md) for reference comparison results, CPU benchmarks, and MPC One polyphony recommendations.

---

## Performance Notes (Original MPC One — ARMv7 Cortex-A17)

- **Default quality (`4×` oversampling):** Mono uses ~7–14% of one core, **Poly 2 uses ~19%**, and **Poly 4 + Delay + Reverb uses ~37–40%** (53% with all 4 voices self-oscillating) — comfortably playable in real time on Gen1 MPC One!
- **Explicit `2×` oversampling (Page 3 `EXT` → `OVERSAMP`):** Cuts DSP load in half again (**Poly 2 ~11%**, **Poly 4 + Delay + Reverb ~20–23%**, **Poly 4 × Unison 2 = 8 voices ~40%**) when you want maximum headroom inside a busy multi-track MPC project.
- **`8×` oversampling** and **Poly 6–12** remain explicitly selectable on Page 3 (`EXT`) and are never silently downgraded.

☕ If this saves you time, you can [buy me a coffee](https://paypal.me/johnnybarter1).
