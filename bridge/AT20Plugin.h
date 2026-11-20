#pragma once
// AT20 MPC / AT20 FX — Complete Akai MPC Standalone VST2 Plugin Adapter.
// Ports Audio Tools AT20V (dh::Engine) onto the official Akai MPC Plugin SDK (mpc_plugin.h).
//
// Signal flow:
//   MIDI (Note/CC/Bend) & Host Transport (BPM/PPQ)
//     -> Voice Pool (1..12 voices, 1..4 unison, analog drift)
//     -> Per-voice full MS-20 @ 4x/8x oversampling:
//        VCO1 + VCO2 (PWM, Ring) + Noise + Ext Signal In
//        -> HPF (Korg35 Rev1 / OTA Rev2) -> LPF (Korg35 Rev1 / OTA Rev2)
//        -> VCA (EG2 + Initial Gain) -> DC Blocker -> Main Volume
//        + 35-Jack Patchbay (1-sample feedback, ±15V rails, Hz/V, 1V/oct, S-trig)
//        + MG (Free / Tempo Sync), EG1, EG2, S/H, Mod VCA, ESP (Preamp/BPF/YIN F-V/Env/Trig)
//     -> Half-band FIR Decimator (4x/8x -> 1x)
//     -> Post-FX @ 1x: Vocoder (8..20 bands) -> Ping-Pong Stereo Delay -> Dattorro Plate Reverb
//     -> NaN Safety Guard -> Transparent Soft Limiter -> Stereo Out

#include "AT20Params.h"
#include "AT20Presets.generated.h"
#include "../dsp/Engine.h"
#include "../dsp/PatchRouter.h"
#include "mpc_plugin.h"

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

namespace at20 {

template <bool IsFx>
class AT20Plugin final : public mpc::Plugin
{
public:
    AT20Plugin() : mpc::Plugin (makePluginInfo()), engine_ (std::make_unique<dh::Engine>())
    {
        for (auto& a : patchAtomic_) a.store (-1, std::memory_order_relaxed);
        for (auto& d : uiDirty_) d.store (false, std::memory_order_relaxed);
        for (auto& t : lastTapMs_) t = 0;
        lastTapVal_.fill (false);

        // Register all 182 parameters in frozen ParamIdx order.
        registerAllParams (*this);

        // Register built-in factory presets (VST2 programs).
        registerPrograms();

        // Initialize engine & state from Program 0.
        applyProgramInitialState();

        // Start lightweight UI notifier worker (pushes derived visual params off audio/setParam threads).
        workerThread_ = std::thread ([this] { uiWorkerLoop(); });
    }

    ~AT20Plugin() override
    {
        stopWorker_.store (true, std::memory_order_release);
        if (workerThread_.joinable()) workerThread_.join();
    }

    static mpc::PluginInfo makePluginInfo()
    {
        mpc::PluginInfo info;
        if constexpr (IsFx)
        {
            info.name         = "Twenty FX";
            info.vendor       = "Stampman3000";
            info.uniqueId     = MPC_FOURCC ('T', 'W', 'F', 'X');
            info.version      = 1000;
            info.isInstrument = false;
            info.numInputs    = 2;
            info.numOutputs   = 2;
            info.wantsMidi    = false;
            info.sendsMidi    = false;
            info.latencySamples = 55; // 4x interpolator + decimator round-trip
            info.tailSamples  = 44100 * 4;
        }
        else
        {
            info.name         = "Twenty";
            info.vendor       = "Stampman3000";
            info.uniqueId     = MPC_FOURCC ('T', 'W', 'N', 'T');
            info.version      = 1000;
            info.isInstrument = true;
            info.numInputs    = 0;
            info.numOutputs   = 2;
            info.wantsMidi    = true;
            info.sendsMidi    = false;
            info.latencySamples = 27; // 4x decimator group delay
            info.tailSamples  = 44100 * 4;
        }
        return info;
    }

    void prepare (double sr, int maxBlockSize) override
    {
        currentSr_ = sr > 8000.0 ? sr : 44100.0;
        const int q = getInt (P_QUALITY);
        const int wantOs = (q <= 0) ? 2 : (q == 1 ? 4 : 8);
        engine_->prepare (currentSr_, 64, wantOs, false);

        const int bufCap = std::max (maxBlockSize, 1024) + 64;
        espMono_.assign ((size_t) bufCap, 0.0f);
        outL_.assign ((size_t) bufCap, 0.0f);
        outR_.assign ((size_t) bufCap, 0.0f);
        selfFeedback_.assign ((size_t) bufCap, 0.0f);

        snapSmoothers();
        updateReportedLatency (wantOs);
        syncPatchRouterToAudio();
        syncVisualsToParams (false);
        readyForHostNotify_.store (true, std::memory_order_release);
    }

    void reset() override
    {
        engine_->allNotesOff();
        engine_->resetFx();
        snapSmoothers();
        modWheel_ = 0.0f;
        bendWheel_ = 0.0f;
        momentaryPedal_ = false;
        std::fill (selfFeedback_.begin(), selfFeedback_.end(), 0.0f);
        syncPatchRouterToAudio();
    }

    void parameterChanged (int index, float plainValue) override
    {
        if (index < 0 || index >= P_COUNT) return;

        // Track last edited musical parameter for Page 1 status readout.
        if (index <= P_MOMENTARY)
        {
            lastEditedParam_.store (index, std::memory_order_relaxed);
            bumpStatusCounter (P_STAT_LAST);
            if (index == P_FILTER_REV || index == P_VOICES || index == P_QUALITY)
                bumpStatusCounter (P_STAT_PRESET);
            return;
        }

        // Direct patchbay input source or cable color parameter changed (preset load, Q-Link, automation).
        if (index >= P_PATCH_SRC_BASE && index < P_PATCH_SRC_BASE + kNumInputJacks)
        {
            const int inSlot = index - P_PATCH_SRC_BASE;
            const int outChoice = (int) std::lround (plainValue);
            {
                std::lock_guard<std::mutex> lk (routerMtx_);
                const int col = getInt (P_PATCH_COL_BASE + inSlot);
                patchRouter_.setInputSourceChoice (inSlot, outChoice, col);
                syncPatchRouterToAudioLocked();
                syncVisualsLocked (true);
            }
            return;
        }

        if (index >= P_PATCH_COL_BASE && index < P_PATCH_COL_BASE + kNumInputJacks)
        {
            const int inSlot = index - P_PATCH_COL_BASE;
            const int col = (int) std::lround (plainValue);
            {
                std::lock_guard<std::mutex> lk (routerMtx_);
                patchRouter_.setInputColor (inSlot, col);
                syncVisualsLocked (true);
            }
            return;
        }

        // Interactive 35-jack touch hit-plates (fires ONLY on actual 0<->1 transition, debounced 240 ms).
        if (index >= P_JACK_TAP_BASE && index < P_JACK_TAP_BASE + kNumJacks)
        {
            const int jackId = index - P_JACK_TAP_BASE;
            if (! passTapDebounce (jackId, plainValue >= 0.5f)) return;

            std::lock_guard<std::mutex> lk (routerMtx_);
            const auto res = patchRouter_.onJackTapped (jackId);
            if (res.routingChanged && res.changedInSlot >= 0)
            {
                const int s = res.changedInSlot;
                storeParamQuiet (P_PATCH_SRC_BASE + s, (float) patchRouter_.getInputSourceChoice (s));
                storeParamQuiet (P_PATCH_COL_BASE + s, (float) patchRouter_.getInputColor (s));
                markDirty (P_PATCH_SRC_BASE + s);
                markDirty (P_PATCH_COL_BASE + s);
            }
            // Mirror selected jack into Direct Patch Editor selectors for seamless hybrid editing.
            if (patchRouter_.getSelectedJack() >= 0)
            {
                const int sj = patchRouter_.getSelectedJack();
                if (isOutputJack (sj))
                {
                    const int os = jackToOutputSlot (sj);
                    if (os >= 0) { storeParamQuiet (P_PEDIT_SRC, (float) os); markDirty (P_PEDIT_SRC); }
                }
                else
                {
                    const int is = jackToInputSlot (sj);
                    if (is >= 0) { storeParamQuiet (P_PEDIT_DST, (float) is); markDirty (P_PEDIT_DST); }
                }
            }
            syncPatchRouterToAudioLocked();
            syncVisualsLocked (true);
            return;
        }

        // Direct Patch Editor action buttons (Connect / Unpatch / Clear All).
        if (index == P_PACT_CONN)
        {
            if (! passTapDebounce (kNumJacks + 0, plainValue >= 0.5f)) return;
            const int outSlot = getInt (P_PEDIT_SRC);
            const int inSlot  = getInt (P_PEDIT_DST);
            std::lock_guard<std::mutex> lk (routerMtx_);
            patchRouter_.setInputSourceChoice (inSlot, outSlot + 1, -1);
            patchRouter_.clearSelection();
            storeParamQuiet (P_PATCH_SRC_BASE + inSlot, (float) patchRouter_.getInputSourceChoice (inSlot));
            storeParamQuiet (P_PATCH_COL_BASE + inSlot, (float) patchRouter_.getInputColor (inSlot));
            markDirty (P_PATCH_SRC_BASE + inSlot);
            markDirty (P_PATCH_COL_BASE + inSlot);
            syncPatchRouterToAudioLocked();
            syncVisualsLocked (true);
            return;
        }

        if (index == P_PACT_DISC)
        {
            if (! passTapDebounce (kNumJacks + 1, plainValue >= 0.5f)) return;
            const int fallbackIn = getInt (P_PEDIT_DST);
            std::lock_guard<std::mutex> lk (routerMtx_);
            if (patchRouter_.disconnectSelectedOr (fallbackIn))
            {
                for (int i = 0; i < kNumInputJacks; ++i)
                {
                    storeParamQuiet (P_PATCH_SRC_BASE + i, (float) patchRouter_.getInputSourceChoice (i));
                    markDirty (P_PATCH_SRC_BASE + i);
                }
            }
            syncPatchRouterToAudioLocked();
            syncVisualsLocked (true);
            return;
        }

        if (index == P_PACT_CLEAR)
        {
            if (! passTapDebounce (kNumJacks + 2, plainValue >= 0.5f)) return;
            std::lock_guard<std::mutex> lk (routerMtx_);
            patchRouter_.clearAll();
            for (int i = 0; i < kNumInputJacks; ++i)
            {
                storeParamQuiet (P_PATCH_SRC_BASE + i, 0.0f);
                storeParamQuiet (P_PATCH_COL_BASE + i, 0.0f);
                markDirty (P_PATCH_SRC_BASE + i);
                markDirty (P_PATCH_COL_BASE + i);
            }
            syncPatchRouterToAudioLocked();
            syncVisualsLocked (true);
            return;
        }
    }

    bool formatValue (int index, float plainValue, std::string& out) override
    {
        if (index == P_PSTAT_TEXT)
        {
            std::lock_guard<std::mutex> lk (routerMtx_);
            out = patchRouter_.statusLine();
            return true;
        }
        if (index == P_STAT_PRESET)
        {
            const char* pname = programName (currentProgram());
            const char* rev = getInt (P_FILTER_REV) == 1 ? "OTA" : "K35";
            const int actV = activeVoicesTelemetry_.load (std::memory_order_relaxed);
            char buf[48];
            std::snprintf (buf, sizeof (buf), "%.14s | %s | V:%d", pname ? pname : "Init", rev, actV);
            out = buf;
            return true;
        }
        if (index == P_STAT_LAST)
        {
            const int lp = lastEditedParam_.load (std::memory_order_relaxed);
            if (lp >= 0 && lp <= P_MOMENTARY)
            {
                std::string valStr;
                const float pv = get (lp);
                if (! formatParamDisplay (lp, pv, getInt (P_MG_SYNC) == 1, valStr))
                    valStr = param (lp).display (pv);
                char buf[48];
                std::snprintf (buf, sizeof (buf), "%.10s: %.12s", param (lp).name.c_str(), valStr.c_str());
                out = buf;
                return true;
            }
            out = "AT20 MPC READY";
            return true;
        }
        return formatParamDisplay (index, plainValue, getInt (P_MG_SYNC) == 1, out);
    }

    void saveExtraState (std::vector<uint8_t>& out) override
    {
        std::lock_guard<std::mutex> lk (routerMtx_);
        patchRouter_.serialize (out);
    }

    void loadExtraState (const uint8_t* data, size_t size) override
    {
        if (! data || size == 0) return;
        std::lock_guard<std::mutex> lk (routerMtx_);
        if (patchRouter_.deserialize (data, size))
            syncPatchRouterToAudioLocked();
    }

    void process (mpc::ProcessContext& ctx) override
    {
        const int n = ctx.numFrames;
        if (n <= 0) return;

        // Protect against unexpected oversized blocks without ever allocating on audio thread.
        const int cap = (int) outL_.size();
        if (cap <= 0) return;

        int offset = 0;
        while (offset < n)
        {
            const int chunk = std::min (n - offset, cap);
            processChunk (ctx, offset, chunk);
            offset += chunk;
        }
    }

private:
    void processChunk (mpc::ProcessContext& ctx, int baseOffset, int n)
    {
        // Realtime-safe oversampling toggle (2x / 4x / 8x, zero heap allocation).
        const int q = getInt (P_QUALITY);
        const int wantOs = (q <= 0) ? 2 : (q == 1 ? 4 : 8);
        if (wantOs != engine_->oversampling())
            engine_->setOversamplingRealtime (wantOs);

        // Read audio input BEFORE writing outputs (MPC runs in-place!).
        const int extSrc = getInt (P_EXT_SOURCE);
        const float* espPtr = nullptr;
        float peakIn = 0.0f;

        if constexpr (IsFx)
        {
            if (extSrc == 0 && ctx.inputs != nullptr && ctx.numInputs > 0 && ctx.inputs[0] != nullptr)
            {
                if (ctx.numInputs >= 2 && ctx.inputs[1] != nullptr)
                {
                    for (int i = 0; i < n; ++i)
                    {
                        const float s = 0.5f * (ctx.inputs[0][baseOffset + i] + ctx.inputs[1][baseOffset + i]);
                        espMono_[(size_t) i] = s;
                        peakIn = std::max (peakIn, std::fabs (s));
                    }
                }
                else
                {
                    for (int i = 0; i < n; ++i)
                    {
                        const float s = ctx.inputs[0][baseOffset + i];
                        espMono_[(size_t) i] = s;
                        peakIn = std::max (peakIn, std::fabs (s));
                    }
                }
                espPtr = espMono_.data();
            }
            else if (extSrc == 1)
            {
                for (int i = 0; i < n; ++i)
                {
                    const float s = selfFeedback_[(size_t) i];
                    espMono_[(size_t) i] = s;
                    peakIn = std::max (peakIn, std::fabs (s));
                }
                espPtr = espMono_.data();
            }
            else if (extSrc == 2)
            {
                for (int i = 0; i < n; ++i)
                {
                    const float s = extNoiseRng_.bipolar() * 0.5f;
                    espMono_[(size_t) i] = s;
                    peakIn = std::max (peakIn, std::fabs (s));
                }
                espPtr = espMono_.data();
            }
        }
        else
        {
            // Instrument: MPC feeds silence on audio inputs, so allow Synth Self or Noise into ESP/Vocoder!
            if (extSrc == 0 && ctx.inputs != nullptr && ctx.numInputs > 0 && ctx.inputs[0] != nullptr)
            {
                for (int i = 0; i < n; ++i)
                {
                    const float s = (ctx.numInputs >= 2 && ctx.inputs[1] != nullptr)
                        ? 0.5f * (ctx.inputs[0][baseOffset + i] + ctx.inputs[1][baseOffset + i])
                        : ctx.inputs[0][baseOffset + i];
                    espMono_[(size_t) i] = s;
                    peakIn = std::max (peakIn, std::fabs (s));
                }
                espPtr = espMono_.data();
            }
            else if (extSrc == 1)
            {
                for (int i = 0; i < n; ++i)
                {
                    const float s = selfFeedback_[(size_t) i];
                    espMono_[(size_t) i] = s;
                    peakIn = std::max (peakIn, std::fabs (s));
                }
                espPtr = espMono_.data();
            }
            else if (extSrc == 2)
            {
                for (int i = 0; i < n; ++i)
                {
                    const float s = extNoiseRng_.bipolar() * 0.5f;
                    espMono_[(size_t) i] = s;
                    peakIn = std::max (peakIn, std::fabs (s));
                }
                espPtr = espMono_.data();
            }
        }

        // Update engine Settings & FxSettings from atomic parameters.
        applySettingsFromParams();

        // Sync lock-free patchbay state into engine.
        for (int j = 0; j < kNumJacks; ++j)
            engine_->patch.src[(size_t) j] = patchAtomic_[(size_t) j].load (std::memory_order_relaxed);

        // Host transport (tempo & PPQ for MG sync and Stereo Delay).
        double bpm = 120.0, ppq = freePpq_;
        bool playing = false;
        if (ctx.transport.valid)
        {
            if (ctx.transport.tempoValid && ctx.transport.bpm > 20.0 && ctx.transport.bpm < 400.0)
                bpm = ctx.transport.bpm;
            playing = ctx.transport.playing;
            if (playing && ctx.transport.ppqValid)
                ppq = ctx.transport.ppqPos;
        }
        const double ppqPerSample = bpm / 60.0 / currentSr_;
        if (! playing)
            freePpq_ += (double) n * ppqPerSample;
        else
            freePpq_ = ppq + (double) n * ppqPerSample;

        engine_->settings.bpm = bpm;
        engine_->settings.playing = playing;

        // Sub-block loop (max 64 samples, splitting at MIDI event offsets — exact AT20V behavior).
        int midiIdx = 0;
        while (midiIdx < ctx.numMidiEvents && ctx.midi[midiIdx].sampleOffset < baseOffset)
            ++midiIdx;

        int pos = 0;
        while (pos < n)
        {
            int end = std::min (n, pos + 64);

            // Process MIDI events at or before current sample position.
            while (midiIdx < ctx.numMidiEvents && ctx.midi[midiIdx].sampleOffset <= baseOffset + pos)
            {
                handleMidi (ctx.midi[midiIdx]);
                ++midiIdx;
            }
            if (midiIdx < ctx.numMidiEvents)
            {
                const int nextRel = ctx.midi[midiIdx].sampleOffset - baseOffset;
                if (nextRel > pos && nextRel < end) end = nextRel;
            }

            // Smooth panel knobs identically to upstream AT20V (0.35 per sub-block for continuous, instant for selectors).
            for (int k = 0; k < dh::kNumKnobs; ++k)
            {
                const int pidx = paramIdxForKnob (k);
                const float target = get (pidx);
                if (dh::layout::knobs[k].steps > 0)
                    smoothedKnobs_[(size_t) k] = target;
                else
                    smoothedKnobs_[(size_t) k] += (target - smoothedKnobs_[(size_t) k]) * 0.35f;
                if (! dh::isFiniteF (smoothedKnobs_[(size_t) k]))
                    smoothedKnobs_[(size_t) k] = dh::isFiniteF (target) ? target : 0.0f;
            }
            engine_->knobs = smoothedKnobs_;

            // Combine UI Wheel + Pitch Bend + CC1 Mod Wheel, and UI Momentary + CC64 Sustain.
            engine_->settings.wheel = mpc::clamp (get (P_WHEEL) + bendWheel_ + modWheel_, -1.0f, 1.0f);
            engine_->settings.momentary = getBool (P_MOMENTARY) || momentaryPedal_;
            engine_->settings.ppq = ppq + (double) (baseOffset + pos) * ppqPerSample;

            engine_->render (outL_.data() + pos, outR_.data() + pos,
                             espPtr != nullptr ? espPtr + pos : nullptr, end - pos);
            pos = end;
        }

        // Write outputs and store mono feedback buffer for next block's optional Synth Self ESP mode.
        if (ctx.outputs != nullptr)
        {
            float* dstL = (ctx.numOutputs >= 1) ? ctx.outputs[0] : nullptr;
            float* dstR = (ctx.numOutputs >= 2) ? ctx.outputs[1] : nullptr;
            for (int i = 0; i < n; ++i)
            {
                float l = outL_[(size_t) i];
                float r = outR_[(size_t) i];
                if (std::fabs (l) < 1e-24f) l = 0.0f;
                if (std::fabs (r) < 1e-24f) r = 0.0f;
                if (dstL) dstL[baseOffset + i] = l;
                if (dstR) dstR[baseOffset + i] = r;
                selfFeedback_[(size_t) i] = 0.5f * (l + r);
            }
        }

        // Publish lightweight telemetry atomics (picked up by background UI worker if changed).
        const auto& v0 = engine_->voices[0];
        ledMgAtomic_.store (v0.ledMg ? 1 : 0, std::memory_order_relaxed);
        ledEg1Atomic_.store (mpc::clamp ((int) std::lround (v0.ledEg * 3.0f), 0, 3), std::memory_order_relaxed);
        ledEspPeakAtomic_.store (v0.ledEspPeak ? 1 : 0, std::memory_order_relaxed);
        ledEspTrigAtomic_.store (v0.ledEspTrig ? 1 : 0, std::memory_order_relaxed);
        ledVocSigAtomic_.store (peakIn > 0.02f ? 1 : 0, std::memory_order_relaxed);
        activeVoicesTelemetry_.store (engine_->playingVoiceCount(), std::memory_order_relaxed);
    }

    void handleMidi (const mpc::MidiEvent& e)
    {
        if (e.isNoteOn())
        {
            engine_->noteOn (e.note(), (float) e.velocity() / 127.0f);
        }
        else if (e.isNoteOff())
        {
            engine_->noteOff (e.note());
        }
        else if (e.isPitchBend())
        {
            const float v = (float) e.pitchBend() / 8192.0f;
            bendWheel_ = mpc::clamp (v, -1.0f, 1.0f);
            engine_->pitchBend (bendWheel_);
        }
        else if (e.isController())
        {
            const int cc = e.controller();
            const int val = e.controllerValue();
            if (cc == 1)        modWheel_ = (float) val / 127.0f;
            else if (cc == 64)  momentaryPedal_ = (val >= 64);
            else if (cc == 121) { modWheel_ = bendWheel_ = 0.0f; momentaryPedal_ = false; engine_->pitchBend (0.0f); }
            else if (cc == 120 || cc == 123) engine_->allNotesOff();
        }
    }

    void applySettingsFromParams()
    {
        auto& st = engine_->settings;
        auto& fx = engine_->fx;

        st.voices      = kVoiceChoices[mpc::clamp (getInt (P_VOICES), 0, 5)];
        st.unison      = 1 + mpc::clamp (getInt (P_UNISON), 0, 3);
        st.detuneCents = get (P_DETUNE);
        st.spread      = get (P_SPREAD);
        st.priority    = mpc::clamp (getInt (P_PRIORITY), 0, 2);
        st.retrigger   = getBool (P_RETRIGGER);
        st.filterRev   = getInt (P_FILTER_REV) >= 1 ? 2 : 1;
        st.analog      = get (P_ANALOG);
        st.mgSync      = getInt (P_MG_SYNC) >= 1;
        st.bendRange   = (float) mpc::clamp (getInt (P_BEND_RANGE), 0, 12);
        st.outputGain  = dbToGain (get (P_OUTPUT));

        fx.vocOn       = getBool (P_VOC_ON);
        fx.vocBands    = kVocBands[mpc::clamp (getInt (P_VOC_BANDS), 0, 3)];
        fx.vocInGain   = dbToGain (get (P_VOC_GAIN));
        fx.vocShift    = get (P_VOC_SHIFT);
        fx.vocQ        = get (P_VOC_Q);
        const float va = get (P_VOC_ATTACK), vr = get (P_VOC_RELEASE);
        fx.vocAttack   = (1.0f + 99.0f * va * va) * 0.001f;
        fx.vocRelease  = (10.0f + 990.0f * vr * vr) * 0.001f;
        fx.vocHiss     = get (P_VOC_HISS);
        fx.vocMix      = get (P_VOC_MIX);

        fx.dlyOn       = getBool (P_DLY_ON);
        fx.dlyBeats    = kDelayBeats[mpc::clamp (getInt (P_DLY_TIME), 0, 11)];
        fx.dlyFeedback = get (P_DLY_FB);
        fx.dlyTone     = get (P_DLY_TONE);
        fx.dlyMix      = get (P_DLY_MIX);

        fx.revOn       = getBool (P_REV_ON);
        fx.revSize     = get (P_REV_SIZE);
        fx.revDamp     = get (P_REV_DAMP);
        fx.revMix      = get (P_REV_MIX);
    }

    void snapSmoothers()
    {
        for (int k = 0; k < dh::kNumKnobs; ++k)
            smoothedKnobs_[(size_t) k] = get (paramIdxForKnob (k));
        engine_->knobs = smoothedKnobs_;
    }

    void updateReportedLatency (int os)
    {
        const double d = dh::halfbandChainDelay (os) * (IsFx ? 2.0 : 1.0);
        setLatency ((int) std::lround (d));
    }

    void registerPrograms()
    {
        if constexpr (IsFx)
        {
            // Order FX presets: Effect (Filter FX first!), Vocoder/AudioIn, Self-Playing, Init.
            std::vector<int> order;
            for (int i = 0; i < kFactoryPresetCount; ++i)
                if (kFactoryPresets[i].fxOrder >= 0) order.push_back (i);
            std::stable_sort (order.begin(), order.end(), [] (int a, int b) {
                return kFactoryPresets[a].fxOrder < kFactoryPresets[b].fxOrder;
            });
            for (int idx : order)
                addPresetProgram (kFactoryPresets[idx]);
        }
        else
        {
            // Instrument: Init (Normal Setting) at Program 0, followed by all 55 AT20V factory presets.
            for (int i = 0; i < kFactoryPresetCount; ++i)
                addPresetProgram (kFactoryPresets[i]);
        }
    }

    void addPresetProgram (const FactoryPreset& fp)
    {
        // Only store musical + patch + jack visual params (0..P_JACK_TAP_BASE-1) so setProgram never touches tap/action buttons.
        std::vector<float> vals (P_JACK_TAP_BASE, 0.0f);
        for (int i = 0; i < kPresetParamCount && i < P_JACK_TAP_BASE; ++i)
            vals[(size_t) i] = fp.values[(size_t) i];

        // Precompute exact initial visual frames for all 35 jacks for this preset!
        PatchRouter tmp;
        for (int i = 0; i < kNumInputJacks; ++i)
        {
            const int srcChoice = (int) std::lround (vals[(size_t) (P_PATCH_SRC_BASE + i)]);
            const int col       = (int) std::lround (vals[(size_t) (P_PATCH_COL_BASE + i)]);
            tmp.setInputSourceChoice (i, srcChoice, col);
        }
        for (int j = 0; j < kNumJacks; ++j)
            vals[(size_t) (P_JACK_VIS_BASE + j)] = (float) tmp.visualFrameForJack (j);

        addProgram (fp.name, std::move (vals));
    }

    void applyProgramInitialState()
    {
        setProgram (0);
        std::lock_guard<std::mutex> lk (routerMtx_);
        for (int i = 0; i < kNumInputJacks; ++i)
            patchRouter_.setInputSourceChoice (i, getInt (P_PATCH_SRC_BASE + i), getInt (P_PATCH_COL_BASE + i));
        syncPatchRouterToAudioLocked();
        syncVisualsLocked (false);
    }

    // Store parameter value directly to its atomic without re-entering parameterChanged().
    void storeParamQuiet (int idx, float plain)
    {
        if (idx < 0 || idx >= numParams()) return;
        values_[(size_t) idx]->store (params_[(size_t) idx].toNormalised (plain), std::memory_order_relaxed);
    }

    void markDirty (int idx)
    {
        if (idx >= 0 && idx < P_COUNT)
            uiDirty_[(size_t) idx].store (true, std::memory_order_release);
    }

    void bumpStatusCounter (int idx)
    {
        // Increment counter modulo 999 so MPC refreshes the Label Value display text without calling requestDisplayUpdate().
        const int next = (getInt (idx) + 1) % 999;
        storeParamQuiet (idx, (float) next);
        markDirty (idx);
    }

    void syncPatchRouterToAudio()
    {
        std::lock_guard<std::mutex> lk (routerMtx_);
        syncPatchRouterToAudioLocked();
    }

    void syncPatchRouterToAudioLocked()
    {
        const dh::PatchState ps = patchRouter_.toDspPatch();
        for (int j = 0; j < kNumJacks; ++j)
            patchAtomic_[(size_t) j].store (ps.src[(size_t) j], std::memory_order_relaxed);
    }

    void pushRouterToParamsAndAudio (bool notifyHost)
    {
        for (int i = 0; i < kNumInputJacks; ++i)
        {
            storeParamQuiet (P_PATCH_SRC_BASE + i, (float) patchRouter_.getInputSourceChoice (i));
            storeParamQuiet (P_PATCH_COL_BASE + i, (float) patchRouter_.getInputColor (i));
            if (notifyHost) { markDirty (P_PATCH_SRC_BASE + i); markDirty (P_PATCH_COL_BASE + i); }
        }
        syncPatchRouterToAudioLocked();
        syncVisualsLocked (notifyHost);
    }

    void syncVisualsToParams (bool notifyHost)
    {
        std::lock_guard<std::mutex> lk (routerMtx_);
        syncVisualsLocked (notifyHost);
    }

    void syncVisualsLocked (bool notifyHost)
    {
        for (int j = 0; j < kNumJacks; ++j)
        {
            const int frame = patchRouter_.visualFrameForJack (j);
            if (getInt (P_JACK_VIS_BASE + j) != frame)
            {
                storeParamQuiet (P_JACK_VIS_BASE + j, (float) frame);
                if (notifyHost) markDirty (P_JACK_VIS_BASE + j);
            }
        }
        if (notifyHost) bumpStatusCounter (P_PSTAT_TEXT);
    }

    bool passTapDebounce (int slot, bool curVal)
    {
        const auto nowMs = std::chrono::duration_cast<std::chrono::milliseconds> (
            std::chrono::steady_clock::now().time_since_epoch()).count();
        std::lock_guard<std::mutex> lk (tapMtx_);
        if (curVal == lastTapVal_[(size_t) slot]) return false;
        lastTapVal_[(size_t) slot] = curVal;
        if (nowMs - lastTapMs_[(size_t) slot] < 240) return false;
        lastTapMs_[(size_t) slot] = nowMs;
        return true;
    }

    // Background UI notifier thread (~30 ms cadence, 5 ms wake granularity for fast shutdown).
    void uiWorkerLoop()
    {
        int prevLedMg = -1, prevLedEg1 = -1, prevLedPeak = -1, prevLedTrig = -1, prevLedVoc = -1, prevActV = -1;
        int prevProg = -1;
        int tick = 0;

        while (! stopWorker_.load (std::memory_order_acquire))
        {
            std::this_thread::sleep_for (std::chrono::milliseconds (5));
            if (stopWorker_.load (std::memory_order_acquire)) break;
            if (++tick < 6) continue; // ~30 ms UI update interval
            tick = 0;

            if (! readyForHostNotify_.load (std::memory_order_acquire)) continue;

            // Check if host switched built-in program (updates status readout).
            const int prog = currentProgram();
            if (prog != prevProg)
            {
                prevProg = prog;
                bumpStatusCounter (P_STAT_PRESET);
                syncVisualsToParams (true);
            }

            // Publish telemetry LEDs ONLY when quantized state actually changes (0% idle UI overhead!).
            auto updateLed = [&] (int paramIdx, int val, int& prev) {
                if (val != prev)
                {
                    prev = val;
                    storeParamQuiet (paramIdx, (float) val);
                    markDirty (paramIdx);
                }
            };
            updateLed (P_LED_MG,       ledMgAtomic_.load (std::memory_order_relaxed),      prevLedMg);
            updateLed (P_LED_EG1,      ledEg1Atomic_.load (std::memory_order_relaxed),     prevLedEg1);
            updateLed (P_LED_ESP_PEAK, ledEspPeakAtomic_.load (std::memory_order_relaxed), prevLedPeak);
            updateLed (P_LED_ESP_TRIG, ledEspTrigAtomic_.load (std::memory_order_relaxed), prevLedTrig);
            updateLed (P_LED_VOC_SIG,  ledVocSigAtomic_.load (std::memory_order_relaxed),  prevLedVoc);

            const int actV = activeVoicesTelemetry_.load (std::memory_order_relaxed);
            if (actV != prevActV)
            {
                prevActV = actV;
                bumpStatusCounter (P_STAT_PRESET);
            }

            // Flush all dirty parameter updates to MPC host UI.
            for (int i = 0; i < P_COUNT; ++i)
            {
                if (uiDirty_[(size_t) i].exchange (false, std::memory_order_acq_rel))
                    notifyHostParameterChanged (i);
            }
        }
    }

    std::unique_ptr<dh::Engine> engine_;
    double currentSr_ = 44100.0;
    double freePpq_ = 0.0;
    dh::KnobValues smoothedKnobs_ {};
    std::vector<float> espMono_, outL_, outR_, selfFeedback_;
    dh::Rng extNoiseRng_ { 0xA7202026u };

    // MIDI modulation state (audio thread)
    float modWheel_ = 0.0f;
    float bendWheel_ = 0.0f;
    bool  momentaryPedal_ = false;

    // Lock-free audio patchbay state
    std::array<std::atomic<int8_t>, kNumJacks> patchAtomic_ {};

    // UI / Patchbay controller state
    std::mutex routerMtx_;
    PatchRouter patchRouter_;

    // Tap debounce table (35 jacks + 3 action buttons)
    std::mutex tapMtx_;
    std::array<int64_t, kNumJacks + 4> lastTapMs_ {};
    std::array<bool, kNumJacks + 4>    lastTapVal_ {};

    // Telemetry & background UI worker
    std::atomic<bool> readyForHostNotify_ { false };
    std::atomic<bool> stopWorker_ { false };
    std::array<std::atomic<bool>, P_COUNT> uiDirty_ {};
    std::atomic<int> lastEditedParam_ { P_LPF_CUTOFF };
    std::atomic<int> ledMgAtomic_ { 0 };
    std::atomic<int> ledEg1Atomic_ { 0 };
    std::atomic<int> ledEspPeakAtomic_ { 0 };
    std::atomic<int> ledEspTrigAtomic_ { 0 };
    std::atomic<int> ledVocSigAtomic_ { 0 };
    std::atomic<int> activeVoicesTelemetry_ { 0 };
    std::thread workerThread_;
};

} // namespace at20
