// Compiles ported AT20 MPC Engine.h into a matching render function for bit/tolerance verification.
#include "../dsp/Engine.h"
#include <algorithm>
#include <cmath>
#include <vector>

extern "C" void render_scenario_port (int scenario, float* outL, float* outR, int totalFrames)
{
    const double sr = 44100.0;
    dh::Engine eng;
    eng.prepare (sr, 64, scenario == 6 ? 8 : 4);
    eng.knobs = dh::Engine::normalSetting();
    eng.settings.analog = 0.0f;

    std::vector<float> extIn ((size_t) totalFrames, 0.0f);
    for (int i = 0; i < totalFrames; ++i)
        extIn[(size_t) i] = 0.45f * std::sin (dh::kTwoPi * 220.0f * i / (float) sr);

    const float* espPtr = nullptr;

    switch (scenario)
    {
        case 0:
            eng.knobs[(size_t) dh::KnobId::lpf_cutoff] = 0.45f;
            eng.knobs[(size_t) dh::KnobId::lpf_peak]   = 0.72f;
            eng.knobs[(size_t) dh::KnobId::lpf_mod_eg2] = 0.55f;
            eng.knobs[(size_t) dh::KnobId::eg2_decay] = 0.3f;
            eng.knobs[(size_t) dh::KnobId::eg2_sustain] = 0.35f;
            eng.noteOn (48, 1.0f);
            break;
        case 1:
            eng.settings.filterRev = 2;
            eng.knobs[(size_t) dh::KnobId::hpf_cutoff] = 0.25f;
            eng.knobs[(size_t) dh::KnobId::hpf_peak]   = 0.92f;
            eng.knobs[(size_t) dh::KnobId::lpf_cutoff] = 0.52f;
            eng.knobs[(size_t) dh::KnobId::lpf_peak]   = 0.94f;
            eng.noteOn (60, 1.0f);
            break;
        case 2:
            eng.knobs[(size_t) dh::KnobId::vco1_wave] = 2.0f;
            eng.knobs[(size_t) dh::KnobId::vco1_pw]   = 0.35f;
            eng.knobs[(size_t) dh::KnobId::vco2_wave] = 3.0f;
            eng.knobs[(size_t) dh::KnobId::vco2_pitch] = 0.71f;
            eng.noteOn (57, 1.0f);
            break;
        case 3:
            eng.patch.src[(size_t) dh::JackId::sh_in]       = (int8_t) dh::JackId::pink_out;
            eng.patch.src[(size_t) dh::JackId::sh_clock_in] = (int8_t) dh::JackId::mg_sq_out;
            eng.patch.src[(size_t) dh::JackId::total_in]    = (int8_t) dh::JackId::sh_out;
            eng.patch.src[(size_t) dh::JackId::ext_sig_in]  = (int8_t) dh::JackId::phones_out;
            eng.knobs[(size_t) dh::KnobId::fm_mg] = 0.5f;
            eng.knobs[(size_t) dh::KnobId::lpf_cutoff] = 0.55f;
            eng.knobs[(size_t) dh::KnobId::lpf_peak]   = 0.78f;
            eng.noteOn (55, 1.0f);
            break;
        case 4:
            eng.patch.src[(size_t) dh::JackId::vco12_cv_in] = (int8_t) dh::JackId::esp_fv_out;
            eng.patch.src[(size_t) dh::JackId::kbd_trig_in] = (int8_t) dh::JackId::esp_trig_out;
            eng.knobs[(size_t) dh::KnobId::esp_level] = 0.65f;
            eng.knobs[(size_t) dh::KnobId::esp_lowcut] = 0.1f;
            eng.knobs[(size_t) dh::KnobId::esp_highcut] = 0.9f;
            eng.knobs[(size_t) dh::KnobId::esp_thresh] = 0.25f;
            espPtr = extIn.data();
            break;
        case 5:
            eng.settings.voices = 4;
            eng.settings.unison = 2;
            eng.settings.detuneCents = 16.0f;
            eng.settings.spread = 0.75f;
            eng.settings.analog = 0.0f; // deterministic comparison (analog drift verified separately)
            eng.fx.vocOn = true; eng.fx.vocBands = 16; eng.fx.vocMix = 0.7f; eng.fx.vocInGain = 2.0f;
            eng.fx.dlyOn = true; eng.fx.dlyMix = 0.3f;
            eng.fx.revOn = true; eng.fx.revMix = 0.3f;
            eng.noteOn (60, 1.0f); eng.noteOn (64, 1.0f); eng.noteOn (67, 1.0f);
            espPtr = extIn.data();
            break;
        case 6:
            eng.knobs[(size_t) dh::KnobId::lpf_cutoff] = 0.6f;
            eng.knobs[(size_t) dh::KnobId::lpf_peak]   = 0.85f;
            eng.noteOn (62, 1.0f);
            break;
    }

    for (int pos = 0; pos < totalFrames; pos += 64)
    {
        const int n = std::min (64, totalFrames - pos);
        eng.render (outL + pos, outR + pos, espPtr ? espPtr + pos : nullptr, n);
    }
}
