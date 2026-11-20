// AT20 MPC — Standalone Akai MPC Instrument Entry Point
// Based on Audio Tools AT20V (GNU AGPLv3).

#include "../../../bridge/AT20Plugin.h"

using AT20MpcPlugin = at20::AT20Plugin<false>;
MPC_PLUGIN_ENTRY(AT20MpcPlugin)
