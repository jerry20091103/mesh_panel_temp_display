#pragma once

#include <Arduino.h>
#include <U8g2lib.h>

struct DotDisplayConfig
{
    uint8_t dotDiameter;
    int16_t startX;
    int16_t startY;
    float xXSpacing;
    float xYSpacing;
    float yXSpacing;
    float yYSpacing;
    uint8_t digitCount;
    char unitSuffix;
    bool invertDisplay;
};

class DotDisplayRenderer
{
public:
    /// Constructor initializes the renderer with a display instance and layout configuration.
    /// @param display Reference to the U8G2 display object
    /// @param config Display configuration with dot size and spacing parameters
    DotDisplayRenderer(U8G2 &display, const DotDisplayConfig &config);

    /// Replace the active display configuration.
    void setConfig(const DotDisplayConfig &config);

    /// Initialize the display and prepare for rendering.
    /// Should be called once in setup() after creating the renderer instance.
    void begin();

    /// Render a temperature value in tenths format (XX.X format).
    /// For values < 100, leading digit is blank; for values >= 100, all three digits are shown.
    /// Automatically clamps values > 999 to 999.
    /// @param tenths The value to display in tenths (e.g., 235 = 23.5 degrees)
    void renderTenths(uint16_t tenths);

private:
    static constexpr uint8_t kDigitColumns = 3;   ///< Width of each digit in columns
    static constexpr uint8_t kDigitRows = 5;      ///< Height of each digit in rows
    static constexpr uint8_t kGlyphAdvanceColumns = 4; ///< Horizontal spacing between digits in columns

    U8G2 &display_;           ///< Reference to the display object
    DotDisplayConfig config_; ///< Display layout configuration (spacing, dot size, etc.)

    /// Draw a single digit (0-9) at the specified origin position.
    /// Uses the kDigitBitmaps lookup table to determine which dots to draw.
    void drawDigit(uint8_t digit, float originX, float originY);

    /// Draw a blank digit (no dots). Reserved for future use.
    void drawBlankDigit(float originX, float originY);

    /// Draw the configured unit suffix after the last digit, if enabled.
    /// Supported suffixes are C and F.
    void drawSuffix(char suffix, float originX, float originY);

    /// Draw the decimal point for the middle digit position.
    void drawDecimalPoint(float originX, float originY);

    /// Draw a single dot at the specified grid position.
    /// @param originX Top-left X coordinate of the digit
    /// @param originY Top-left Y coordinate of the digit
    /// @param column Horizontal grid position (0-2)
    /// @param row Vertical grid position (0-4)
    /// @param radius Dot radius in pixels
    void drawCell(float originX, float originY, uint8_t column, uint8_t row, uint8_t radius);

    /// Calculate the X coordinate for a digit's top-left corner given its index.
    /// @param baseX Starting X position of the first digit
    /// @param glyphIndex Position of the digit (0 = first, 1 = second, 2 = third)
    /// @return Calculated X coordinate accounting for spacing
    float glyphOriginX(float baseX, uint8_t glyphIndex) const;

    /// Calculate the Y coordinate for a digit's top-left corner given its index.
    /// @param baseY Starting Y position of the first digit
    /// @param glyphIndex Position of the digit (0 = first, 1 = second, 2 = third)
    /// @return Calculated Y coordinate accounting for spacing
    float glyphOriginY(float baseY, uint8_t glyphIndex) const;

    /// Draw a 3x5 glyph pattern using the configured dot spacing.
    void drawPattern(const uint8_t *patternRows, uint8_t rowCount, float originX, float originY);
};