#pragma once

#include <Arduino.h>

#define DEBUG_SERIAL 0

/// Encapsulates USB serial communication and command parsing.
/// Supports extensible command format: COMMAND:VALUE\n
class SerialProtocol
{
public:
    /// Command type enumeration for different protocol messages.
    enum class CommandType
    {
        TEMP,            ///< Temperature update: TEMP:XXX
        DOT_DIAMETER,    ///< Dot diameter update: DOTDIAMETER:5
        START_X,         ///< Start X update: STARTX:15
        START_Y,         ///< Start Y update: STARTY:5
        X_X_SPACING,     ///< X-axis horizontal spacing update: XXSPACING:7.0
        X_Y_SPACING,     ///< X-axis vertical spacing update: XYSPACING:0.0
        Y_X_SPACING,     ///< Y-axis horizontal spacing update: YXSPACING:-4.0
        Y_Y_SPACING,     ///< Y-axis vertical spacing update: YYSPACING:7.0
        DIGIT_COUNT,     ///< Digit count update: DIGITCOUNT:3
        UNIT_SUFFIX,     ///< Unit suffix update: SUFFIX:C
        INVERT,          ///< Invert display update: INVERT:0 or INVERT:1
        INVALID          ///< Unrecognized command
    };

    /// Represents a parsed command with its type and payload.
    struct Command
    {
        CommandType type;
        float value;
        char suffix;

        Command() : type(CommandType::INVALID), value(0.0f), suffix('\0') {}
        Command(CommandType t, float v) : type(t), value(v), suffix('\0') {}
        Command(CommandType t, char s) : type(t), value(0.0f), suffix(s) {}

        bool isValid() const { return type != CommandType::INVALID; }
    };

    SerialProtocol();

    /// Initialize serial communication. Must be called once in setup().
    void begin();

    /// Process incoming serial data. Should be called in the main loop.
    void update();

    /// Check if a new command was received and is waiting to be handled.
    /// @return true if a command line was parsed and is ready to be retrieved
    bool hasNewCommand() const;

    /// Clear the pending command flag after the command has been handled.
    void clearNewCommand();

    /// Retrieve the most recently parsed command.
    /// @return Command struct with type and value
    const Command &getLastCommand() const;

    /// Send a status message to the serial monitor.
    void sendStatus(const __FlashStringHelper *status) const;

    /// Send a debug message to the serial monitor.
    void sendDebug(const __FlashStringHelper *label, const char *value) const;

    /// Send an ACK response to indicate command was processed successfully.
    void sendAckOk() const;

    /// Send a NAK response to indicate command parsing failed.
    void sendAckError() const;

private:
    Command lastCommand_;
    bool hasNewCommand_;
    uint32_t lastDebugLogMs_;

    static constexpr uint32_t kSerialDebugLogIntervalMs = 1000;
    static constexpr size_t kSerialLineMaxLength = 48;

    /// Parse a single line of serial input.
    /// @param line The raw line received (without newline)
    /// @return Parsed Command; type is INVALID if parsing fails
    Command parseLine(const char *line);
};
