#include "DotDisplayRenderer.h"

#include <math.h>

namespace
{
// 3-column x 5-row digit bitmaps (each row uses 3 bits)
constexpr uint8_t kDigitBitmaps[10][5] = {
    {0b111, 0b101, 0b101, 0b101, 0b111},  // 0
    {0b010, 0b010, 0b010, 0b010, 0b010},  // 1
    {0b111, 0b001, 0b111, 0b100, 0b111},  // 2
    {0b111, 0b001, 0b111, 0b001, 0b111},  // 3
    {0b101, 0b101, 0b111, 0b001, 0b001},  // 4
    {0b111, 0b100, 0b111, 0b001, 0b111},  // 5
    {0b111, 0b100, 0b111, 0b101, 0b111},  // 6
    {0b111, 0b001, 0b010, 0b010, 0b010},  // 7
    {0b111, 0b101, 0b111, 0b101, 0b111},  // 8
    {0b111, 0b101, 0b111, 0b001, 0b111},  // 9
};

constexpr uint8_t kSuffixBitmaps[2][5] = {
    {0b000, 0b111, 0b100, 0b100, 0b111},  // C
    {0b000, 0b111, 0b100, 0b111, 0b100},  // F
};
}

DotDisplayRenderer::DotDisplayRenderer(U8G2 &display, const DotDisplayConfig &config)
    : display_(display), config_(config)
{
}

void DotDisplayRenderer::begin()
{
    display_.begin();
    display_.setContrast(255);
    display_.setDrawColor(1);
}

void DotDisplayRenderer::renderTenths(uint16_t tenths)
{
    display_.clearBuffer();
    display_.setDrawColor(1);

    uint8_t digitCount = config_.digitCount;
    if (digitCount < 2) {
        digitCount = 3;
    } else if (digitCount > 4) {
        digitCount = 4;
    }

    const bool showSuffix = config_.unitSuffix == 'C' || config_.unitSuffix == 'F';
    const float baseX = static_cast<float>(config_.startX);
    const float baseY = static_cast<float>(config_.startY);

    auto drawDigitSlot = [&](uint8_t slotIndex, uint8_t digit) {
        drawDigit(digit, glyphOriginX(baseX, slotIndex), glyphOriginY(baseY, slotIndex));
    };

    auto drawBlankSlot = [&](uint8_t slotIndex) {
        drawBlankDigit(glyphOriginX(baseX, slotIndex), glyphOriginY(baseY, slotIndex));
    };

    auto drawSuffixSlot = [&](uint8_t slotIndex) {
        drawSuffix(config_.unitSuffix, glyphOriginX(baseX, slotIndex), glyphOriginY(baseY, slotIndex));
    };

    const uint16_t whole = tenths / 10;
    const uint8_t decimal = tenths % 10;

    if (digitCount == 2) {
        const uint16_t clampedWhole = (whole > 99) ? 99 : whole;
        const uint8_t tens = clampedWhole / 10;
        const uint8_t ones = clampedWhole % 10;

        if (clampedWhole < 10) {
            drawBlankSlot(0);
        } else {
            drawDigitSlot(0, tens);
        }

        drawDigitSlot(1, ones);

        if (showSuffix) {
            drawSuffixSlot(2);
        }
    } else if (digitCount == 3) {
        if (whole >= 100) {
            const uint16_t clampedWhole = (whole > 999) ? 999 : whole;
            drawDigitSlot(0, clampedWhole / 100);
            drawDigitSlot(1, (clampedWhole / 10) % 10);
            drawDigitSlot(2, clampedWhole % 10);
        } else {
            if (whole < 10) {
                drawBlankSlot(0);
            } else {
                drawDigitSlot(0, whole / 10);
            }

            drawDigitSlot(1, whole % 10);
            drawDecimalPoint(glyphOriginX(baseX, 1), glyphOriginY(baseY, 1));
            drawDigitSlot(2, decimal);
        }

        if (showSuffix) {
            drawSuffixSlot(3);
        }
    } else {
        if (whole >= 1000) {
            const uint16_t clampedWhole = (whole > 9999) ? 9999 : whole;
            drawDigitSlot(0, (clampedWhole / 1000) % 10);
            drawDigitSlot(1, (clampedWhole / 100) % 10);
            drawDigitSlot(2, (clampedWhole / 10) % 10);
            drawDigitSlot(3, clampedWhole % 10);
        } else {
            if (whole < 100) {
                drawBlankSlot(0);
            } else {
                drawDigitSlot(0, whole / 100);
            }

            if (whole < 10) {
                drawBlankSlot(1);
            } else {
                drawDigitSlot(1, (whole / 10) % 10);
            }

            drawDigitSlot(2, whole % 10);
            drawDecimalPoint(glyphOriginX(baseX, 2), glyphOriginY(baseY, 2));
            drawDigitSlot(3, decimal);
        }

        if (showSuffix) {
            drawSuffixSlot(4);
        }
    }

    display_.sendBuffer();
}

void DotDisplayRenderer::drawDigit(uint8_t digit, float originX, float originY)
{
    drawPattern(kDigitBitmaps[digit], kDigitRows, originX, originY);
}

void DotDisplayRenderer::drawBlankDigit(float originX, float originY)
{
    (void)originX;
    (void)originY;
}

void DotDisplayRenderer::drawSuffix(char suffix, float originX, float originY)
{
    switch (suffix) {
    case 'C':
        drawPattern(kSuffixBitmaps[0], kDigitRows, originX, originY);
        break;
    case 'F':
        drawPattern(kSuffixBitmaps[1], kDigitRows, originX, originY);
        break;
    default:
        break;
    }
}

void DotDisplayRenderer::drawDecimalPoint(float originX, float originY)
{
    const uint8_t radius = config_.dotDiameter / 2;
    drawCell(originX, originY, 3, 4, radius);
}

void DotDisplayRenderer::drawCell(float originX, float originY, uint8_t column, uint8_t row, uint8_t radius)
{
    const float x = originX + (static_cast<float>(column) * config_.xXSpacing) + (static_cast<float>(row) * config_.yXSpacing);
    const float y = originY + (static_cast<float>(column) * config_.xYSpacing) + (static_cast<float>(row) * config_.yYSpacing);
    display_.drawDisc(static_cast<int16_t>(lroundf(x)), static_cast<int16_t>(lroundf(y)), radius, U8G2_DRAW_ALL);
}

void DotDisplayRenderer::drawPattern(const uint8_t *patternRows, uint8_t rowCount, float originX, float originY)
{
    const uint8_t radius = config_.dotDiameter / 2;

    for (uint8_t row = 0; row < rowCount; ++row) {
        const uint8_t pattern = patternRows[row];

        for (uint8_t column = 0; column < kDigitColumns; ++column) {
            const uint8_t mask = 1U << (kDigitColumns - 1 - column);
            if (pattern & mask) {
                drawCell(originX, originY, column, row, radius);
            }
        }
    }
}

float DotDisplayRenderer::glyphOriginX(float baseX, uint8_t glyphIndex) const
{
    return baseX + (glyphIndex * kGlyphAdvanceColumns * config_.xXSpacing);
}

float DotDisplayRenderer::glyphOriginY(float baseY, uint8_t glyphIndex) const
{
    // the start Y position is the same for all digits (digits are horizontally aligned), so glyphIndex is not used here
    return baseY;
}