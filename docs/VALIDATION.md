# AT20 MPC & AT20 FX — Validation & CPU Benchmark Report

Date: 2026-11-20  
Upstream Reference: Audio Tools AT20V (`palmereta/audio_tools` commit `b30b959`, AT20V v1.0.7)  
SDK: Official Akai MPC Plugin Builder SDK (`inmusic-software/mpc-plugin-builder-sdk` commit `a5949cf`)  
Toolchain: Zig 0.17.1 (`arm-linux-gnueabihf.2.31` / `cortex_a17`, `aarch64-linux-gnu.2.31` / `cortex_a55`, native macOS arm64)

---

## 1. Upstream AT20V Reference vs Ported AT20 MPC Comparison

Compiled the unmodified upstream `audio_tools/plugins/at20v/Source/dsp/Engine.h` against `dsp/Engine.h` (ODR-isolated via `-Ddh=dh_ref` / `-Ddh=dh_port`, deterministic `analog = 0` so RNG phase is identical) across 0.5 s stereo renders at 44,100 Hz (`tests/compare_upstream.cpp`):

| Scenario | Max Sample Error | RMS Error | SNR | Status |
|---|---:|---:|---:|---|
| 0: Korg35 Rev 1 LPF Sweep & Envelope | `9.45e-06` | `8.24e-07` | **109.3 dB** | **PASS** |
| 1: OTA Rev 2 High-Reso Self-Oscillation | `1.37e-06` | `2.49e-07` | **130.3 dB** | **PASS** |
| 2: VCO2 Ring Modulation + VCO1 PWM | `1.91e-05` | `1.73e-06` | **110.0 dB** | **PASS** |
| 3: Patchbay Sample & Hold + Feedback Loop | `1.96e-05` | `3.64e-06` | **105.2 dB** | **PASS** |
| 4: ESP Preamp / BPF / YIN F-V / Trig Tracking | `1.46e-05` | `5.99e-07` | **118.5 dB** | **PASS** |
| 5: Poly 4 + Unison 2 + 16-Band Vocoder + Delay + Reverb | `4.30e-06` | `5.04e-07` | **106.7 dB** | **PASS** |
| 6: 8× Oversampling High-Reso Korg35 | `1.83e-05` | `5.08e-06` | **100.9 dB** | **PASS** |

**Result:** **7 / 7 high-precision match (`100.9–130.3 dB` SNR — cleaner than 16-bit audio across all filters, self-oscillation, ring mod, feedback loops, ESP, and FX).**

---

## 2. DSP, Patchbay & 56-Preset Validation (`tests/validate_dsp.cpp`)

**Result: 20 / 20 PASSED (0 FAILED)**
- VCO1 Triangle, Sawtooth, Pulse (PWM), and White Noise verified; A4 tuning measured **440.00 Hz** (target 440.0 Hz).
- VCO2 XOR Ring Modulation + VCO1 PW interaction verified (`rms=0.544`, `pwDiff=0.406`).
- Rev 1 Korg35 LPF self-oscillation at 500 Hz cutoff: `rms=0.404`, `freq=498.0 Hz`; Rev 2 OTA LPF self-oscillation: `rms=0.065`, `freq=500.0 Hz`.
- Rev 1 Korg35 nonlinear saturation under hot mixer drive verified significantly stronger than Rev 2 OTA (`nlDev=0.3751` vs `0.0225`).
- 2× / 4× / 8× oversampling RMS parity verified (`0.531` / `0.531` / `0.531`) plus zero-allocation live 2× ↔ 4× ↔ 8× switching.
- EG2 Attack / Sustain / Release curve verified (`early=0.110`, `late=0.418`, `release_end=0.00000`).
- `PatchRouter` interactive tap-to-patch FSM verified: tap output highlights compatible inputs, tap input connects with matching colour/route badge, multi-out fan-out shares bus badge, double-tap connected input disconnects, and `phones_out -> ext_sig_in` feedback loop under peak=0.95 stays finite and cleanly rail-limited (`peak=1.000`).
- ESP YIN pitch-to-CV & S-trig tracking verified on 220 Hz audio input (`tracked=220.0 Hz`, `trigLed=1`).
- Polyphony + Unison + Stereo Spread + Ping-Pong Delay + Plate Reverb + 16-band Vocoder verified.
- **All 56 / 56 factory presets** (`Init (Normal)` + all 55 AT20V JSON presets) load and render cleanly with zero NaN/Inf.

---

## 3. End-to-End VST2 Plugin & Official `host_sim` Validation

### `tests/test_vst_patchbay.cpp`: **15 / 15 PASSED (0 FAILED)**
- Verified tapping `MG SQ OUT` -> `INIT GAIN IN` via VST2 parameters updates both jack visual filmstrips to the same cable badge **and** immediately opens the VCA in `processReplacing` (`silentRms=0.00000` -> `patchedRms=0.2620`).
- Verified `Clear All` disconnects cables, `effGetChunk` / `effSetChunk` restores exact cables & colours, `Sample & Hold` preset synchronizes jack badges, and `AT20 FX` (`Filter FX` at Program 0) processes live stereo audio through ESP + Korg35 filters (`rms=0.6037`).

### Official Akai SDK `host_sim test`
- **`AT20 MPC`:** **`19 passed, 0 warnings, 0 failures`** (peak `-2.67 dBFS`, RMS `-9.38 dBFS`, latency 27 samples, block sizes 32/128/512, 200-param random sweep finite, 3313-byte chunk round-trip **byte-identical**, all-notes-off quiet `-134.6 dBFS`, zero denormals).
- **`AT20 FX`:** **`20 passed, 0 warnings, 0 failures`** (peak `-4.15 dBFS`, RMS `-7.52 dBFS`, latency 55 samples, **in-place processing matches out-of-place**, chunk round-trip **byte-identical**, passes silence `-105.7 dBFS`, zero denormals).

### Official Akai SDK `tools/validate.py`
- **`Audio Tools - VST - AT20 MPC`:** **`0 errors, 0 warnings`**
  - `VST/at20-mpc-arm32.so` (326 KB): 32-bit ARM ELF, max `GLIBC_2.27`, exports only `VSTPluginMain`.
  - `VST/at20-mpc-arm64.so` (389 KB): 64-bit AArch64 ELF, max `GLIBC_2.27`, exports only `VSTPluginMain`.
  - `Plugin Skins/TUI.json` (3 tabs, handles in `0..181`, all 27 PNG assets verified) & `Q-Links.json` (3 tab maps).
  - `version.xml`: `uiversion 0.1.0.0`.
- **`Audio Tools - VST - AT20 FX`:** **`0 errors, 0 warnings`**
  - `VST/at20-fx-arm32.so` (331 KB) & `VST/at20-fx-arm64.so` (395 KB): max `GLIBC_2.27`, exports only `VSTPluginMain`.

---

## 4. Actual On-Device MPC One (ARMv7 Cortex-A17) & Desktop CPU Benchmarks (`tests/bench_cpu.cpp`)

Measured directly on the target **Akai MPC One (Gen1, ARMv7 Cortex-A17, Linux 6.18.44-rt6 PREEMPT_RT)** at **44.1 kHz, 128-frame block (2902.5 µs budget)** — plus desktop Apple Silicon reference — after applying Cortex-A17 hot-loop optimizations (**>100 dB SNR** vs upstream AT20V: `prewarpFast` 5th-order polynomial + `fc -> G` caching, exact 0-iteration closed-form `K == 0` filter path, first-order Newton convergence update, skipping unpatched Pink/S&H/MVCA/Ring-pulse work, base-rate 0.3 Hz analog drift, division-free `Mg::processFast` & `RampCore::setFreqFast`, and explicit `2x | 4x | 8x` oversampling):

| Scenario | MPC One Avg (µs) | MPC One p99 (µs) | MPC One Core % | Desktop Avg (µs) |
|---|---:|---:|---:|---:|
| **Mono Init (2×, Korg35)** | **165.4** | 321.7 | **5.7%** | 16.9 |
| **Mono High-Reso Self-Osc (2×)** | **228.6** | 632.3 | **7.9%** | 18.5 |
| **Poly 2 Voices (2×)** | **310.0** | 695.6 | **10.7%** | 25.6 |
| **Poly 4 Voices (2×)** | **591.0** | 1299.0 | **20.4%** | 42.2 |
| **Poly 4 Voices + Delay + Rev (2×)** | **664.8** | 1245.3 | **22.9%** | 39.9 |
| **Poly 4 High-Reso Self-Osc (2×)** | **848.7** | 1530.9 | **29.2%** | 42.7 |
| **Poly 4 × Unison 2 = 8v (2×)** | **1149.2** | 1873.3 | **39.6%** | 63.7 |
| Mono Init (4×, Korg35) | **305.6** | 597.3 | **10.5%** | 19.1 |
| Mono Init (4×, OTA Rev 2) | **197.9** | 564.9 | **6.8%** | 12.4 |
| Mono High-Reso Self-Osc (4×) | **413.3** | 814.3 | **14.2%** | 20.8 |
| Mono Init (8× oversampling) | **588.7** | 998.6 | **20.3%** | 36.9 |
| Mono Feedback Patch (4×) | **428.5** | 878.2 | **14.8%** | 22.4 |
| Mono + ESP YIN Pitch Track (4×) | **525.7** | 1096.9 | **18.1%** | 35.3 |
| Mono + Delay + Plate Reverb (4×) | **379.8** | 788.9 | **13.1%** | 21.2 |
| Mono + 16-Band Vocoder (4×) | **536.5** | 1128.7 | **18.5%** | 28.2 |
| Mono + 20-Band Vocoder + FX (4×) | **635.5** | 1307.8 | **21.9%** | 32.8 |
| Poly 2 Voices (4×) | **563.5** | 1203.6 | **19.4%** | 33.0 |
| Poly 4 Voices (4×) | **1072.9** | 1741.7 | **37.0%** | 65.1 |
| Poly 4 Voices + Delay + Rev (4×) | **1150.2** | 1820.5 | **39.6%** | 67.5 |
| Poly 4 High-Reso Self-Osc (4×) | **1548.9** | 2511.1 | **53.4%** | 75.8 |
| Poly 6 Voices (4×) | **1588.4** | 2365.6 | **54.7%** | 94.5 |
| Poly 8 Voices (4×) | **2104.1** | 3250.4 | 72.5% | 126.6 |
| Poly 12 Voices (4×) | **3128.5** | 4208.8 | 107.8% | 184.8 |
| Mono Unison 2 (4×) | **565.7** | 1087.3 | **19.5%** | 34.4 |
| Mono Unison 4 (4×) | **1072.5** | 1730.7 | **37.0%** | 65.2 |
| Poly 4 × Unison 2 = 8v + FX (4×) | **2187.9** | 3098.2 | 75.4% | 128.5 |

### First-Generation MPC One (ARMv7 Cortex-A17) Practical Polyphony Limits
- **At default `4×` oversampling** (2.1–2.2× faster than v1.0.0 baseline!):
  - **Mono (Korg35/OTA, Feedback, Delay+Reverb, ESP, 16–20 Band Vocoder):** **6.8%–21.9%** of one core.
  - **Mono (`8×` oversampling):** **20.3%** of one core.
  - **Poly 2 / Unison 2:** **19.4%–19.5%** of one core — effortless even inside busy MPC beats!
  - **Poly 4 / Unison 4 (+ Delay + Reverb):** **37.0%–39.6%** of one core (53.4% even with all 4 voices self-oscillating!).
- **At explicit `2×` oversampling** (Page 3 `EXT` → `OVERSAMP`):
  - **Poly 2:** **10.7%** of one core; **Poly 4 (+ Delay + Reverb):** **20.4%–22.9%** of one core; **Poly 4 × Unison 2 (8 voices):** **39.6%** of one core!
- **On-device binary & VST2 integration test (`at20_test_arm32`):** Ran on an MPC One against the installed Twenty and Twenty FX binaries — **15 / 15 PASSED (0 FAILED)**!
