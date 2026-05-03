#include "SerialProtocol.h"

#include <stdlib.h>
#include <string.h>

namespace
{
void trimInPlace(char *text)
{
    if (text == nullptr) {
        return;
    }

    char *start = text;
    while (*start != '\0' && isspace(static_cast<unsigned char>(*start))) {
        ++start;
    }

    if (start != text) {
        memmove(text, start, strlen(start) + 1);
    }

    size_t length = strlen(text);
    while (length > 0 && isspace(static_cast<unsigned char>(text[length - 1]))) {
        text[length - 1] = '\0';
        --length;
    }
}

bool parseFloatValue(const char *text, float &value)
{
    if (text == nullptr || *text == '\0') {
        return false;
    }

    bool hasDigit = false;
    bool hasDot = false;

    for (const char *cursor = text; *cursor != '\0'; ++cursor) {
        const char ch = *cursor;
        if (cursor == text && (ch == '+' || ch == '-')) {
            continue;
        }

        if (ch == '.') {
            if (hasDot) {
                return false;
            }
            hasDot = true;
            continue;
        }

        if (isDigit(ch)) {
            hasDigit = true;
            continue;
        }

        return false;
    }

    if (!hasDigit) {
        return false;
    }

    value = static_cast<float>(atof(text));
    return true;
}

bool parseCharValue(const char *text, char &value)
{
    if (text == nullptr || *text == '\0') {
        value = '\0';
        return true;
    }

    if (text[1] != '\0') {
        return false;
    }

    const char ch = text[0];
    if (ch == 'C' || ch == 'c') {
        value = 'C';
        return true;
    }

    if (ch == 'F' || ch == 'f') {
        value = 'F';
        return true;
    }

    return false;
}
} // namespace

SerialProtocol::SerialProtocol()
    : lastCommand_(), hasNewCommand_(false), lastDebugLogMs_(0)
{
}

void SerialProtocol::begin()
{
    Serial.begin(9600);
    Serial.setTimeout(10);
    lastDebugLogMs_ = millis();
    sendStatus(F("Temperature display initialized. Send TEMP:XXX or config commands."));
}

void SerialProtocol::update()
{
    if (Serial.available()) {
        char line[kSerialLineMaxLength];
        size_t length = Serial.readBytesUntil('\n', line, sizeof(line) - 1);
        line[length] = '\0';
        trimInPlace(line);

        lastCommand_ = parseLine(line);
        hasNewCommand_ = true;
    }
}

void SerialProtocol::clearNewCommand()
{
    hasNewCommand_ = false;
}

bool SerialProtocol::hasNewCommand() const
{
    return hasNewCommand_;
}

const SerialProtocol::Command &SerialProtocol::getLastCommand() const
{
    return lastCommand_;
}

void SerialProtocol::sendStatus(const __FlashStringHelper *status) const
{
    Serial.println(status);
}

void SerialProtocol::sendDebug(const __FlashStringHelper *label, const char *value) const
{
#if DEBUG_SERIAL
    Serial.print(F("[DEBUG] "));
    Serial.print(label);
    Serial.print(F(": "));
    Serial.println(value);
#else
    (void)label;
    (void)value;
#endif
}

void SerialProtocol::sendAckOk() const
{
    Serial.println(F("ACK:OK"));
}

void SerialProtocol::sendAckError() const
{
    Serial.println(F("ACK:ERROR"));
}

SerialProtocol::Command SerialProtocol::parseLine(const char *line)
{
    if (line == nullptr || line[0] == '\0') {
        return Command(CommandType::INVALID, 0.0f);
    }

    if (strncmp(line, "TEMP:", 5) == 0) {
        const char *valueStr = line + 5;
        float value = 0.0f;
        if (!parseFloatValue(valueStr, value)) {
            sendDebug(F("Invalid TEMP command"), valueStr);
            return Command(CommandType::INVALID, 0.0f);
        }

        sendDebug(F("Parsed TEMP command"), valueStr);
        return Command(CommandType::TEMP, value);
    }

    if (strncmp(line, "DOTDIAMETER:", 12) == 0) {
        const char *valueStr = line + 12;
        float value = 0.0f;
        if (!parseFloatValue(valueStr, value)) {
            sendDebug(F("Invalid DOTDIAMETER command"), valueStr);
            return Command(CommandType::INVALID, 0.0f);
        }

        sendDebug(F("Parsed DOTDIAMETER command"), valueStr);
        return Command(CommandType::DOT_DIAMETER, value);
    }

    if (strncmp(line, "STARTX:", 7) == 0) {
        const char *valueStr = line + 7;
        float value = 0.0f;
        if (!parseFloatValue(valueStr, value)) {
            sendDebug(F("Invalid STARTX command"), valueStr);
            return Command(CommandType::INVALID, 0.0f);
        }

        sendDebug(F("Parsed STARTX command"), valueStr);
        return Command(CommandType::START_X, value);
    }

    if (strncmp(line, "STARTY:", 7) == 0) {
        const char *valueStr = line + 7;
        float value = 0.0f;
        if (!parseFloatValue(valueStr, value)) {
            sendDebug(F("Invalid STARTY command"), valueStr);
            return Command(CommandType::INVALID, 0.0f);
        }

        sendDebug(F("Parsed STARTY command"), valueStr);
        return Command(CommandType::START_Y, value);
    }

    if (strncmp(line, "XXSPACING:", 10) == 0) {
        const char *valueStr = line + 10;
        float value = 0.0f;
        if (!parseFloatValue(valueStr, value)) {
            sendDebug(F("Invalid XXSPACING command"), valueStr);
            return Command(CommandType::INVALID, 0.0f);
        }

        sendDebug(F("Parsed XXSPACING command"), valueStr);
        return Command(CommandType::X_X_SPACING, value);
    }

    if (strncmp(line, "XYSPACING:", 10) == 0) {
        const char *valueStr = line + 10;
        float value = 0.0f;
        if (!parseFloatValue(valueStr, value)) {
            sendDebug(F("Invalid XYSPACING command"), valueStr);
            return Command(CommandType::INVALID, 0.0f);
        }

        sendDebug(F("Parsed XYSPACING command"), valueStr);
        return Command(CommandType::X_Y_SPACING, value);
    }

    if (strncmp(line, "YXSPACING:", 10) == 0) {
        const char *valueStr = line + 10;
        float value = 0.0f;
        if (!parseFloatValue(valueStr, value)) {
            sendDebug(F("Invalid YXSPACING command"), valueStr);
            return Command(CommandType::INVALID, 0.0f);
        }

        sendDebug(F("Parsed YXSPACING command"), valueStr);
        return Command(CommandType::Y_X_SPACING, value);
    }

    if (strncmp(line, "YYSPACING:", 10) == 0) {
        const char *valueStr = line + 10;
        float value = 0.0f;
        if (!parseFloatValue(valueStr, value)) {
            sendDebug(F("Invalid YYSPACING command"), valueStr);
            return Command(CommandType::INVALID, 0.0f);
        }

        sendDebug(F("Parsed YYSPACING command"), valueStr);
        return Command(CommandType::Y_Y_SPACING, value);
    }

    if (strncmp(line, "DIGITCOUNT:", 11) == 0) {
        const char *valueStr = line + 11;
        float value = 0.0f;
        if (!parseFloatValue(valueStr, value)) {
            sendDebug(F("Invalid DIGITCOUNT command"), valueStr);
            return Command(CommandType::INVALID, 0.0f);
        }

        sendDebug(F("Parsed DIGITCOUNT command"), valueStr);
        return Command(CommandType::DIGIT_COUNT, value);
    }

    if (strncmp(line, "SUFFIX:", 7) == 0) {
        const char *valueStr = line + 7;
        char suffix = '\0';
        if (!parseCharValue(valueStr, suffix)) {
            sendDebug(F("Invalid SUFFIX command"), valueStr);
            return Command(CommandType::INVALID, 0.0f);
        }

        sendDebug(F("Parsed SUFFIX command"), valueStr);
        return Command(CommandType::UNIT_SUFFIX, suffix);
    }

    if (strncmp(line, "INVERT:", 7) == 0) {
        const char *valueStr = line + 7;
        float value = 0.0f;
        if (!parseFloatValue(valueStr, value)) {
            sendDebug(F("Invalid INVERT command"), valueStr);
            return Command(CommandType::INVALID, 0.0f);
        }

        sendDebug(F("Parsed INVERT command"), valueStr);
        return Command(CommandType::INVERT, value);
    }

    // Unknown command format
    sendDebug(F("Unknown command"), line);
    return Command(CommandType::INVALID, 0.0f);
}
