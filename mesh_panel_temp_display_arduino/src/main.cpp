#include <Arduino.h>
#include <U8g2lib.h>

#include "DotDisplayRenderer.h"
#include "DotDisplayConfigs.h"

U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0);

namespace
{
constexpr DotDisplayConfig kDisplayConfig = {
    5, // dotDiameter
    15, // startX
    5, // startY
    7.0f, // xXSpacing
    0.0f, // xYSpacing
    -4.0f, // yXSpacing
    7.0f, // yYSpacing
    3, // digitCount
    'F', // unitSuffix
};

constexpr uint16_t kDemoValuesTenths[] = {
    888,
    234,
    196,
    420,
    618,
};

constexpr uint32_t kDemoIntervalMs = 1800;
constexpr uint32_t kSerialIntervalMs = 3000;
} // namespace

DotDisplayRenderer renderer(u8g2, kNcaseM2Config);

uint32_t lastValueChangeMs = 0;
uint32_t lastSerialMs = 0;
size_t demoIndex = 0;

void setup()
{
    Serial.begin(9600);
    renderer.begin();
    lastValueChangeMs = millis();
    lastSerialMs = lastValueChangeMs;
}

void loop()
{
    const uint32_t now = millis();

    if (now - lastValueChangeMs >= kDemoIntervalMs) {
        demoIndex = (demoIndex + 1) % (sizeof(kDemoValuesTenths) / sizeof(kDemoValuesTenths[0]));
        lastValueChangeMs = now;
    }

    renderer.renderTenths(kDemoValuesTenths[demoIndex]);

    if (now - lastSerialMs >= kSerialIntervalMs) {
        Serial.print(F("Demo tenths: "));
        Serial.println(kDemoValuesTenths[demoIndex]);
        lastSerialMs = now;
    }
}
