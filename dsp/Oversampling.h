#pragma once
// Sobremuestreo 2x/4x/8x con FIR half-band en cascada (ventana de Kaiser). La última etapa
// (2x→1x) es la exigente: transición 20–28 kHz a 96 kHz, ~100 dB de rechazo. Las anteriores
// sólo tienen que limpiar lo que doblaría sobre la banda de audio, así que son cortas.

#include <cmath>
#include <vector>

namespace dh {

constexpr double kPiD = 3.14159265358979323846;

class HalfbandFir
{
public:
    void design (int taps, double beta)
    {
        n = taps | 1;
        h.assign ((size_t) n, 0.0f);
        const int m = n / 2;
        const double i0b = besselI0 (beta);
        for (int k = 0; k < n; ++k)
        {
            const int t = k - m;
            const double sinc = t == 0 ? 0.5 : std::sin (kPiD * t * 0.5) / (kPiD * t);
            const double r = (double) t / m;
            const double w = besselI0 (beta * std::sqrt (std::max (0.0, 1.0 - r * r))) / i0b;
            h[(size_t) k] = (float) (sinc * w);
        }
        hist.assign ((size_t) (2 * n), 0.0f);
        halfCount = (m + 1) / 2;
        hOdd.resize ((size_t) halfCount);
        for (int i = 0; i < halfCount; ++i)
        {
            const int k = 2 * i + 1;
            hOdd[(size_t) i] = h[(size_t) (m - k)];
        }
        hCenter = h[(size_t) m];
        pos = 0;
    }

    void reset() { std::fill (hist.begin(), hist.end(), 0.0f); pos = 0; }

    inline void push (float x)
    {
        pos = (pos == 0 ? n : pos) - 1;
        hist[(size_t) pos] = hist[(size_t) (pos + n)] = x;
    }

    inline float output() const
    {
        // Half-band FIR: every even offset != 0 is exact zero, and taps are symmetric around center m.
        const float* x = hist.data() + pos;
        const int m = n >> 1;
        float acc = hCenter * x[m];
        const float* ho = hOdd.data();
        for (int i = 0; i < halfCount; ++i)
        {
            const int k = (i << 1) + 1;
            acc += ho[i] * (x[m - k] + x[m + k]);
        }
        return acc;
    }

private:
    static double besselI0 (double x)
    {
        double sum = 1.0, term = 1.0;
        for (int k = 1; k < 40; ++k) { term *= (x / (2.0 * k)) * (x / (2.0 * k)); sum += term; }
        return sum;
    }
    std::vector<float> h, hOdd, hist;
    float hCenter = 0.5f;
    int n = 1, halfCount = 0, pos = 0;
};

inline void designStage (HalfbandFir& f, int stageFromBase)
{
    // stageFromBase 0 = la etapa que entrega la frecuencia base (la más exigente).
    if (stageFromBase == 0) f.design (95, 9.0);
    else f.design (31, 7.0);
}

// Retardo de grupo, en muestras a la frecuencia base, de la cadena de medias bandas de un factor (el mismo para el
// diezmador y el interpolador): cada etapa de N coeficientes demora (N − 1)/2 muestras a su frecuencia.
inline double halfbandChainDelay (int factor)
{
    const int stages = factor >= 8 ? 3 : factor >= 4 ? 2 : factor >= 2 ? 1 : 0;
    double d = 0.0;
    for (int s = 0; s < stages; ++s)
    {
        const int taps = (stages - 1 - s) == 0 ? 95 : 31;            // como designStage
        d += 0.5 * (taps - 1) / (double) (1 << (stages - s));        // la etapa s corre a base · 2^(stages − s)
    }
    return d;
}

class Decimator
{
public:
    void prepare (int factor, int maxFrames = 1024)
    {
        stages = factor >= 8 ? 3 : factor >= 4 ? 2 : factor >= 2 ? 1 : 0;
        for (int s = 0; s < stages; ++s) designStage (fir[s], stages - 1 - s);
        const size_t need = (size_t) std::max (64, maxFrames) * 8u;
        stride = need / 2u;
        if (work.size() < need) work.assign (need, 0.0f);
    }

    void reset() { for (int s = 0; s < 3; ++s) fir[s].reset(); }

    // in: n·factor muestras; out: n muestras (se suma gain·y a out).
    void process (const float* in, float* out, int n, float gain)
    {
        if (stages == 0) { for (int i = 0; i < n; ++i) out[i] += gain * in[i]; return; }
        int len = n << stages;
        const float* src = in;
        for (int s = 0; s < stages; ++s)
        {
            const int outLen = len / 2;
            float* dst = s == stages - 1 ? nullptr : work.data() + (size_t) (s % 2) * stride;
            for (int i = 0; i < outLen; ++i)
            {
                fir[s].push (src[2 * i]);
                const float y = fir[s].output();   // ganancia de continua 1 (el ×2 es sólo al interpolar)
                fir[s].push (src[2 * i + 1]);
                if (dst) dst[i] = y; else out[i] += gain * y;
            }
            src = dst; len = outLen;
        }
    }

private:
    HalfbandFir fir[3];
    int stages = 0;
    size_t stride = 4096;
    std::vector<float> work;
};

class Interpolator
{
public:
    void prepare (int factor, int maxFrames = 1024)
    {
        stages = factor >= 8 ? 3 : factor >= 4 ? 2 : factor >= 2 ? 1 : 0;
        for (int s = 0; s < stages; ++s) designStage (fir[s], s);
        const size_t need = (size_t) std::max (64, maxFrames) * 16u;
        stride = need / 2u;
        if (work.size() < need) work.assign (need, 0.0f);
    }

    void reset() { for (int s = 0; s < 3; ++s) fir[s].reset(); }

    // in: n muestras; out: n·factor muestras.
    void process (const float* in, float* out, int n)
    {
        if (stages == 0) { std::copy (in, in + n, out); return; }
        const float* src = in;
        int len = n;
        for (int s = 0; s < stages; ++s)
        {
            float* dst = s == stages - 1 ? out : work.data() + (size_t) (s % 2) * stride;
            for (int i = 0; i < len; ++i)
            {
                fir[s].push (src[i] * 2.0f); dst[2 * i] = fir[s].output();
                fir[s].push (0.0f);          dst[2 * i + 1] = fir[s].output();
            }
            src = dst; len *= 2;
        }
    }

private:
    HalfbandFir fir[3];
    int stages = 0;
    size_t stride = 8192;
    std::vector<float> work;
};

} // namespace dh
