#pragma once
// AT20 MPC — Stable Parameter Registry, Indices & Physical Value Formatters.
// Frozen parameter order: never reorder existing indices; append new parameters at the end.
// Parameter 0 is Main Volume (harmless when nudged by the MPC host on load).

#include "../dsp/Engine.h"
#include "../dsp/PatchRouter.h"
#include "mpc_plugin.h"

#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

namespace at20 {

enum ParamIdx : int
{
    // 0: Harmless master volume (MPC host nudges param 0 on load)
    P_VOLUME = 0,

    // 1..30: Synth Panel knobs
    P_VCO1_WAVE,
    P_VCO1_PW,
    P_VCO1_SCALE,
    P_VCO2_WAVE,
    P_VCO2_PITCH,
    P_VCO2_SCALE,
    P_PORTAMENTO,
    P_MASTER_TUNE,
    P_VCO1_LEVEL,
    P_VCO2_LEVEL,
    P_FM_MG,
    P_FM_EG1,
    P_HPF_CUTOFF,
    P_HPF_PEAK,
    P_HPF_MOD_MG,
    P_HPF_MOD_EG2,
    P_LPF_CUTOFF,
    P_LPF_PEAK,
    P_LPF_MOD_MG,
    P_LPF_MOD_EG2,
    P_MG_WAVE,
    P_MG_FREQ,
    P_EG1_DELAY,
    P_EG1_ATTACK,
    P_EG1_RELEASE,
    P_EG2_HOLD,
    P_EG2_ATTACK,
    P_EG2_DECAY,
    P_EG2_SUSTAIN,
    P_EG2_RELEASE,

    // 31..35: ESP knobs
    P_ESP_LEVEL,
    P_ESP_LOWCUT,
    P_ESP_HIGHCUT,
    P_ESP_CVADJ,
    P_ESP_THRESH,

    // 36..41: Voice & Performance extensions
    P_VOICES,
    P_UNISON,
    P_DETUNE,
    P_SPREAD,
    P_PRIORITY,
    P_RETRIGGER,

    // 42..48: Analogue & System extensions
    P_FILTER_REV,
    P_ANALOG,
    P_MG_SYNC,
    P_BEND_RANGE,
    P_QUALITY,
    P_OUTPUT,
    P_EXT_SOURCE,

    // 49..57: Vocoder extensions
    P_VOC_ON,
    P_VOC_BANDS,
    P_VOC_GAIN,
    P_VOC_SHIFT,
    P_VOC_Q,
    P_VOC_ATTACK,
    P_VOC_RELEASE,
    P_VOC_HISS,
    P_VOC_MIX,

    // 58..62: Stereo Delay extensions
    P_DLY_ON,
    P_DLY_TIME,
    P_DLY_FB,
    P_DLY_TONE,
    P_DLY_MIX,

    // 63..66: Plate Reverb extensions
    P_REV_ON,
    P_REV_SIZE,
    P_REV_DAMP,
    P_REV_MIX,

    // 67..68: Performance controls (Patchbay outputs)
    P_WHEEL,
    P_MOMENTARY,

    // 69..83: 15 Patchbay input jack source assignments (0=Normalled, 1..20=Output Jack)
    P_PATCH_SRC_BASE = 69,
    // 84..98: 15 Patchbay input cable color assignments (0..5)
    P_PATCH_COL_BASE = P_PATCH_SRC_BASE + kNumInputJacks, // 84

    // 99..133: 35 Jack visual filmstrip state params (non-automatable)
    P_JACK_VIS_BASE = P_PATCH_COL_BASE + kNumInputJacks,  // 99
    // 134..168: 35 Jack tap hit-plate params (non-automatable)
    P_JACK_TAP_BASE = P_JACK_VIS_BASE + kNumJacks,        // 134

    // 169..174: Direct patchbay editor & status (non-automatable)
    P_PEDIT_SRC = P_JACK_TAP_BASE + kNumJacks,            // 169
    P_PEDIT_DST,                                          // 170
    P_PACT_CONN,                                          // 171
    P_PACT_DISC,                                          // 172
    P_PACT_CLEAR,                                         // 173
    P_PSTAT_TEXT,                                         // 174

    // 175..181: LEDs & Status readouts (non-automatable)
    P_LED_MG,                                             // 175
    P_LED_EG1,                                            // 176
    P_LED_ESP_PEAK,                                       // 177
    P_LED_ESP_TRIG,                                       // 178
    P_LED_VOC_SIG,                                        // 179
    P_STAT_PRESET,                                        // 180
    P_STAT_LAST,                                          // 181

    P_COUNT                                               // 182
};

// Map AT20V KnobId (0..35) -> ParamIdx (0..35).
inline int paramIdxForKnob (int knobId)
{
    switch ((dh::KnobId) knobId)
    {
        case dh::KnobId::vco1_wave:    return P_VCO1_WAVE;
        case dh::KnobId::vco1_pw:      return P_VCO1_PW;
        case dh::KnobId::vco1_scale:   return P_VCO1_SCALE;
        case dh::KnobId::vco2_wave:    return P_VCO2_WAVE;
        case dh::KnobId::vco2_pitch:   return P_VCO2_PITCH;
        case dh::KnobId::vco2_scale:   return P_VCO2_SCALE;
        case dh::KnobId::portamento:   return P_PORTAMENTO;
        case dh::KnobId::master_tune:  return P_MASTER_TUNE;
        case dh::KnobId::vco1_level:   return P_VCO1_LEVEL;
        case dh::KnobId::vco2_level:   return P_VCO2_LEVEL;
        case dh::KnobId::fm_mg:        return P_FM_MG;
        case dh::KnobId::fm_eg1:       return P_FM_EG1;
        case dh::KnobId::hpf_cutoff:   return P_HPF_CUTOFF;
        case dh::KnobId::hpf_peak:     return P_HPF_PEAK;
        case dh::KnobId::hpf_mod_mg:   return P_HPF_MOD_MG;
        case dh::KnobId::hpf_mod_eg2:  return P_HPF_MOD_EG2;
        case dh::KnobId::lpf_cutoff:   return P_LPF_CUTOFF;
        case dh::KnobId::lpf_peak:     return P_LPF_PEAK;
        case dh::KnobId::lpf_mod_mg:   return P_LPF_MOD_MG;
        case dh::KnobId::lpf_mod_eg2:  return P_LPF_MOD_EG2;
        case dh::KnobId::mg_wave:      return P_MG_WAVE;
        case dh::KnobId::mg_freq:      return P_MG_FREQ;
        case dh::KnobId::eg1_delay:    return P_EG1_DELAY;
        case dh::KnobId::eg1_attack:   return P_EG1_ATTACK;
        case dh::KnobId::eg1_release:  return P_EG1_RELEASE;
        case dh::KnobId::eg2_hold:     return P_EG2_HOLD;
        case dh::KnobId::eg2_attack:   return P_EG2_ATTACK;
        case dh::KnobId::eg2_decay:    return P_EG2_DECAY;
        case dh::KnobId::eg2_sustain:  return P_EG2_SUSTAIN;
        case dh::KnobId::eg2_release:  return P_EG2_RELEASE;
        case dh::KnobId::volume:       return P_VOLUME;
        case dh::KnobId::esp_level:    return P_ESP_LEVEL;
        case dh::KnobId::esp_lowcut:   return P_ESP_LOWCUT;
        case dh::KnobId::esp_highcut:  return P_ESP_HIGHCUT;
        case dh::KnobId::esp_cvadj:    return P_ESP_CVADJ;
        case dh::KnobId::esp_thresh:   return P_ESP_THRESH;
        default:                       return -1;
    }
}

inline constexpr float kDelayBeats[12] = {
    0.125f, 1.0f / 6.0f, 0.25f, 0.375f, 1.0f / 3.0f, 0.5f,
    0.75f, 2.0f / 3.0f, 1.0f, 1.5f, 2.0f, 4.0f
};
inline constexpr int kVoiceChoices[6] = { 1, 2, 4, 6, 8, 12 };
inline constexpr int kVocBands[4]     = { 8, 12, 16, 20 };

inline float dbToGain (float db) { return std::pow (10.0f, db * 0.05f); }

inline std::string fmtTimeShort (float s)
{
    char buf[32];
    if (s <= 0.0f) return "0 ms";
    if (s < 0.01f) { std::snprintf (buf, sizeof (buf), "%.1fms", (double) (s * 1000.0f)); return buf; }
    if (s < 1.0f)  { std::snprintf (buf, sizeof (buf), "%.0fms", (double) (s * 1000.0f)); return buf; }
    std::snprintf (buf, sizeof (buf), "%.2fs", (double) s);
    return buf;
}

inline std::string fmtHzShort (float hz)
{
    char buf[32];
    if (hz < 10.0f)    { std::snprintf (buf, sizeof (buf), "%.2fHz", (double) hz); return buf; }
    if (hz < 100.0f)   { std::snprintf (buf, sizeof (buf), "%.1fHz", (double) hz); return buf; }
    if (hz < 1000.0f)  { std::snprintf (buf, sizeof (buf), "%.0fHz", (double) hz); return buf; }
    std::snprintf (buf, sizeof (buf), "%.2fkHz", (double) (hz * 0.001f));
    return buf;
}

// Compact physical display formatting for MPC screen & automation readouts.
inline bool formatParamDisplay (int idx, float v, bool mgSync, std::string& out)
{
    char buf[48];
    switch (idx)
    {
        case P_VCO2_PITCH:
            std::snprintf (buf, sizeof (buf), "%+.1f st", (double) (dh::cal::vco2PitchOct (v) * 12.0f));
            out = buf; return true;
        case P_MASTER_TUNE:
            std::snprintf (buf, sizeof (buf), "%+.0f ct", (double) (dh::cal::masterTuneOct (v) * 1200.0f));
            out = buf; return true;
        case P_PORTAMENTO:
            out = fmtTimeShort (dh::cal::portamento (v)); return true;
        case P_HPF_CUTOFF:
        case P_LPF_CUTOFF:
            out = fmtHzShort (std::exp2 (dh::cal::cutoffOct (v))); return true;
        case P_MG_FREQ:
            if (mgSync) { out = dh::cal::syncName (dh::cal::syncIndex (v)); return true; }
            out = fmtHzShort (dh::cal::mgHz (v)); return true;
        case P_MG_WAVE:
            if (v < 0.47f) { std::snprintf (buf, sizeof (buf), "Dn %.1f", (double) (v * 10.0f)); out = buf; }
            else if (v > 0.53f) { std::snprintf (buf, sizeof (buf), "Up %.1f", (double) (v * 10.0f)); out = buf; }
            else out = "Tri";
            return true;
        case P_EG1_DELAY:   out = fmtTimeShort (dh::cal::delay (v)); return true;
        case P_EG2_HOLD:    out = fmtTimeShort (dh::cal::hold (v)); return true;
        case P_EG1_ATTACK:
        case P_EG2_ATTACK:  out = fmtTimeShort (dh::cal::attack (v)); return true;
        case P_EG1_RELEASE:
        case P_EG2_DECAY:
        case P_EG2_RELEASE: out = fmtTimeShort (dh::cal::decay (v)); return true;
        case P_ESP_LOWCUT:  out = fmtHzShort (dh::cal::espLowCut (v)); return true;
        case P_ESP_HIGHCUT: out = fmtHzShort (dh::cal::espHighCut (v)); return true;
        case P_VOLUME:
        case P_VCO1_PW:
        case P_VCO1_LEVEL:
        case P_VCO2_LEVEL:
        case P_FM_MG:
        case P_FM_EG1:
        case P_HPF_PEAK:
        case P_HPF_MOD_MG:
        case P_HPF_MOD_EG2:
        case P_LPF_PEAK:
        case P_LPF_MOD_MG:
        case P_LPF_MOD_EG2:
        case P_EG2_SUSTAIN:
        case P_ESP_LEVEL:
        case P_ESP_CVADJ:
        case P_ESP_THRESH:
        case P_ANALOG:
        case P_SPREAD:
        case P_VOC_Q:
        case P_VOC_HISS:
        case P_VOC_MIX:
        case P_DLY_TONE:
        case P_DLY_MIX:
        case P_REV_SIZE:
        case P_REV_DAMP:
        case P_REV_MIX:
            std::snprintf (buf, sizeof (buf), "%.1f", (double) (v * 10.0f));
            out = buf; return true;
        case P_DLY_FB:
            std::snprintf (buf, sizeof (buf), "%.0f%%", (double) (v * 100.0f));
            out = buf; return true;
        case P_DETUNE:
            std::snprintf (buf, sizeof (buf), "%.1f ct", (double) v);
            out = buf; return true;
        case P_OUTPUT:
        case P_VOC_GAIN:
            std::snprintf (buf, sizeof (buf), "%+.1f dB", (double) v);
            out = buf; return true;
        case P_VOC_SHIFT:
            std::snprintf (buf, sizeof (buf), "%+.1f st", (double) (v * 12.0f));
            out = buf; return true;
        case P_VOC_ATTACK:
            std::snprintf (buf, sizeof (buf), "%.1fms", (double) (1.0f + 99.0f * v * v));
            out = buf; return true;
        case P_VOC_RELEASE:
            std::snprintf (buf, sizeof (buf), "%.0fms", (double) (10.0f + 990.0f * v * v));
            out = buf; return true;
        case P_WHEEL:
            std::snprintf (buf, sizeof (buf), "%+.1fV", (double) (v * 5.0f));
            out = buf; return true;
        default:
            return false;
    }
}

// Register all 182 parameters onto an mpc::Plugin in exact ParamIdx order.
inline void registerAllParams (mpc::Plugin& plugin)
{
    using namespace mpc;
    auto addNonAuto = [&] (Param p) { p.automatable = false; plugin.addParam (p); };

    const auto norm = dh::Engine::normalSetting();
    auto nk = [&] (dh::KnobId k) { return norm[(size_t) k]; };

    // 0: Main Volume
    plugin.addParam (floatParam ("volume", "Main Volume", 0.0f, 1.0f, nk (dh::KnobId::volume), "", 2));

    // 1..30: Synth Panel
    plugin.addParam (choiceParam ("vco1_wave",   "VCO1 Wave",    { "Tri", "Saw", "Pulse", "Noise" }, (int) nk (dh::KnobId::vco1_wave)));
    plugin.addParam (floatParam  ("vco1_pw",     "VCO1 PW",      0.0f, 1.0f, nk (dh::KnobId::vco1_pw)));
    plugin.addParam (choiceParam ("vco1_scale",  "VCO1 Scale",   { "32'", "16'", "8'", "4'" }, (int) nk (dh::KnobId::vco1_scale)));
    plugin.addParam (choiceParam ("vco2_wave",   "VCO2 Wave",    { "Saw", "Square", "Narrow", "Ring" }, (int) nk (dh::KnobId::vco2_wave)));
    plugin.addParam (floatParam  ("vco2_pitch",  "VCO2 Pitch",   0.0f, 1.0f, nk (dh::KnobId::vco2_pitch)));
    plugin.addParam (choiceParam ("vco2_scale",  "VCO2 Scale",   { "16'", "8'", "4'", "2'" }, (int) nk (dh::KnobId::vco2_scale)));
    plugin.addParam (floatParam  ("portamento",  "Portamento",   0.0f, 1.0f, nk (dh::KnobId::portamento)));
    plugin.addParam (floatParam  ("master_tune", "Master Tune",  0.0f, 1.0f, nk (dh::KnobId::master_tune)));
    plugin.addParam (floatParam  ("vco1_level",  "VCO1 Level",   0.0f, 1.0f, nk (dh::KnobId::vco1_level)));
    plugin.addParam (floatParam  ("vco2_level",  "VCO2 Level",   0.0f, 1.0f, nk (dh::KnobId::vco2_level)));
    plugin.addParam (floatParam  ("fm_mg",       "FM MG/TExt",   0.0f, 1.0f, nk (dh::KnobId::fm_mg)));
    plugin.addParam (floatParam  ("fm_eg1",      "FM EG1/Ext",   0.0f, 1.0f, nk (dh::KnobId::fm_eg1)));
    plugin.addParam (floatParam  ("hpf_cutoff",  "HPF Cutoff",   0.0f, 1.0f, nk (dh::KnobId::hpf_cutoff)));
    plugin.addParam (floatParam  ("hpf_peak",    "HPF Peak",     0.0f, 1.0f, nk (dh::KnobId::hpf_peak)));
    plugin.addParam (floatParam  ("hpf_mod_mg",  "HPF MG Mod",   0.0f, 1.0f, nk (dh::KnobId::hpf_mod_mg)));
    plugin.addParam (floatParam  ("hpf_mod_eg2", "HPF EG2 Mod",  0.0f, 1.0f, nk (dh::KnobId::hpf_mod_eg2)));
    plugin.addParam (floatParam  ("lpf_cutoff",  "LPF Cutoff",   0.0f, 1.0f, nk (dh::KnobId::lpf_cutoff)));
    plugin.addParam (floatParam  ("lpf_peak",    "LPF Peak",     0.0f, 1.0f, nk (dh::KnobId::lpf_peak)));
    plugin.addParam (floatParam  ("lpf_mod_mg",  "LPF MG Mod",   0.0f, 1.0f, nk (dh::KnobId::lpf_mod_mg)));
    plugin.addParam (floatParam  ("lpf_mod_eg2", "LPF EG2 Mod",  0.0f, 1.0f, nk (dh::KnobId::lpf_mod_eg2)));
    plugin.addParam (floatParam  ("mg_wave",     "MG Wave",      0.0f, 1.0f, nk (dh::KnobId::mg_wave)));
    plugin.addParam (floatParam  ("mg_freq",     "MG Freq",      0.0f, 1.0f, nk (dh::KnobId::mg_freq)));
    plugin.addParam (floatParam  ("eg1_delay",   "EG1 Delay",    0.0f, 1.0f, nk (dh::KnobId::eg1_delay)));
    plugin.addParam (floatParam  ("eg1_attack",  "EG1 Attack",   0.0f, 1.0f, nk (dh::KnobId::eg1_attack)));
    plugin.addParam (floatParam  ("eg1_release", "EG1 Release",  0.0f, 1.0f, nk (dh::KnobId::eg1_release)));
    plugin.addParam (floatParam  ("eg2_hold",    "EG2 Hold",     0.0f, 1.0f, nk (dh::KnobId::eg2_hold)));
    plugin.addParam (floatParam  ("eg2_attack",  "EG2 Attack",   0.0f, 1.0f, nk (dh::KnobId::eg2_attack)));
    plugin.addParam (floatParam  ("eg2_decay",   "EG2 Decay",    0.0f, 1.0f, nk (dh::KnobId::eg2_decay)));
    plugin.addParam (floatParam  ("eg2_sustain", "EG2 Sustain",  0.0f, 1.0f, nk (dh::KnobId::eg2_sustain)));
    plugin.addParam (floatParam  ("eg2_release", "EG2 Release",  0.0f, 1.0f, nk (dh::KnobId::eg2_release)));

    // 31..35: ESP
    plugin.addParam (floatParam  ("esp_level",   "ESP Level",    0.0f, 1.0f, nk (dh::KnobId::esp_level)));
    plugin.addParam (floatParam  ("esp_lowcut",  "ESP Low Cut",  0.0f, 1.0f, nk (dh::KnobId::esp_lowcut)));
    plugin.addParam (floatParam  ("esp_highcut", "ESP High Cut", 0.0f, 1.0f, nk (dh::KnobId::esp_highcut)));
    plugin.addParam (floatParam  ("esp_cvadj",   "ESP CV Adj",   0.0f, 1.0f, nk (dh::KnobId::esp_cvadj)));
    plugin.addParam (floatParam  ("esp_thresh",  "ESP Thresh",   0.0f, 1.0f, nk (dh::KnobId::esp_thresh)));

    // 36..41: Voice & Performance
    plugin.addParam (choiceParam ("voices",    "Voices",     { "Mono", "2", "4", "6", "8", "12" }, 0));
    plugin.addParam (choiceParam ("unison",    "Unison",     { "1", "2", "3", "4" }, 0));
    plugin.addParam (floatParam  ("detune",    "Uni Detune", 0.0f, 50.0f, 12.0f, "ct", 1));
    plugin.addParam (floatParam  ("spread",    "Spread",     0.0f, 1.0f, 0.6f));
    plugin.addParam (choiceParam ("priority",  "Priority",   { "Last", "High", "Low" }, 1));
    plugin.addParam (boolParam   ("retrigger", "Retrigger",  false));

    // 42..48: Analogue & System
    plugin.addParam (choiceParam ("filter_rev", "Filter Rev",   { "Korg35", "OTA" }, 0));
    plugin.addParam (floatParam  ("analog",     "Analog Drift", 0.0f, 1.0f, 0.35f));
    plugin.addParam (choiceParam ("mg_sync",    "MG Clock",     { "Free", "Sync" }, 0));
    plugin.addParam (choiceParam ("bend_range", "Bend Range",   { "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12" }, 2));
    plugin.addParam (choiceParam ("quality",    "Oversample",   { "2x", "4x", "8x" }, 1));
    plugin.addParam (floatParam  ("output",     "Output dB",    -24.0f, 6.0f, 0.0f, "dB", 1));
    plugin.addParam (choiceParam ("ext_source", "Ext Audio",    { "Audio In", "Synth Self", "Noise" }, 0));

    // 49..57: Vocoder
    plugin.addParam (boolParam   ("voc_on",      "Vocoder",     false));
    plugin.addParam (choiceParam ("voc_bands",   "Voc Bands",   { "8", "12", "16", "20" }, 2));
    plugin.addParam (floatParam  ("voc_gain",    "Voc Input",   -12.0f, 24.0f, 6.0f, "dB", 1));
    plugin.addParam (floatParam  ("voc_shift",   "Voc Formant", -1.0f, 1.0f, 0.0f));
    plugin.addParam (floatParam  ("voc_q",       "Voc Reso",    0.0f, 1.0f, 0.5f));
    plugin.addParam (floatParam  ("voc_attack",  "Voc Attack",  0.0f, 1.0f, 0.2f));
    plugin.addParam (floatParam  ("voc_release", "Voc Release", 0.0f, 1.0f, 0.3f));
    plugin.addParam (floatParam  ("voc_hiss",    "Voc Sibil",   0.0f, 1.0f, 0.4f));
    plugin.addParam (floatParam  ("voc_mix",     "Voc Mix",     0.0f, 1.0f, 1.0f));

    // 58..62: Delay
    plugin.addParam (boolParam   ("dly_on",   "Delay",      false));
    plugin.addParam (choiceParam ("dly_time", "Delay Time", { "1/32", "1/16T", "1/16", "1/16D", "1/8T", "1/8", "1/8D", "1/4T", "1/4", "1/4D", "1/2", "1 bar" }, 6));
    plugin.addParam (floatParam  ("dly_fb",   "Delay Fbk",  0.0f, 0.95f, 0.35f));
    plugin.addParam (floatParam  ("dly_tone", "Delay Tone", 0.0f, 1.0f, 0.6f));
    plugin.addParam (floatParam  ("dly_mix",  "Delay Mix",  0.0f, 1.0f, 0.25f));

    // 63..66: Reverb
    plugin.addParam (boolParam   ("rev_on",   "Reverb",     false));
    plugin.addParam (floatParam  ("rev_size", "Rev Size",   0.0f, 1.0f, 0.6f));
    plugin.addParam (floatParam  ("rev_damp", "Rev Damp",   0.0f, 1.0f, 0.4f));
    plugin.addParam (floatParam  ("rev_mix",  "Rev Mix",    0.0f, 1.0f, 0.25f));

    // 67..68: Performance
    plugin.addParam (floatParam  ("wheel",     "Ctrl Wheel", -1.0f, 1.0f, 0.0f));
    plugin.addParam (boolParam   ("momentary", "Mom Switch", false));

    // 69..83: 15 Patchbay input source choices
    std::vector<std::string> outChoices;
    outChoices.push_back ("Normal");
    for (int o = 0; o < kNumOutputJacks; ++o)
        outChoices.push_back (jackMeta (kOutputJackIds[o]).shortName);

    for (int i = 0; i < kNumInputJacks; ++i)
    {
        const int jid = kInputJackIds[i];
        std::string pid = std::string ("patch_") + dh::layout::jacks[jid].id;
        std::string pname = std::string ("In ") + jackMeta (jid).shortName;
        plugin.addParam (choiceParam (pid.c_str(), pname.c_str(), outChoices, 0));
    }

    // 84..98: 15 Patchbay cable color choices (non-automatable, saved with presets/state)
    const std::vector<std::string> colChoices = { "Red", "Blue", "Yellow", "Green", "White", "Black" };
    for (int i = 0; i < kNumInputJacks; ++i)
    {
        const int jid = kInputJackIds[i];
        std::string pid = std::string ("pcol_") + dh::layout::jacks[jid].id;
        std::string pname = std::string ("Col ") + jackMeta (jid).shortName;
        addNonAuto (choiceParam (pid.c_str(), pname.c_str(), colChoices, 0));
    }

    // 99..133: 35 Jack visual state params (non-automatable)
    for (int j = 0; j < kNumJacks; ++j)
    {
        char pid[32], pname[32];
        std::snprintf (pid, sizeof (pid), "jvis_%02d", j);
        std::snprintf (pname, sizeof (pname), "JVis %02d", j);
        addNonAuto (intParam (pid, pname, 0, kNumJackFrames - 1, 0));
    }

    // 134..168: 35 Jack tap hit-plate params (non-automatable)
    for (int j = 0; j < kNumJacks; ++j)
    {
        char pid[32], pname[32];
        std::snprintf (pid, sizeof (pid), "jtap_%02d", j);
        std::snprintf (pname, sizeof (pname), "JTap %02d", j);
        addNonAuto (boolParam (pid, pname, false));
    }

    // 169..174: Direct patch editor & status
    std::vector<std::string> outNamesOnly;
    for (int o = 0; o < kNumOutputJacks; ++o) outNamesOnly.push_back (jackMeta (kOutputJackIds[o]).shortName);
    std::vector<std::string> inNamesOnly;
    for (int i = 0; i < kNumInputJacks; ++i) inNamesOnly.push_back (jackMeta (kInputJackIds[i]).shortName);

    addNonAuto (choiceParam ("pedit_src",  "Patch Out",  outNamesOnly, 2)); // default MG TRI
    addNonAuto (choiceParam ("pedit_dst",  "Patch In",   inNamesOnly,  4)); // default LPF CUT
    addNonAuto (boolParam   ("pact_conn",  "Connect",    false));
    addNonAuto (boolParam   ("pact_disc",  "Unpatch",    false));
    addNonAuto (boolParam   ("pact_clear", "Clear All",  false));
    addNonAuto (intParam    ("pstat_text", "Patch Info", 0, 999, 0));

    // 175..181: LEDs & Status readouts
    addNonAuto (intParam ("led_mg",       "MG LED",      0, 1, 0));
    addNonAuto (intParam ("led_eg1",      "EG1 LED",     0, 3, 0));
    addNonAuto (intParam ("led_esp_peak", "ESP Peak",    0, 1, 0));
    addNonAuto (intParam ("led_esp_trig", "ESP Trig",    0, 1, 0));
    addNonAuto (intParam ("led_voc_sig",  "Voc Sig",     0, 1, 0));
    addNonAuto (intParam ("stat_preset",  "Status",      0, 999, 0));
    addNonAuto (intParam ("stat_last",    "Last Edit",   0, 999, 0));
}

} // namespace at20
