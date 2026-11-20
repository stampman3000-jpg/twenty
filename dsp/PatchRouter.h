#pragma once
// AT20 MPC — 35-Jack MS-20 Patchbay Routing Controller
// Manages all 15 inputs & 20 outputs, normalled defaults, cable colours (6 AT20V colours),
// numbered route badges, multi-out fan-out, single-in rules, and the interactive tap-to-patch FSM.
// Pure C++17, zero JUCE dependencies.

#include "Engine.h"
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>

namespace at20 {

constexpr int kNumJacks       = dh::kNumJacks; // 35
constexpr int kNumInputJacks  = 15;
constexpr int kNumOutputJacks = 20;
constexpr int kNumCableColors = 6;
constexpr int kNumRouteSlots  = 12; // 2 cycles of 6 colors (1..9, A, B, C)

// Visual filmstrip frame indices for each jack (28 frames total).
enum JackVisualFrame : int
{
    kFrameEmpty            = 0,  // Unconnected chrome 1/4" socket
    kFrameSelectedEmpty    = 1,  // Selected unconnected jack (gold ring)
    kFrameTargetHighlight  = 2,  // Compatible destination/source highlight
    kFramePlugBase         = 3,  // 3..14: Connected plug for route slot 0..11
    kFramePlugSelectedBase = 15, // 15..26: Selected connected plug for route slot 0..11
    kFramePlugTargetHint   = 27, // Connected jack highlighted as replaceable target
    kNumJackFrames         = 28
};

// Exact AT20V cable color order matching upstream PanelView.cpp.
enum CableColor : int
{
    kColorRed    = 0,
    kColorBlue   = 1,
    kColorYellow = 2,
    kColorGreen  = 3,
    kColorWhite  = 4,
    kColorBlack  = 5
};

inline constexpr const char* kCableColorNames[kNumCableColors] = {
    "red", "blue", "yellow", "green", "white", "black"
};

inline constexpr const char* kCableColorShort[kNumCableColors] = {
    "RED", "BLU", "YEL", "GRN", "WHT", "BLK"
};

inline constexpr char kRouteSlotChar[kNumRouteSlots] = {
    '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C'
};

// Input jack index (0..14) -> dh::JackId (0..34)
inline constexpr int kInputJackIds[kNumInputJacks] = {
    (int) dh::JackId::total_in,
    (int) dh::JackId::freq_in,
    (int) dh::JackId::ext_sig_in,
    (int) dh::JackId::hpf_cut_in,
    (int) dh::JackId::lpf_cut_in,
    (int) dh::JackId::gain_in,
    (int) dh::JackId::vco2_cv_in,
    (int) dh::JackId::vco12_cv_in,
    (int) dh::JackId::sh_clock_in,
    (int) dh::JackId::vca_ctrl_in,
    (int) dh::JackId::eg1_trig_in,
    (int) dh::JackId::kbd_trig_in,
    (int) dh::JackId::sh_in,
    (int) dh::JackId::vca_in,
    (int) dh::JackId::esp_in,
};

// Output jack index (0..19) -> dh::JackId (0..34)
inline constexpr int kOutputJackIds[kNumOutputJacks] = {
    (int) dh::JackId::signal_out,
    (int) dh::JackId::phones_out,
    (int) dh::JackId::mg_tri_out,
    (int) dh::JackId::mg_sq_out,
    (int) dh::JackId::eg1_out,
    (int) dh::JackId::eg2_rev_out,
    (int) dh::JackId::kbd_cv_out,
    (int) dh::JackId::eg1_rev_out,
    (int) dh::JackId::kbd_trig_out,
    (int) dh::JackId::sh_out,
    (int) dh::JackId::vca_out,
    (int) dh::JackId::pink_out,
    (int) dh::JackId::white_out,
    (int) dh::JackId::wheel_out,
    (int) dh::JackId::msw_out,
    (int) dh::JackId::esp_amp_out,
    (int) dh::JackId::esp_bpf_out,
    (int) dh::JackId::esp_fv_out,
    (int) dh::JackId::esp_env_out,
    (int) dh::JackId::esp_trig_out,
};

struct JackMeta
{
    const char* shortName;   // Short screen label (<= 10 chars)
    const char* normalDesc;  // Normalled default description (inputs only)
};

inline const JackMeta& jackMeta (int jackId)
{
    static const JackMeta meta[kNumJacks] = {
        { "TOTAL",    "MG TRI" },      // 0  total_in
        { "FREQ",     "EG1" },         // 1  freq_in
        { "EXT SIG",  "NONE" },        // 2  ext_sig_in
        { "HPF CUT",  "EG2" },         // 3  hpf_cut_in
        { "LPF CUT",  "EG2" },         // 4  lpf_cut_in
        { "INIT GN",  "NONE" },        // 5  gain_in
        { "SIG OUT",  "" },            // 6  signal_out
        { "PHONES",   "" },            // 7  phones_out
        { "MG TRI",   "" },            // 8  mg_tri_out
        { "MG SQ",    "" },            // 9  mg_sq_out
        { "EG1 OUT",  "" },            // 10 eg1_out
        { "EG2 REV",  "" },            // 11 eg2_rev_out
        { "VCO2 CV",  "VCO1+2" },      // 12 vco2_cv_in
        { "VCO12 CV", "KBD CV" },      // 13 vco12_cv_in
        { "KBD CV",   "" },            // 14 kbd_cv_out
        { "S/H CLK",  "NONE" },        // 15 sh_clock_in
        { "EG1 REV",  "" },            // 16 eg1_rev_out
        { "MVCA CTL", "EG1" },         // 17 vca_ctrl_in
        { "EG1 TRG",  "KBD TRG" },     // 18 eg1_trig_in
        { "KBD TRG",  "KEY GATE" },    // 19 kbd_trig_in
        { "TRG OUT",  "" },            // 20 kbd_trig_out
        { "S/H IN",   "NONE" },        // 21 sh_in
        { "S/H OUT",  "" },            // 22 sh_out
        { "MVCA IN",  "NONE" },        // 23 vca_in
        { "MVCA OUT", "" },            // 24 vca_out
        { "PINK",     "" },            // 25 pink_out
        { "WHITE",    "" },            // 26 white_out
        { "WHEEL",    "" },            // 27 wheel_out
        { "MOM SW",   "" },            // 28 msw_out
        { "ESP IN",   "AUDIO IN" },    // 29 esp_in
        { "ESP AMP",  "" },            // 30 esp_amp_out
        { "ESP BPF",  "" },            // 31 esp_bpf_out
        { "ESP F-V",  "" },            // 32 esp_fv_out
        { "ESP ENV",  "" },            // 33 esp_env_out
        { "ESP TRG",  "" },            // 34 esp_trig_out
    };
    if (jackId < 0 || jackId >= kNumJacks) return meta[0];
    return meta[jackId];
}

inline bool isOutputJack (int jackId)
{
    return jackId >= 0 && jackId < kNumJacks && dh::layout::jacks[jackId].isOutput;
}

inline int jackToInputSlot (int jackId)
{
    for (int i = 0; i < kNumInputJacks; ++i)
        if (kInputJackIds[i] == jackId) return i;
    return -1;
}

inline int jackToOutputSlot (int jackId)
{
    for (int i = 0; i < kNumOutputJacks; ++i)
        if (kOutputJackIds[i] == jackId) return i;
    return -1;
}

inline int colorIndexFromName (const char* name)
{
    if (! name) return kColorRed;
    for (int i = 0; i < kNumCableColors; ++i)
        if (std::strcmp (name, kCableColorNames[i]) == 0) return i;
    return kColorRed;
}

// Complete patchbay routing controller.
class PatchRouter
{
public:
    PatchRouter() { clearAll(); }

    void clearAll()
    {
        inputSrcOutSlot.fill (-1);
        inputColor.fill (kColorRed);
        selectedJack = -1;
        nextColor = 0;
        recomputeSlots();
        updateStatusText();
    }

    // Set input slot (0..14) to output choice (0 = normalled/off, 1..20 = output slot + 1).
    void setInputSourceChoice (int inSlot, int outChoice, int explicitColor = -1)
    {
        if (inSlot < 0 || inSlot >= kNumInputJacks) return;
        if (outChoice <= 0 || outChoice > kNumOutputJacks)
        {
            inputSrcOutSlot[(size_t) inSlot] = -1;
        }
        else
        {
            const int outSlot = outChoice - 1;
            inputSrcOutSlot[(size_t) inSlot] = (int8_t) outSlot;
            if (explicitColor >= 0 && explicitColor < kNumCableColors)
            {
                inputColor[(size_t) inSlot] = (int8_t) explicitColor;
            }
            else
            {
                // If this output already feeds another input, share its color so fan-out groups visually.
                int sharedCol = -1;
                for (int i = 0; i < kNumInputJacks; ++i)
                {
                    if (i != inSlot && inputSrcOutSlot[(size_t) i] == outSlot)
                    {
                        sharedCol = inputColor[(size_t) i];
                        break;
                    }
                }
                if (sharedCol >= 0)
                    inputColor[(size_t) inSlot] = (int8_t) sharedCol;
                else
                {
                    inputColor[(size_t) inSlot] = (int8_t) (nextColor % 5); // cycle red..white like AT20V UI
                    nextColor = (nextColor + 1) % 5;
                }
            }
        }
        recomputeSlots();
        updateStatusText();
    }

    void setInputColor (int inSlot, int colorIdx)
    {
        if (inSlot < 0 || inSlot >= kNumInputJacks) return;
        inputColor[(size_t) inSlot] = (int8_t) (colorIdx >= 0 ? (colorIdx % kNumCableColors) : 0);
        recomputeSlots();
        updateStatusText();
    }

    int getInputSourceChoice (int inSlot) const
    {
        if (inSlot < 0 || inSlot >= kNumInputJacks) return 0;
        const int s = inputSrcOutSlot[(size_t) inSlot];
        return s < 0 ? 0 : (s + 1);
    }

    int getInputColor (int inSlot) const
    {
        if (inSlot < 0 || inSlot >= kNumInputJacks) return 0;
        return inputColor[(size_t) inSlot];
    }

    // Export current routing to dh::PatchState for the DSP engine.
    dh::PatchState toDspPatch() const
    {
        dh::PatchState ps;
        for (int i = 0; i < kNumInputJacks; ++i)
        {
            const int outSlot = inputSrcOutSlot[(size_t) i];
            if (outSlot >= 0 && outSlot < kNumOutputJacks)
                ps.src[(size_t) kInputJackIds[i]] = (int8_t) kOutputJackIds[outSlot];
        }
        return ps;
    }

    int cableCount() const
    {
        int n = 0;
        for (int i = 0; i < kNumInputJacks; ++i)
            if (inputSrcOutSlot[(size_t) i] >= 0) ++n;
        return n;
    }

    int getSelectedJack() const { return selectedJack; }
    void clearSelection() { selectedJack = -1; updateStatusText(); }

    // Interactive touch-patching state machine.
    // Returns true if any patch connection changed (not just selection).
    struct TapResult
    {
        bool routingChanged = false;
        int  changedInSlot  = -1; // 0..14 if a single input slot changed
    };

    TapResult onJackTapped (int jackId)
    {
        TapResult res;
        if (jackId < 0 || jackId >= kNumJacks) return res;

        const bool tappedOut = isOutputJack (jackId);

        if (selectedJack < 0)
        {
            selectedJack = jackId;
            updateStatusText();
            return res;
        }

        if (selectedJack == jackId)
        {
            // Tapping the already-selected jack:
            // - If it's a connected input jack, disconnect it!
            // - Otherwise deselect.
            if (! tappedOut)
            {
                const int inSlot = jackToInputSlot (jackId);
                if (inSlot >= 0 && inputSrcOutSlot[(size_t) inSlot] >= 0)
                {
                    inputSrcOutSlot[(size_t) inSlot] = -1;
                    res.routingChanged = true;
                    res.changedInSlot = inSlot;
                }
            }
            selectedJack = -1;
            recomputeSlots();
            updateStatusText();
            return res;
        }

        const bool selOut = isOutputJack (selectedJack);
        if (selOut == tappedOut)
        {
            // Same direction -> switch selection to the newly tapped jack.
            selectedJack = jackId;
            updateStatusText();
            return res;
        }

        // Opposite directions -> make or toggle connection!
        const int outJack = selOut ? selectedJack : jackId;
        const int inJack  = selOut ? jackId : selectedJack;
        const int outSlot = jackToOutputSlot (outJack);
        const int inSlot  = jackToInputSlot (inJack);
        if (outSlot >= 0 && inSlot >= 0)
        {
            if (inputSrcOutSlot[(size_t) inSlot] == outSlot)
            {
                // Tapping existing pair disconnects it.
                inputSrcOutSlot[(size_t) inSlot] = -1;
            }
            else
            {
                setInputSourceChoice (inSlot, outSlot + 1, -1);
            }
            res.routingChanged = true;
            res.changedInSlot = inSlot;
        }
        selectedJack = -1;
        recomputeSlots();
        updateStatusText();
        return res;
    }

    // Disconnects currently selected jack (all outgoing if output, or its cable if input),
    // or falls back to disconnecting fallbackInSlot if nothing is selected.
    bool disconnectSelectedOr (int fallbackInSlot)
    {
        bool changed = false;
        if (selectedJack >= 0)
        {
            if (isOutputJack (selectedJack))
            {
                const int outSlot = jackToOutputSlot (selectedJack);
                for (int i = 0; i < kNumInputJacks; ++i)
                    if (inputSrcOutSlot[(size_t) i] == outSlot) { inputSrcOutSlot[(size_t) i] = -1; changed = true; }
            }
            else
            {
                const int inSlot = jackToInputSlot (selectedJack);
                if (inSlot >= 0 && inputSrcOutSlot[(size_t) inSlot] >= 0) { inputSrcOutSlot[(size_t) inSlot] = -1; changed = true; }
            }
            selectedJack = -1;
        }
        else if (fallbackInSlot >= 0 && fallbackInSlot < kNumInputJacks && inputSrcOutSlot[(size_t) fallbackInSlot] >= 0)
        {
            inputSrcOutSlot[(size_t) fallbackInSlot] = -1;
            changed = true;
        }
        if (changed) recomputeSlots();
        updateStatusText();
        return changed;
    }

    // Compute the visual filmstrip frame (0..27) for every one of the 35 jacks.
    int visualFrameForJack (int jackId) const
    {
        if (jackId < 0 || jackId >= kNumJacks) return kFrameEmpty;

        const int slot = jackRouteSlot[(size_t) jackId]; // -1 if unconnected, else 0..11
        const bool isSel = (selectedJack == jackId);
        const bool isOut = isOutputJack (jackId);
        const bool compatibleTarget = (selectedJack >= 0) && (isOutputJack (selectedJack) != isOut);

        if (isSel)
            return (slot >= 0) ? (kFramePlugSelectedBase + slot) : kFrameSelectedEmpty;

        if (compatibleTarget)
            return (slot >= 0) ? kFramePlugTargetHint : kFrameTargetHighlight;

        if (slot >= 0)
            return kFramePlugBase + slot;

        return kFrameEmpty;
    }

    const std::string& statusLine() const { return statusStr; }

    // Binary extra-state serialization (version 1): 15 pairs of (int8 srcOutSlot, int8 color).
    void serialize (std::vector<uint8_t>& out) const
    {
        out.push_back (1); // version
        for (int i = 0; i < kNumInputJacks; ++i)
        {
            out.push_back ((uint8_t) inputSrcOutSlot[(size_t) i]);
            out.push_back ((uint8_t) inputColor[(size_t) i]);
        }
    }

    bool deserialize (const uint8_t* data, size_t size)
    {
        if (! data || size < 1 + (size_t) kNumInputJacks * 2) return false;
        if (data[0] != 1) return false;
        size_t pos = 1;
        for (int i = 0; i < kNumInputJacks; ++i)
        {
            int8_t s = (int8_t) data[pos++];
            int8_t c = (int8_t) data[pos++];
            if (s < -1 || s >= kNumOutputJacks) s = -1;
            if (c < 0 || c >= kNumCableColors) c = 0;
            inputSrcOutSlot[(size_t) i] = s;
            inputColor[(size_t) i] = c;
        }
        selectedJack = -1;
        recomputeSlots();
        updateStatusText();
        return true;
    }

private:
    // Assign deterministic numbered route slots (0..11) grouped by output jack & honoring cable color.
    void recomputeSlots()
    {
        jackRouteSlot.fill (-1);
        std::array<bool, kNumRouteSlots> usedSlot {};
        std::array<int8_t, kNumOutputJacks> outAssignedSlot;
        outAssignedSlot.fill (-1);

        for (int i = 0; i < kNumInputJacks; ++i)
        {
            const int outSlot = inputSrcOutSlot[(size_t) i];
            if (outSlot < 0 || outSlot >= kNumOutputJacks) continue;

            int rSlot = outAssignedSlot[(size_t) outSlot];
            if (rSlot < 0)
            {
                const int col = inputColor[(size_t) i] % kNumCableColors;
                // Prefer slot `col`, then `col + 6`, then any unused slot.
                if (! usedSlot[(size_t) col]) rSlot = col;
                else if (! usedSlot[(size_t) (col + kNumCableColors)]) rSlot = col + kNumCableColors;
                else
                {
                    rSlot = col;
                    for (int s = 0; s < kNumRouteSlots; ++s)
                        if (! usedSlot[(size_t) s]) { rSlot = s; break; }
                }
                usedSlot[(size_t) rSlot] = true;
                outAssignedSlot[(size_t) outSlot] = (int8_t) rSlot;
                jackRouteSlot[(size_t) kOutputJackIds[outSlot]] = (int8_t) rSlot;
            }
            jackRouteSlot[(size_t) kInputJackIds[i]] = (int8_t) rSlot;
        }
    }

    void updateStatusText()
    {
        char buf[64];
        if (selectedJack >= 0)
        {
            const char* name = jackMeta (selectedJack).shortName;
            if (isOutputJack (selectedJack))
            {
                const int outSlot = jackToOutputSlot (selectedJack);
                int cnt = 0, firstIn = -1;
                for (int i = 0; i < kNumInputJacks; ++i)
                    if (inputSrcOutSlot[(size_t) i] == outSlot) { if (firstIn < 0) firstIn = kInputJackIds[i]; ++cnt; }
                if (cnt == 0)
                    std::snprintf (buf, sizeof (buf), "%s -> TAP IN", name);
                else if (cnt == 1)
                    std::snprintf (buf, sizeof (buf), "%s>%s", name, jackMeta (firstIn).shortName);
                else
                    std::snprintf (buf, sizeof (buf), "%s -> %d INS", name, cnt);
            }
            else
            {
                const int inSlot = jackToInputSlot (selectedJack);
                const int outSlot = inSlot >= 0 ? inputSrcOutSlot[(size_t) inSlot] : -1;
                if (outSlot >= 0)
                {
                    const int rs = jackRouteSlot[(size_t) selectedJack];
                    const char ch = (rs >= 0 && rs < kNumRouteSlots) ? kRouteSlotChar[rs] : '*';
                    std::snprintf (buf, sizeof (buf), "[%c] %s>%s", ch, jackMeta (kOutputJackIds[outSlot]).shortName, name);
                }
                else
                {
                    std::snprintf (buf, sizeof (buf), "%s (NORM:%s)", name, jackMeta (selectedJack).normalDesc);
                }
            }
            statusStr = buf;
            return;
        }

        const int c = cableCount();
        if (c == 0)
            statusStr = "NORMALLED (0)";
        else if (c == 1)
        {
            for (int i = 0; i < kNumInputJacks; ++i)
                if (inputSrcOutSlot[(size_t) i] >= 0)
                {
                    const int rs = jackRouteSlot[(size_t) kInputJackIds[i]];
                    const char ch = (rs >= 0 && rs < kNumRouteSlots) ? kRouteSlotChar[rs] : '1';
                    std::snprintf (buf, sizeof (buf), "[%c] %s>%s", ch,
                                   jackMeta (kOutputJackIds[inputSrcOutSlot[(size_t) i]]).shortName,
                                   jackMeta (kInputJackIds[i]).shortName);
                    statusStr = buf;
                    return;
                }
        }
        else
        {
            std::snprintf (buf, sizeof (buf), "%d CABLES ACTIVE", c);
            statusStr = buf;
        }
    }

    std::array<int8_t, kNumInputJacks> inputSrcOutSlot {};
    std::array<int8_t, kNumInputJacks> inputColor {};
    std::array<int8_t, kNumJacks>      jackRouteSlot {};
    int selectedJack = -1;
    int nextColor = 0;
    std::string statusStr = "NORMALLED (0)";
};

} // namespace at20
