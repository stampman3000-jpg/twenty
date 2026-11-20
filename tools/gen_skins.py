#!/usr/bin/env python3
"""Generate valid Akai MPC TUI.json and Q-Links.json for AT20 MPC and AT20 FX.

Reads tools/ui_layout_manifest.json and writes:
  - plugins/at20_mpc/skins/{TUI.json, Q-Links.json}
  - plugins/at20_fx/skins/{TUI.json, Q-Links.json}

Handles the MPC JSON parser's duplicate "version" key requirement for KnobOverlay,
avoids MenuOverlay and NonZero (known broken on MPC OS 3.10.1), and sets exact
replacementStrings for all discrete choice parameters.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_PATH = os.path.join(ROOT, "tools", "ui_layout_manifest.json")
SKIN_DIRS = [
    os.path.join(ROOT, "plugins", "at20_mpc", "skins"),
    os.path.join(ROOT, "plugins", "at20_fx", "skins"),
]


class DupObj:
    """List-of-pairs JSON object that preserves duplicate keys (for MPC Overlay widgets)."""
    def __init__(self, pairs):
        self.pairs = pairs


def dump_mpc_json(obj, indent=0):
    sp = "  " * indent
    sp2 = "  " * (indent + 1)
    if isinstance(obj, DupObj):
        if not obj.pairs:
            return "{}"
        items = [f'{sp2}{json.dumps(k)}: {dump_mpc_json(v, indent + 1)}' for k, v in obj.pairs]
        return "{\n" + ",\n".join(items) + f"\n{sp}}}"
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        items = [f'{sp2}{json.dumps(k)}: {dump_mpc_json(v, indent + 1)}' for k, v in obj.items()]
        return "{\n" + ",\n".join(items) + f"\n{sp}}}"
    if isinstance(obj, list):
        if not obj:
            return "[]"
        if all(not isinstance(x, (dict, list, DupObj)) for x in obj):
            return "[" + ", ".join(json.dumps(x) for x in obj) + "]"
        items = [f"{sp2}{dump_mpc_json(x, indent + 1)}" for x in obj]
        return "[\n" + ",\n".join(items) + f"\n{sp}]"
    return json.dumps(obj)


def empty_bg():
    return {
        "version": 1,
        "focussed":   {"version": 1, "colour": "0", "image": ""},
        "unfocussed": {"version": 1, "colour": "0", "image": ""},
    }


def make_bounds(x, y, w, h, focus="No", invalid="Show", when="Always"):
    return {
        "version": 1,
        "acceptsHWFocus": focus,
        "showWhenDataModelInvalid": invalid,
        "whenVisible": when,
        "boundsType": "Absolute",
        "bounds": f"{int(round(x))} {int(round(y))} {int(round(w))} {int(round(h))}",
    }


def make_entry(name, comp_type, data, bounds, remap=None):
    return {
        "version": 2,
        "componentData": {
            "version": 1,
            "name": name,
            "type": comp_type,
            "data": data,
        },
        "handle remapping": {
            "version": 1,
            "map": remap if remap is not None else [],
        },
        "bounds": bounds,
    }


def make_knob_overlay_def(bipolar=False):
    # Exact duplicate "version" keys required by MPC firmware parser (ui-reference.md §1.8 & §6.10)
    overlay_data = DupObj([
        ("version", 2),
        ("version", 1),
        ("actions", [
            {"version": 1, "onAction": "Focus Lost", "handler": "Focus Lost", "handleName": "Focus Lost", "additionalData": ""}
        ]),
        ("overlayType", "Knob With Header"),
        ("scaleType", "Linear"),
        ("polarityType", "Bipolar" if bipolar else "Unipolar"),
        ("showMinusSign", True),
        ("handleName", "Data"),
    ])
    return {
        "version": 2,
        "actions": [],
        "backgroundData": empty_bg(),
        "ignoreMousePresses": True,
        "disableCoarseDataWheel": False,
        "componentsData": [
            make_entry("overlay", "KnobOverlay", overlay_data,
                       make_bounds(0, 0, 1280, 800, focus="Yes", invalid="Show"))
        ],
    }


def make_knob_component_def(strip, frames, size, bipolar=False):
    overlay_name = "knob overlay bipolar" if bipolar else "knob overlay"
    return {
        "version": 2,
        "actions": [
            {"version": 1, "onAction": "Mouse Down",    "handler": "Q-Link",       "handleName": "Data", "additionalData": ""},
            {"version": 1, "onAction": "Double Click",  "handler": "Show Overlay", "handleName": "Data", "additionalData": overlay_name},
            {"version": 1, "onAction": "Enter Pressed", "handler": "Show Overlay", "handleName": "Data", "additionalData": overlay_name},
        ],
        "backgroundData": empty_bg(),
        "ignoreMousePresses": False,
        "disableCoarseDataWheel": False,
        "componentsData": [
            make_entry(
                "focus", "Focus",
                {"version": 1, "backgroundColour": "14e0ac4a", "outlineColour": "ffe0ac4a",
                 "backgroundInset": 1.0, "outlineThickness": 1.5},
                make_bounds(0, 0, size, size, focus="No", invalid="Show", when="WhenFocussed"),
            ),
            make_entry(
                "knob", "Knob",
                {"version": 3, "knobType": "FilmStrip", "filmStrip": strip,
                 "numFrames": frames, "invert": False, "dragOrientation": "Vertical",
                 "handleName": "Data"},
                make_bounds(0, 0, size, size, focus="No", invalid="Show"),
            ),
        ],
    }


def make_wheel_component_def(strip, frames, w, h):
    return {
        "version": 2,
        "actions": [
            {"version": 1, "onAction": "Mouse Down",    "handler": "Q-Link",       "handleName": "Data", "additionalData": ""},
            {"version": 1, "onAction": "Double Click",  "handler": "Show Overlay", "handleName": "Data", "additionalData": "knob overlay bipolar"},
            {"version": 1, "onAction": "Enter Pressed", "handler": "Show Overlay", "handleName": "Data", "additionalData": "knob overlay bipolar"},
        ],
        "backgroundData": empty_bg(),
        "ignoreMousePresses": False,
        "disableCoarseDataWheel": False,
        "componentsData": [
            make_entry(
                "focus", "Focus",
                {"version": 1, "backgroundColour": "14e0ac4a", "outlineColour": "ffe0ac4a",
                 "backgroundInset": 1.0, "outlineThickness": 1.5},
                make_bounds(0, 0, w, h, focus="No", invalid="Show", when="WhenFocussed"),
            ),
            make_entry(
                "wheel", "Knob",
                {"version": 3, "knobType": "FilmStrip", "filmStrip": strip,
                 "numFrames": frames, "invert": False, "dragOrientation": "Vertical",
                 "handleName": "Data"},
                make_bounds(0, 0, w, h, focus="No", invalid="Show"),
            ),
        ],
    }


def make_replacement_strings():
    """Discrete choice labels matching AT20Params.h (so Q-Links & data wheel step cleanly)."""
    out_names = [
        "SIG OUT", "PHONES", "MG TRI", "MG SQ", "EG1 OUT", "EG2 REV",
        "KBD CV", "EG1 REV", "TRG OUT", "S/H OUT", "MVCA OUT", "PINK",
        "WHITE", "WHEEL", "MOM SW", "ESP AMP", "ESP BPF", "ESP F-V",
        "ESP ENV", "ESP TRG",
    ]
    in_names = [
        "TOTAL", "FREQ", "EXT SIG", "HPF CUT", "LPF CUT", "INIT GN",
        "VCO2 CV", "VCO12 CV", "S/H CLK", "MVCA CTL", "EG1 TRG",
        "KBD TRG", "S/H IN", "MVCA IN", "ESP IN",
    ]
    rows = [
        (1,  ["Tri", "Saw", "Pulse", "Noise"]),
        (3,  ["32'", "16'", "8'", "4'"]),
        (4,  ["Saw", "Square", "Narrow", "Ring"]),
        (6,  ["16'", "8'", "4'", "2'"]),
        (36, ["Mono", "2", "4", "6", "8", "12"]),
        (37, ["1", "2", "3", "4"]),
        (40, ["Last", "High", "Low"]),
        (41, ["Off", "On"]),
        (42, ["Korg35", "OTA"]),
        (44, ["Free", "Sync"]),
        (45, [str(i) for i in range(13)]),
        (46, ["2x", "4x", "8x"]),
        (48, ["Audio In", "Synth Self", "Noise"]),
        (49, ["Off", "On"]),
        (50, ["8", "12", "16", "20"]),
        (58, ["Off", "On"]),
        (59, ["1/32", "1/16T", "1/16", "1/16D", "1/8T", "1/8", "1/8D", "1/4T", "1/4", "1/4D", "1/2", "1 bar"]),
        (63, ["Off", "On"]),
        (68, ["Off", "On"]),
        (169, out_names),
        (170, in_names),
    ]
    for i in range(15):
        rows.append((69 + i, ["Normal"] + out_names))
    return [{"key": f"Parameter {p}", "value": vals} for p, vals in rows]


def build_tui(manifest):
    local_defs = [
        {"key": "knob overlay",         "value": make_knob_overlay_def(bipolar=False)},
        {"key": "knob overlay bipolar", "value": make_knob_overlay_def(bipolar=True)},
    ]

    # Collect unique knob component definitions across all 3 pages
    seen_knob_types = {}
    def get_knob_type_name(k):
        key = (k["strip"], k["frames"], k["size"], bool(k.get("bipolar", False)))
        if key not in seen_knob_types:
            tname = f"k_{os.path.splitext(k['strip'])[0]}_{k['size']}_{'bi' if key[3] else 'uni'}"
            seen_knob_types[key] = tname
            local_defs.append({
                "key": tname,
                "value": make_knob_component_def(k["strip"], k["frames"], k["size"], bipolar=key[3]),
            })
        return seen_knob_types[key]

    w_spec = manifest["page2"]["wheel"]
    local_defs.append({
        "key": "ms20_wheel",
        "value": make_wheel_component_def(w_spec["strip"], w_spec["frames"], w_spec["w"], w_spec["h"]),
    })

    def add_bg(comps, bg_file):
        comps.append(make_entry(
            "bg", "Image",
            {"version": 2, "imageType": "Regular", "colour": "0", "image": bg_file},
            make_bounds(0, 0, 1280, 628, focus="No", invalid="Show"),
        ))

    def add_knobs(comps, knobs):
        for k in knobs:
            tname = get_knob_type_name(k)
            sz = k["size"]
            comps.append(make_entry(
                k["id"], tname,
                {"version": 1, "handleName": "Data"},
                make_bounds(k["cx"] - sz / 2, k["cy"] - sz / 2, sz, sz, focus="Yes", invalid="Hide"),
                remap=[{"key": "Data", "value": f"Parameter {k['param']}"}],
            ))

    def add_leds(comps, leds):
        for l in leds:
            sz = l["size"]
            comps.append(make_entry(
                l["id"], "Image",
                {"version": 2, "imageType": "FilmStrip", "colour": "0",
                 "image": l["strip"], "numFrames": l["frames"],
                 "handleName": f"Parameter {l['param']}"},
                make_bounds(l["cx"] - sz / 2, l["cy"] - sz / 2, sz, sz, focus="No", invalid="Show"),
            ))

    def add_labels(comps, labels):
        for lb in labels:
            comps.append(make_entry(
                lb["id"], "Label",
                {
                    "version": 1,
                    "textStyle": {
                        "version": 1,
                        "font": {"version": 1, "name": "Titillium Web", "style": "SemiBold", "height": float(lb["size"])},
                        "colour": lb["color"],
                        "justification": "horizontallyCentred verticallyCentred",
                        "case": "Original",
                    },
                    "type": "Value",
                    "handleName": f"Parameter {lb['param']}",
                },
                make_bounds(lb["x"], lb["y"], lb["w"], lb["h"], focus="No", invalid="Show"),
            ))

    def make_tab(tab_name, fn_key, fn_sub, comps):
        return {
            "version": 1,
            "tabName": tab_name,
            "fnKeyIndex": fn_key,
            "fnKeySubIndex": fn_sub,
            "componentDefinition": {
                "version": 2,
                "actions": [],
                "backgroundData": {"version": 1, "focussed": {"version": 1, "colour": "ff161719", "image": ""}, "unfocussed": {"version": 1, "colour": "ff161719", "image": ""}},
                "ignoreMousePresses": False,
                "disableCoarseDataWheel": False,
                "componentsData": comps,
            },
            "qlinkBoundsData": [],
        }

    # ── TAB 1 (SubTabs 0 & 1): SYNTH PANEL ──
    def build_c1():
        c = []
        add_bg(c, "bg_synth.png")
        add_leds(c, manifest["page1"]["leds"])
        add_labels(c, manifest["page1"]["labels"])
        add_knobs(c, manifest["page1"]["knobs"])
        return c

    # ── TAB 2 (SubTabs 0 & 1): PATCHBAY / ESP ──
    def build_c2():
        c = []
        add_bg(c, "bg_patch.png")
        add_leds(c, manifest["page2"]["leds"])
        add_labels(c, manifest["page2"]["labels"])
        add_knobs(c, manifest["page2"]["knobs"])

        # 35 patchbay jacks: FilmStrip Image underneath + alpha=4 Button hit-plate on top
        for j in manifest["page2"]["jacks"]:
            sz = j["size"]
            bx, by = j["cx"] - sz / 2, j["cy"] - sz / 2
            c.append(make_entry(
                f"jvis_{j['id']}", "Image",
                {"version": 2, "imageType": "FilmStrip", "colour": "0",
                 "image": "jack_strip.png", "numFrames": 28,
                 "handleName": f"Parameter {j['visParam']}"},
                make_bounds(bx, by, sz, sz, focus="No", invalid="Show"),
            ))
            c.append(make_entry(
                f"jtap_{j['id']}", "Button",
                {"version": 2, "onImage": "hit_46.png", "offImage": "hit_46.png",
                 "buttonId": 1, "numButtonsInGroup": 1,
                 "handleName": f"Parameter {j['tapParam']}", "gestureBehaviour": "Instant"},
                make_bounds(bx, by, sz, sz, focus="No", invalid="Show"),
            ))

        # Action buttons + Momentary Switch
        for b in manifest["page2"]["buttons"]:
            c.append(make_entry(
                b["id"], "Button",
                {"version": 2, "onImage": b["on"], "offImage": b["off"],
                 "buttonId": 1, "numButtonsInGroup": 1,
                 "handleName": f"Parameter {b['param']}", "gestureBehaviour": "Instant"},
                make_bounds(b["x"], b["y"], b["w"], b["h"], focus="No", invalid="Show"),
            ))

        # Control Wheel
        c.append(make_entry(
            w_spec["id"], "ms20_wheel",
            {"version": 1, "handleName": "Data"},
            make_bounds(w_spec["x"], w_spec["y"], w_spec["w"], w_spec["h"], focus="Yes", invalid="Hide"),
            remap=[{"key": "Data", "value": f"Parameter {w_spec['param']}"}],
        ))
        return c

    # ── TAB 3 (SubTabs 0 & 1): EXTENSIONS / ANALOGUE / FX / VOCODER ──
    def build_c3():
        c = []
        add_bg(c, "bg_ext.png")
        add_leds(c, manifest["page3"]["leds"])
        add_knobs(c, manifest["page3"]["knobs"])
        return c

    tabs = [
        make_tab("SYNTH 1", 0, 0, build_c1()),
        make_tab("SYNTH 2", 0, 1, build_c1()),
        make_tab("PATCH 1", 1, 0, build_c2()),
        make_tab("PATCH 2", 1, 1, build_c2()),
        make_tab("EXT 1",   2, 0, build_c3()),
        make_tab("EXT 2",   2, 1, build_c3()),
    ]

    return {
        "pageData": {
            "version": 1,
            "componentDefinitions": {
                "version": 2,
                "importFiles": [],
                "localComponentDefinitions": local_defs,
            },
            "replacementStrings": make_replacement_strings(),
            "info": {"version": 1, "type": "CompleteDescription"},
            "tabs": tabs,
        }
    }


def make_qlink_dict(cols_top_to_bottom):
    """Map 4 columns of 4 params (top->bottom per col) to physical Q-Link 1..16 (ui-reference.md §8.2)."""
    # Column 0 (top->bot): 13, 9, 5, 1
    # Column 1 (top->bot): 14, 10, 6, 2
    # Column 2 (top->bot): 15, 11, 7, 3
    # Column 3 (top->bot): 16, 12, 8, 4
    slots = [
        [13, 9, 5, 1],
        [14, 10, 6, 2],
        [15, 11, 7, 3],
        [16, 12, 8, 4],
    ]
    out = {}
    for c in range(4):
        for r in range(4):
            out[f"Q-Link {slots[c][r]}"] = cols_top_to_bottom[c][r]
    return {f"Q-Link {i}": out[f"Q-Link {i}"] for i in range(1, 17)}


def build_qlinks():
    # Tab 1 SubTab 1 (SYNTH 1): Filters, VCO waves/levels, LPF Mod/MG, full EG2 ADSR
    t1_s1 = make_qlink_dict([
        [17, 18, 13, 14],  # LPF Cut, LPF Peak, HPF Cut, HPF Peak
        [1,  4,  9,  10],  # VCO1 Wave, VCO2 Wave, VCO1 Lvl, VCO2 Lvl
        [20, 19, 22, 21],  # LPF EG2, LPF MG, MG Freq, MG Wave
        [27, 28, 29, 30],  # EG2 Atk, EG2 Dec, EG2 Sus, EG2 Rel
    ])

    # Tab 1 SubTab 2 (SYNTH 2): Remaining 15 SYNTH knobs + Main Volume (31/31 SYNTH coverage!)
    t1_s2 = make_qlink_dict([
        [2,  3,  5,  6],   # VCO1 PW, VCO1 Scale, VCO2 Pitch, VCO2 Scale
        [7,  8,  11, 12],  # Portamento, Master Tune, FM MG/TExt, FM EG1/Ext
        [15, 16, 26, 0],   # HPF MG Mod, HPF EG2 Mod, EG2 Hold, Main Volume
        [23, 24, 25, 0],   # EG1 Delay, EG1 Attack, EG1 Release, Main Volume
    ])

    # Tab 2 SubTab 1 (PATCH 1): ESP, Wheel/MomSw, Patch Editor, Quick Filters + Clear
    t2_s1 = make_qlink_dict([
        [31, 32, 33, 35],      # ESP Level, Low Cut, High Cut, Thresh
        [34, 67, 68, 0],       # ESP CV Adj, Ctrl Wheel, Mom Switch, Volume
        [169, 170, 171, 172],  # Patch Out, Patch In, Connect, Disconnect
        [17, 18, 13, 173],     # LPF Cut, LPF Peak, HPF Cut, Clear All
    ])

    # Tab 2 SubTab 2 (PATCH 2): Direct Q-Link cable source selector for ALL 15 MS-20 patchbay input jacks + Clear All
    t2_s2 = make_qlink_dict([
        [69, 70, 72, 73],  # In TOTAL, In FREQ, In HPF CUT, In LPF CUT
        [75, 76, 71, 74],  # In VCO2 CV, In VCO12 CV, In EXT SIG, In INIT GN
        [77, 81, 78, 82],  # In S/H CLK, In S/H IN, In MVCA CTL, In MVCA IN
        [79, 80, 83, 173], # In EG1 TRG, In KBD TRG, In ESP IN, Clear All
    ])

    # Tab 3 SubTab 1 (EXT 1): Voice/Unison, Analog/Oversample, full Delay, full Reverb
    t3_s1 = make_qlink_dict([
        [36, 37, 38, 39],  # Voices, Unison, Uni Detune, Spread
        [42, 43, 44, 46],  # Filter Rev, Analog Drift, MG Clock, Oversample
        [58, 59, 60, 62],  # Delay On, Delay Time, Delay Fbk, Delay Mix
        [63, 64, 65, 66],  # Reverb On, Rev Size, Rev Damp, Rev Mix
    ])

    # Tab 3 SubTab 2 (EXT 2): Priority/Retrig/Bend/Out, Ext Audio/Delay Tone, ALL 10 Vocoder params + Volume (31/31 EXT coverage!)
    t3_s2 = make_qlink_dict([
        [40, 41, 45, 47],  # Priority, Retrigger, Bend Range, Output dB
        [48, 61, 49, 50],  # Ext Audio, Delay Tone, Vocoder On, Voc Bands
        [51, 52, 53, 56],  # Voc Input, Voc Formant, Voc Reso, Voc Sibil
        [54, 55, 57, 0],   # Voc Attack, Voc Release, Voc Mix, Main Volume
    ])

    # Program Mode Q-Links (Track mode): immediate performance access
    prog_q = {
        "Q-Link 1":  17,  # LPF Cutoff
        "Q-Link 2":  18,  # LPF Peak
        "Q-Link 3":  13,  # HPF Cutoff
        "Q-Link 4":  14,  # HPF Peak
        "Q-Link 5":  20,  # LPF EG2 Mod
        "Q-Link 6":  27,  # EG2 Attack
        "Q-Link 7":  28,  # EG2 Decay
        "Q-Link 8":  30,  # EG2 Release
        "Q-Link 9":  9,   # VCO1 Level
        "Q-Link 10": 10,  # VCO2 Level
        "Q-Link 11": 5,   # VCO2 Pitch
        "Q-Link 12": 2,   # VCO1 PW
        "Q-Link 13": 22,  # MG Freq
        "Q-Link 14": 62,  # Delay Mix
        "Q-Link 15": 66,  # Reverb Mix
        "Q-Link 16": 0,   # Main Volume
    }

    return {
        "version": 4,
        "info": {"version": 1, "type": "CompleteDescription"},
        "Screen Mode Q-Links": {
            "version": 4,
            "map": [
                {"Tab": 1, "SubTab": 1, "Bank Direction": "Column", "Q-Links": t1_s1},
                {"Tab": 1, "SubTab": 2, "Bank Direction": "Column", "Q-Links": t1_s2},
                {"Tab": 2, "SubTab": 1, "Bank Direction": "Column", "Q-Links": t2_s1},
                {"Tab": 2, "SubTab": 2, "Bank Direction": "Column", "Q-Links": t2_s2},
                {"Tab": 3, "SubTab": 1, "Bank Direction": "Column", "Q-Links": t3_s1},
                {"Tab": 3, "SubTab": 2, "Bank Direction": "Column", "Q-Links": t3_s2},
            ],
        },
        "Program Mode Q-Links": prog_q,
    }


def main():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    tui = build_tui(manifest)
    qlinks = build_qlinks()
    tui_str = dump_mpc_json(tui) + "\n"
    ql_str = dump_mpc_json(qlinks) + "\n"

    for d in SKIN_DIRS:
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "TUI.json"), "w", encoding="utf-8") as fh:
            fh.write(tui_str)
        with open(os.path.join(d, "Q-Links.json"), "w", encoding="utf-8") as fh:
            fh.write(ql_str)
        print(f"Wrote {d}/TUI.json ({len(tui_str)} B) and Q-Links.json ({len(ql_str)} B)")


if __name__ == "__main__":
    main()
