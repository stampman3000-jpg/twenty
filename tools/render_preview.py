#!/usr/bin/env python3
"""Render live 1280x628 visual previews of all 3 AT20 MPC pages using the generated skin assets."""
import json
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIN_DIR = os.path.join(ROOT, "plugins", "at20_mpc", "skins")
MANIFEST_PATH = os.path.join(ROOT, "tools", "ui_layout_manifest.json")
OUT_DIR = os.path.join(ROOT, "docs", "previews")
os.makedirs(OUT_DIR, exist_ok=True)


def get_frame(strip_name, num_frames, frame_idx):
    im = Image.open(os.path.join(SKIN_DIR, strip_name)).convert("RGBA")
    fh = im.height // num_frames
    idx = max(0, min(num_frames - 1, frame_idx))
    return im.crop((0, idx * fh, im.width, (idx + 1) * fh))


def draw_label_preview(canvas, lb, text_str):
    dr = ImageDraw.Draw(canvas)
    # Approximate MPC Titillium rendering (~0.65 * height)
    sz = max(10, int(round(lb["size"] * 0.72)))
    try:
        font = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", sz, index=1)
    except Exception:
        font = ImageFont.load_default()
    c = lb["color"]
    col = (int(c[2:4], 16), int(c[4:6], 16), int(c[6:8], 16), 255)
    bbox = dr.textbbox((0, 0), text_str, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = lb["x"] + (lb["w"] - tw) // 2
    ty = lb["y"] + (lb["h"] - th) // 2
    dr.text((tx, ty), text_str, font=font, fill=col)


def main():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
        m = json.load(fh)

    # Normal Setting + musical demo knob values (normalized 0..1)
    knob_norm = {
        "volume": 0.7, "vco1_wave": 1/3, "vco1_pw": 0.25, "vco1_scale": 2/3,
        "vco2_wave": 0.0, "vco2_pitch": 0.5, "vco2_scale": 1/3,
        "portamento": 0.15, "master_tune": 0.5, "vco1_level": 0.9, "vco2_level": 0.75,
        "fm_mg": 0.12, "fm_eg1": 0.0,
        "hpf_cutoff": 0.18, "hpf_peak": 0.45, "hpf_mod_mg": 0.0, "hpf_mod_eg2": 0.2,
        "lpf_cutoff": 0.52, "lpf_peak": 0.65, "lpf_mod_mg": 0.1, "lpf_mod_eg2": 0.6,
        "mg_wave": 0.5, "mg_freq": 0.42,
        "eg1_delay": 0.0, "eg1_attack": 0.2, "eg1_release": 0.3,
        "eg2_hold": 0.0, "eg2_attack": 0.05, "eg2_decay": 0.35, "eg2_sustain": 0.6, "eg2_release": 0.28,
        "esp_level": 0.55, "esp_lowcut": 0.2, "esp_highcut": 0.85, "esp_cvadj": 1.0, "esp_thresh": 0.4,
        "pedit_src": 2/19, "pedit_dst": 4/14,
        "voices": 0.4, "unison": 1/3, "detune": 0.24, "spread": 0.6, "priority": 0.5, "retrigger": 0.0,
        "filter_rev": 0.0, "analog": 0.35, "mg_sync": 1.0, "quality": 0.5, "bend_range": 2/12, "output": 0.8, "ext_source": 0.0,
        "dly_on": 1.0, "dly_time": 6/11, "dly_fb": 0.4, "dly_tone": 0.6, "dly_mix": 0.3,
        "rev_on": 1.0, "rev_size": 0.65, "rev_damp": 0.4, "rev_mix": 0.28,
        "voc_on": 0.0, "voc_bands": 2/3, "voc_gain": 0.5, "voc_shift": 0.5, "voc_q": 0.5,
        "voc_hiss": 0.4, "voc_attack": 0.2, "voc_release": 0.3, "voc_mix": 1.0,
    }

    # ── PAGE 1 ──
    p1 = Image.open(os.path.join(SKIN_DIR, "bg_synth.png")).convert("RGBA")
    for k in m["page1"]["knobs"]:
        v = knob_norm.get(k["id"], 0.5)
        fr = get_frame(k["strip"], k["frames"], int(round(v * (k["frames"] - 1))))
        p1.alpha_composite(fr, (int(k["cx"] - k["size"] / 2), int(k["cy"] - k["size"] / 2)))
    for l in m["page1"]["leds"]:
        fr = get_frame(l["strip"], l["frames"], l["frames"] - 1)
        p1.alpha_composite(fr, (int(l["cx"] - l["size"] / 2), int(l["cy"] - l["size"] / 2)))
    draw_label_preview(p1, m["page1"]["labels"][0], "Synthe Bass | K35 | V:1")
    draw_label_preview(p1, m["page1"]["labels"][1], "LPF Cut: 540Hz")
    p1.convert("RGB").save(os.path.join(OUT_DIR, "page1_synth.png"))

    # ── PAGE 2 (with Sample & Hold 3-cable demo: Pink->S/H In [Red 1], MG Sq->S/H Clk [Blue 2], S/H Out->Total [Yellow 3]) ──
    p2 = Image.open(os.path.join(SKIN_DIR, "bg_patch.png")).convert("RGBA")
    demo_jack_frames = {
        "pink_out": 3, "sh_in": 3,          # Red [1]
        "mg_sq_out": 4, "sh_clock_in": 4,   # Blue [2]
        "sh_out": 5, "total_in": 5,         # Yellow [3]
        "wheel_out": 6, "lpf_cut_in": 6,    # Green [4]
    }
    for j in m["page2"]["jacks"]:
        fidx = demo_jack_frames.get(j["id"], 0)
        fr = get_frame("jack_strip.png", 28, fidx)
        p2.alpha_composite(fr, (int(j["cx"] - j["size"] / 2), int(j["cy"] - j["size"] / 2)))
    for k in m["page2"]["knobs"]:
        v = knob_norm.get(k["id"], 0.5)
        fr = get_frame(k["strip"], k["frames"], int(round(v * (k["frames"] - 1))))
        p2.alpha_composite(fr, (int(k["cx"] - k["size"] / 2), int(k["cy"] - k["size"] / 2)))
    for l in m["page2"]["leds"]:
        fr = get_frame(l["strip"], l["frames"], 1 if l["id"] == "led_esp_trig" else 0)
        p2.alpha_composite(fr, (int(l["cx"] - l["size"] / 2), int(l["cy"] - l["size"] / 2)))
    for b in m["page2"]["buttons"]:
        bi = Image.open(os.path.join(SKIN_DIR, b["off"])).convert("RGBA")
        p2.alpha_composite(bi, (b["x"], b["y"]))
    w = m["page2"]["wheel"]
    wfr = get_frame(w["strip"], w["frames"], 16)
    p2.alpha_composite(wfr, (w["x"], w["y"]))
    draw_label_preview(p2, m["page2"]["labels"][0], "4 CABLES ACTIVE")
    draw_label_preview(p2, m["page2"]["labels"][1], "MG TRI")
    draw_label_preview(p2, m["page2"]["labels"][2], "LPF CUT")
    p2.convert("RGB").save(os.path.join(OUT_DIR, "page2_patch.png"))

    # ── PAGE 3 ──
    p3 = Image.open(os.path.join(SKIN_DIR, "bg_ext.png")).convert("RGBA")
    for k in m["page3"]["knobs"]:
        v = knob_norm.get(k["id"], 0.5)
        fr = get_frame(k["strip"], k["frames"], int(round(v * (k["frames"] - 1))))
        p3.alpha_composite(fr, (int(k["cx"] - k["size"] / 2), int(k["cy"] - k["size"] / 2)))
    for l in m["page3"]["leds"]:
        fr = get_frame(l["strip"], l["frames"], 1)
        p3.alpha_composite(fr, (int(l["cx"] - l["size"] / 2), int(l["cy"] - l["size"] / 2)))
    p3.convert("RGB").save(os.path.join(OUT_DIR, "page3_ext.png"))

    print(f"Rendered all 3 previews to {OUT_DIR}/page{{1,2,3}}_*.png")


if __name__ == "__main__":
    main()
