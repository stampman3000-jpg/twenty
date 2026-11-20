// AT20 MPC — Standalone CPU Benchmark Harness
// Measures per-block wall time & CPU% relative to MPC's 44.1 kHz / 128-frame (2902 us)
// and 256-frame (5805 us) real-time audio budgets across all key synthesis scenarios.

#include "../dsp/Engine.h"
#include "../dsp/PatchRouter.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <vector>

struct BenchResult
{
    const char* name;
    double avgUs;
    double p99Us;
    double maxUs;
    double cpu128Pct;
    double cpu256Pct;
};

static BenchResult runScenario (const char* name, int voices, int unison, int os,
                                bool highReso, int filterRev, bool feedback, bool espYin,
                                bool vocoder, int vocBands, bool fxOn, int blockFrames = 128)
{
    const double sr = 44100.0;
    const int warmupBlocks = 30;
    const int measureBlocks = 400; // ~1.16 s of real-time audio

    dh::Engine eng;
    eng.prepare (sr, 64, os);
    eng.knobs = dh::Engine::normalSetting();
    eng.settings.voices = voices;
    eng.settings.unison = unison;
    eng.settings.filterRev = filterRev;
    eng.settings.analog = 0.35f;

    if (highReso)
    {
        eng.knobs[(size_t) dh::KnobId::hpf_cutoff] = 0.25f;
        eng.knobs[(size_t) dh::KnobId::hpf_peak]   = 0.92f;
        eng.knobs[(size_t) dh::KnobId::lpf_cutoff] = 0.55f;
        eng.knobs[(size_t) dh::KnobId::lpf_peak]   = 0.95f;
    }
    if (feedback)
    {
        eng.patch.src[(size_t) dh::JackId::ext_sig_in] = (int8_t) dh::JackId::phones_out;
        eng.patch.src[(size_t) dh::JackId::lpf_cut_in] = (int8_t) dh::JackId::mg_tri_out;
    }
    if (espYin)
    {
        eng.patch.src[(size_t) dh::JackId::vco12_cv_in] = (int8_t) dh::JackId::esp_fv_out;
        eng.patch.src[(size_t) dh::JackId::kbd_trig_in] = (int8_t) dh::JackId::esp_trig_out;
    }
    if (vocoder)
    {
        eng.fx.vocOn = true;
        eng.fx.vocBands = vocBands;
        eng.fx.vocMix = 1.0f;
    }
    if (fxOn)
    {
        eng.fx.dlyOn = true; eng.fx.dlyMix = 0.3f;
        eng.fx.revOn = true; eng.fx.revMix = 0.3f;
    }

    // Trigger chord matching requested polyphony
    const int notes[12] = { 48, 52, 55, 60, 64, 67, 71, 72, 76, 79, 83, 84 };
    const int polyNotes = std::max (1, voices <= 1 ? 1 : std::min (voices, 12 / unison));
    for (int i = 0; i < polyNotes; ++i) eng.noteOn (notes[i], 1.0f);

    std::vector<float> L (blockFrames, 0.0f), R (blockFrames, 0.0f), extIn (blockFrames, 0.0f);
    for (int i = 0; i < blockFrames; ++i)
        extIn[(size_t) i] = 0.4f * std::sin (dh::kTwoPi * 220.0f * i / (float) sr);

    const float* espPtr = (espYin || vocoder) ? extIn.data() : nullptr;

    auto renderOne = [&] () {
        for (int pos = 0; pos < blockFrames; pos += 64)
        {
            const int n = std::min (64, blockFrames - pos);
            eng.render (L.data() + pos, R.data() + pos, espPtr ? espPtr + pos : nullptr, n);
        }
    };

    for (int b = 0; b < warmupBlocks; ++b) renderOne();

    std::vector<double> timesUs;
    timesUs.reserve (measureBlocks);
    for (int b = 0; b < measureBlocks; ++b)
    {
        const auto t0 = std::chrono::steady_clock::now();
        renderOne();
        const auto t1 = std::chrono::steady_clock::now();
        timesUs.push_back (std::chrono::duration<double, std::micro> (t1 - t0).count());
    }

    double sum = 0.0;
    for (double t : timesUs) sum += t;
    std::sort (timesUs.begin(), timesUs.end());
    const double avg = sum / (double) timesUs.size();
    const double p99 = timesUs[(size_t) (timesUs.size() * 99 / 100)];
    const double mx  = timesUs.back();
    const double budget128 = (128.0 / sr) * 1e6; // 2902.49 us
    return { name, avg, p99, mx, (avg / budget128) * 100.0, (p99 / budget128) * 100.0 };
}

int main()
{
    std::printf ("=== AT20 MPC CPU Benchmark (44.1 kHz, 128-frame block = 2902.5 us) ===\n");
    std::printf ("%-38s %8s %8s %8s %8s %8s\n", "Scenario", "Avg(us)", "p99(us)", "Max(us)", "Avg%128", "p99%128");
    std::printf ("------------------------------------------------------------------------------------\n");

    const BenchResult results[] = {
        runScenario ("Mono Init (2x, Korg35)",           1, 1, 2, false, 1, false, false, false, 16, false),
        runScenario ("Mono High-Reso Self-Osc (2x)",     1, 1, 2, true,  1, false, false, false, 16, false),
        runScenario ("Poly 2 Voices (2x)",               2, 1, 2, false, 1, false, false, false, 16, false),
        runScenario ("Poly 4 Voices (2x)",               4, 1, 2, false, 1, false, false, false, 16, false),
        runScenario ("Poly 4 Voices + Delay + Rev (2x)", 4, 1, 2, false, 1, false, false, false, 16, true),
        runScenario ("Poly 4 High-Reso Self-Osc (2x)",   4, 1, 2, true,  1, false, false, false, 16, false),
        runScenario ("Poly 4 x Unison 2 = 8v (2x)",      4, 2, 2, false, 1, false, false, false, 16, false),
        runScenario ("Mono Init (4x, Korg35)",           1, 1, 4, false, 1, false, false, false, 16, false),
        runScenario ("Mono Init (4x, OTA Rev2)",         1, 1, 4, false, 2, false, false, false, 16, false),
        runScenario ("Mono High-Reso Self-Osc (4x)",     1, 1, 4, true,  1, false, false, false, 16, false),
        runScenario ("Mono Init (8x oversampling)",      1, 1, 8, false, 1, false, false, false, 16, false),
        runScenario ("Mono Feedback Patch (4x)",         1, 1, 4, true,  1, true,  false, false, 16, false),
        runScenario ("Mono + ESP YIN Pitch Track (4x)",  1, 1, 4, false, 1, false, true,  false, 16, false),
        runScenario ("Mono + Delay + Plate Reverb (4x)", 1, 1, 4, false, 1, false, false, false, 16, true),
        runScenario ("Mono + 16-Band Vocoder (4x)",      1, 1, 4, false, 1, false, false, true,  16, false),
        runScenario ("Mono + 20-Band Vocoder + FX (4x)", 1, 1, 4, false, 1, false, false, true,  20, true),
        runScenario ("Poly 2 Voices (4x)",               2, 1, 4, false, 1, false, false, false, 16, false),
        runScenario ("Poly 4 Voices (4x)",               4, 1, 4, false, 1, false, false, false, 16, false),
        runScenario ("Poly 4 Voices + Delay + Rev (4x)", 4, 1, 4, false, 1, false, false, false, 16, true),
        runScenario ("Poly 4 High-Reso Self-Osc (4x)",   4, 1, 4, true,  1, false, false, false, 16, false),
        runScenario ("Poly 6 Voices (4x)",               6, 1, 4, false, 1, false, false, false, 16, false),
        runScenario ("Poly 8 Voices (4x)",               8, 1, 4, false, 1, false, false, false, 16, false),
        runScenario ("Poly 12 Voices (4x)",             12, 1, 4, false, 1, false, false, false, 16, false),
        runScenario ("Mono Unison 2 (4x)",               1, 2, 4, false, 1, false, false, false, 16, false),
        runScenario ("Mono Unison 4 (4x)",               1, 4, 4, false, 1, false, false, false, 16, false),
        runScenario ("Poly 4 x Unison 2 = 8v + FX (4x)", 4, 2, 4, false, 1, false, false, false, 16, true),
    };

    for (const auto& r : results)
    {
        std::printf ("%-38s %8.1f %8.1f %8.1f %7.2f%% %7.2f%%\n",
                     r.name, r.avgUs, r.p99Us, r.maxUs, r.cpu128Pct, r.cpu256Pct);
    }
    return 0;
}
