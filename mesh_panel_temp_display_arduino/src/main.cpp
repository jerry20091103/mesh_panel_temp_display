#include <Arduino.h>
#include <U8g2lib.h>

#include "DotDisplayRenderer.h"
#include "DotDisplayConfigs.h"
#include "SerialProtocol.h"

U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0);

namespace
{
DotDisplayConfig gDisplayConfig = {
    5, // dotDiameter
    20, // startX
    10, // startY
    7.0f, // xXSpacing
    0.0f, // xYSpacing
    -4.0f, // yXSpacing
    7.0f, // yYSpacing
    3, // digitCount
    'F', // unitSuffix
    false, // invertDisplay
};

constexpr uint16_t kDemoValuesTenths[] = {
    123,
    234,
    345,
    456,
    567,
    678,
    789,
    890,
};

constexpr uint32_t kDemoIntervalMs = 1800;
} // namespace

DotDisplayRenderer renderer(u8g2, gDisplayConfig);
SerialProtocol serialProtocol;

uint32_t lastValueChangeMs = 0;
size_t demoIndex = 0;

// Display state
uint16_t currentTempTenths = 0;
bool isLiveMode = false;

void applyConfigCommand(const SerialProtocol::Command &cmd)
{
    switch (cmd.type) {
    case SerialProtocol::CommandType::DOT_DIAMETER:
        gDisplayConfig.dotDiameter = static_cast<uint8_t>(constrain(lroundf(cmd.value), 0L, 255L));
        renderer.setConfig(gDisplayConfig);
        break;
    case SerialProtocol::CommandType::START_X:
        gDisplayConfig.startX = static_cast<int16_t>(constrain(lroundf(cmd.value), -32768L, 32767L));
        renderer.setConfig(gDisplayConfig);
        break;
    case SerialProtocol::CommandType::START_Y:
        gDisplayConfig.startY = static_cast<int16_t>(constrain(lroundf(cmd.value), -32768L, 32767L));
        renderer.setConfig(gDisplayConfig);
        break;
    case SerialProtocol::CommandType::X_X_SPACING:
        gDisplayConfig.xXSpacing = cmd.value;
        renderer.setConfig(gDisplayConfig);
        break;
    case SerialProtocol::CommandType::X_Y_SPACING:
        gDisplayConfig.xYSpacing = cmd.value;
        renderer.setConfig(gDisplayConfig);
        break;
    case SerialProtocol::CommandType::Y_X_SPACING:
        gDisplayConfig.yXSpacing = cmd.value;
        renderer.setConfig(gDisplayConfig);
        break;
    case SerialProtocol::CommandType::Y_Y_SPACING:
        gDisplayConfig.yYSpacing = cmd.value;
        renderer.setConfig(gDisplayConfig);
        break;
    case SerialProtocol::CommandType::DIGIT_COUNT:
        gDisplayConfig.digitCount = static_cast<uint8_t>(constrain(lroundf(cmd.value), 2L, 4L));
        renderer.setConfig(gDisplayConfig);
        break;
    case SerialProtocol::CommandType::UNIT_SUFFIX:
        if (cmd.suffix == 'C' || cmd.suffix == 'F' || cmd.suffix == '\0') {
            gDisplayConfig.unitSuffix = cmd.suffix;
            renderer.setConfig(gDisplayConfig);
        }
        break;
    case SerialProtocol::CommandType::INVERT:
        gDisplayConfig.invertDisplay = cmd.value != 0.0f;
        renderer.setConfig(gDisplayConfig);
        break;
    default:
        break;
    }
}

void setup()
{
    serialProtocol.begin();
    renderer.begin();
    lastValueChangeMs = millis();
}

void loop()
{
    const uint32_t now = millis();

    // Process incoming serial commands
    serialProtocol.update();

    // Handle new command from serial
    if (serialProtocol.hasNewCommand()) {
        const SerialProtocol::Command &cmd = serialProtocol.getLastCommand();
        const bool isValidCommand = cmd.isValid();

        if (isValidCommand && !isLiveMode) {
            isLiveMode = true;
            serialProtocol.sendStatus(F("Switched to live mode."));
        }

        if (isValidCommand) {
            if (cmd.type == SerialProtocol::CommandType::TEMP) {
                currentTempTenths = static_cast<uint16_t>(constrain(lroundf(cmd.value), 0L, 999L));
            } else {
                applyConfigCommand(cmd);
            }
            serialProtocol.sendAckOk();
        } else {
            serialProtocol.sendAckError();
        }

        serialProtocol.clearNewCommand();
    }

    uint16_t displayValue;
    if (isLiveMode) {
        displayValue = currentTempTenths;
    } else {
        // Demo mode: cycle through preset values
        if (now - lastValueChangeMs >= kDemoIntervalMs) {
            demoIndex = (demoIndex + 1) % (sizeof(kDemoValuesTenths) / sizeof(kDemoValuesTenths[0]));
            lastValueChangeMs = now;
        }
        displayValue = kDemoValuesTenths[demoIndex];
    }

    renderer.renderTenths(displayValue);
}
