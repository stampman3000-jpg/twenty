// Compares upstream Audio Tools AT20V Engine vs ported AT20 MPC Engine sample-by-sample.
#include <cmath>
#include <cstdio>
#include <vector>

extern "C" void render_scenario_ref  (int scenario, float* outL, float* outR, int totalFrames);
extern "C" void render_scenario_port (int scenario, float* outL, float* outR, int totalFrames);

int main()
{
    const char* names[7] = {
        "0: Korg35 Rev1 LPF Sweep & Envelope",
        "1: OTA Rev2 High-Reso Self-Oscillation",
        "2: VCO2 Ring Modulation + VCO1 PWM",
        "3: Patchbay Sample&Hold + Feedback Loop",
        "4: ESP Preamp/BPF/YIN F-V/Trig Tracking",
        "5: Poly4 + Unison2 + Vocoder + Delay + Reverb",
        "6: 8x Oversampling High-Reso Korg35",
    };

    const int N = 22050; // 0.5 s @ 44.1 kHz
    std::vector<float> rL (N), rR (N), pL (N), pR (N);
    int fails = 0;

    std::printf ("=== Upstream AT20V Reference vs Ported AT20 MPC Sample Comparison ===\n");
    for (int s = 0; s < 7; ++s)
    {
        render_scenario_ref  (s, rL.data(), rR.data(), N);
        render_scenario_port (s, pL.data(), pR.data(), N);

        double maxErr = 0.0, sqErr = 0.0, sigSq = 0.0;
        for (int i = 0; i < N; ++i)
        {
            const double dL = (double) rL[(size_t) i] - (double) pL[(size_t) i];
            const double dR = (double) rR[(size_t) i] - (double) pR[(size_t) i];
            maxErr = std::max (maxErr, std::max (std::fabs (dL), std::fabs (dR)));
            sqErr += dL * dL + dR * dR;
            sigSq += (double) rL[(size_t) i] * rL[(size_t) i] + (double) rR[(size_t) i] * rR[(size_t) i];
        }
        const double rmsErr = std::sqrt (sqErr / (2.0 * N));
        const double sigRms = std::sqrt (sigSq / (2.0 * N));
        const double snrDb  = rmsErr > 0.0 ? 20.0 * std::log10 (sigRms / rmsErr) : 999.0;
        const bool ok = (maxErr < 1e-4 && snrDb > 95.0);
        if (! ok) ++fails;
        std::printf ("%s  %-46s  maxErr=%.2e  rmsErr=%.2e  SNR=%.1f dB\n",
                     ok ? "PASS" : "FAIL", names[s], maxErr, rmsErr, snrDb);
    }
    std::printf ("\nReference comparison: %d/7 high-precision match (>95 dB SNR, fails=%d)\n", 7 - fails, fails);
    return fails == 0 ? 0 : 1;
}
