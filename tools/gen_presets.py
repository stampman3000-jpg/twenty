#!/usr/bin/env python3
"""Generate bridge/AT20Presets.generated.h from AT20V's 55 factory JSON presets + Init."""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SRC = os.path.join(
    ROOT, "third_party", "audio_tools", "plugins", "at20v", "assets", "presets"
)
SRC_DIR = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
OUT_PATH = os.path.join(ROOT, "bridge", "AT20Presets.generated.h")

# Exact ParamIdx 0..68 order matching bridge/AT20Params.h
PARAM_KEYS = [
    ("volume", 0.7),
    ("vco1_wave", 1.0), ("vco1_pw", 0.0), ("vco1_scale", 2.0),
    ("vco2_wave", 0.0), ("vco2_pitch", 0.5), ("vco2_scale", 1.0),
    ("portamento", 0.0), ("master_tune", 0.5),
    ("vco1_level", 1.0), ("vco2_level", 1.0),
    ("fm_mg", 0.0), ("fm_eg1", 0.0),
    ("hpf_cutoff", 0.0), ("hpf_peak", 0.0), ("hpf_mod_mg", 0.0), ("hpf_mod_eg2", 0.0),
    ("lpf_cutoff", 1.0), ("lpf_peak", 0.0), ("lpf_mod_mg", 0.0), ("lpf_mod_eg2", 0.0),
    ("mg_wave", 0.5), ("mg_freq", 0.5),
    ("eg1_delay", 0.0), ("eg1_attack", 0.0), ("eg1_release", 0.0),
    ("eg2_hold", 0.0), ("eg2_attack", 0.0), ("eg2_decay", 0.0), ("eg2_sustain", 1.0), ("eg2_release", 0.0),
    ("esp_level", 0.5), ("esp_lowcut", 1.0), ("esp_highcut", 0.0), ("esp_cvadj", 1.0), ("esp_thresh", 0.5),
    # 36..41 Voice & Perf
    ("voices", 0.0), ("unison", 0.0), ("detune", 12.0), ("spread", 0.6), ("priority", 1.0), ("retrigger", 0.0),
    # 42..48 System / Analogue
    ("filter_rev", 0.0), ("analog", 0.35), ("mg_sync", 0.0), ("bend_range", 2.0), ("quality", 1.0), ("output", 0.0), ("ext_source", 0.0),
    # 49..57 Vocoder
    ("voc_on", 0.0), ("voc_bands", 2.0), ("voc_gain", 6.0), ("voc_shift", 0.0),
    ("voc_q", 0.5), ("voc_attack", 0.2), ("voc_release", 0.3), ("voc_hiss", 0.4), ("voc_mix", 1.0),
    # 58..62 Delay
    ("dly_on", 0.0), ("dly_time", 6.0), ("dly_fb", 0.35), ("dly_tone", 0.6), ("dly_mix", 0.25),
    # 63..66 Reverb
    ("rev_on", 0.0), ("rev_size", 0.6), ("rev_damp", 0.4), ("rev_mix", 0.25),
    # 67..68 Performance
    ("wheel", 0.0), ("momentary", 0.0),
]

INPUT_JACKS = [
    "total_in", "freq_in", "ext_sig_in", "hpf_cut_in", "lpf_cut_in", "gain_in",
    "vco2_cv_in", "vco12_cv_in", "sh_clock_in", "vca_ctrl_in", "eg1_trig_in",
    "kbd_trig_in", "sh_in", "vca_in", "esp_in",
]

OUTPUT_JACKS = [
    "signal_out", "phones_out", "mg_tri_out", "mg_sq_out", "eg1_out", "eg2_rev_out",
    "kbd_cv_out", "eg1_rev_out", "kbd_trig_out", "sh_out", "vca_out", "pink_out",
    "white_out", "wheel_out", "msw_out", "esp_amp_out", "esp_bpf_out", "esp_fv_out",
    "esp_env_out", "esp_trig_out",
]

COLOR_MAP = {"red": 0, "blue": 1, "yellow": 2, "green": 3, "white": 4, "black": 5}
IN_INDEX = {k: i for i, k in enumerate(INPUT_JACKS)}
OUT_INDEX = {k: i + 1 for i, k in enumerate(OUTPUT_JACKS)}  # 1..20 (0 = Normalled)
PARAM_INDEX = {k: i for i, (k, _) in enumerate(PARAM_KEYS)}

assert len(PARAM_KEYS) == 69
assert len(INPUT_JACKS) == 15
assert len(OUTPUT_JACKS) == 20


def fx_order(name, category):
    if category == "Effect":
        return 0
    if category == "Vocoder" or name.endswith("(Audio In)"):
        return 1
    if category == "Self-Playing":
        return 2
    return -1


def make_preset_values(knobs, settings, cables):
    # Params 0..98 (69 base + 15 patch src + 15 patch col = 99 values)
    vals = [float(d) for _, d in PARAM_KEYS] + [0.0] * 15 + [0.0] * 15
    for k, v in knobs.items():
        if k in PARAM_INDEX:
            vals[PARAM_INDEX[k]] = float(v)
    for k, v in settings.items():
        if k == "quality":
            # Upstream AT20V quality: 0=4x, 1=8x -> MPC quality: 0=2x, 1=4x, 2=8x
            vals[PARAM_INDEX[k]] = 2.0 if int(round(float(v))) >= 1 else 1.0
        elif k in PARAM_INDEX:
            vals[PARAM_INDEX[k]] = float(v)
    for cb in cables:
        dst = cb.get("dst", "")
        src = cb.get("src", "")
        col = cb.get("color", "red")
        if dst in IN_INDEX and src in OUT_INDEX:
            ii = IN_INDEX[dst]
            vals[69 + ii] = float(OUT_INDEX[src])
            vals[84 + ii] = float(COLOR_MAP.get(col, 0))
    return vals


def c_escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def main():
    files = sorted(glob.glob(os.path.join(SRC_DIR, "*.json")))
    if not files:
        sys.exit(f"No preset JSON files found in {SRC_DIR}")

    presets = []
    # Program 0 for Instrument: Init / Normal Setting (matches MS-20 Owner's Manual p.4)
    presets.append({
        "name": "Init (Normal)",
        "category": "Init",
        "fxOrder": 99,  # included at end for FX
        "values": make_preset_values({}, {}, []),
        "cables": 0,
    })

    max_cables = 0
    for path in files:
        with open(path, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        name = d.get("name", os.path.basename(path))
        cat = d.get("category", "Factory")
        cables = d.get("cables", [])
        max_cables = max(max_cables, len(cables))
        vals = make_preset_values(d.get("knobs", {}), d.get("settings", {}), cables)
        presets.append({
            "name": name,
            "category": cat,
            "fxOrder": fx_order(name, cat),
            "values": vals,
            "cables": len(cables),
        })

    # Write header
    lines = [
        "#pragma once",
        "// Auto-generated by tools/gen_presets.py from Audio Tools AT20V factory presets.",
        "// Preserves all 36 panel knobs, extension settings, patchbay cables and cable colours.",
        "",
        "#include <array>",
        "#include <cstddef>",
        "",
        "namespace at20 {",
        "",
        "constexpr int kPresetParamCount = 99; // Params 0..98 (knobs + ext + perf + 15 patch src + 15 patch col)",
        f"constexpr int kFactoryPresetCount = {len(presets)};",
        "",
        "struct FactoryPreset",
        "{",
        "    const char* name;",
        "    const char* category;",
        "    int fxOrder; // >= 0 included in AT20 FX (0=Effect, 1=Vocoder/AudioIn, 2=Self-Playing, 99=Init)",
        "    std::array<float, kPresetParamCount> values;",
        "};",
        "",
        "inline const FactoryPreset kFactoryPresets[kFactoryPresetCount] = {",
    ]

    def fmt_f(v):
        s = f"{v:.6g}"
        if "." not in s and "e" not in s and "E" not in s:
            s += ".0"
        return s + "f"

    for p in presets:
        short_name = p["name"][:23]  # VST2 kVstMaxProgNameLen = 24 (23 chars + NUL)
        vstr = ", ".join(fmt_f(v) for v in p["values"])
        lines.append(f'    {{ "{c_escape(short_name)}", "{c_escape(p["category"])}", {p["fxOrder"]}, {{ {{ {vstr} }} }} }},')

    lines += [
        "};",
        "",
        "} // namespace at20",
        "",
    ]

    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    fx_count = sum(1 for p in presets if p["fxOrder"] >= 0)
    print(f"Generated {OUT_PATH}: {len(presets)} total presets ({fx_count} FX-compatible), max cables={max_cables}")


if __name__ == "__main__":
    main()
