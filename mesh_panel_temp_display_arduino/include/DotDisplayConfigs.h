#pragma once

#include "DotDisplayRenderer.h"
// This file defines the DotDisplayConfig parameter presets for select mesh panels.
constexpr DotDisplayConfig kNcaseM2Config = {
    7, // dotDiameter
    24, // startX
    5, // startY
    10.5f, // xXSpacing
    0.0f, // xYSpacing
    -5.25f, // yXSpacing
    9.0f, // yYSpacing
    2, // digitCount
    'C', // unitSuffix
};