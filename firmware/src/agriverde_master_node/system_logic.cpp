#include <Arduino.h>
#include "system_logic.h"
#include "config.h"
#include "sensors.h"
#include "irrigation.h"

void setupSystemLogic() {
    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(LED_YELLOW_PIN, OUTPUT);
    pinMode(LED_BLUE_PIN, OUTPUT);
    pinMode(LED_RED_PIN, OUTPUT);
    
    // Turn all off initially
    noTone(BUZZER_PIN);
    digitalWrite(LED_YELLOW_PIN, LOW);
    digitalWrite(LED_BLUE_PIN, LOW);
    digitalWrite(LED_RED_PIN, LOW);
}

void updateSystemLogic() {
    unsigned long now = millis();
    static bool motionBeepDone = false;
    static bool isBeeping = false;
    static unsigned long beepStartTime = 0;

    // 1. Motion & Touch Alarm Handling (Single crisp beep on first detection, does NOT repeat)
    if (isMotionAlarmActive || isTouchDetected) {
        digitalWrite(LED_RED_PIN, HIGH);

        // Sound one single beep on first detection event - do NOT repeat while active
        if (!motionBeepDone) {
            tone(BUZZER_PIN, isTouchDetected ? 2800 : 1800);
            beepStartTime = now;
            isBeeping = true;
            motionBeepDone = true; // Lock: do not repeat beep for this detection event
        }
    } else {
        digitalWrite(LED_RED_PIN, LOW);
        motionBeepDone = false; // Reset lock once sensor has completely cleared
    }

    // Automatically silence buzzer after short BEEP_DURATION_MS (150ms)
    if (isBeeping && (now - beepStartTime >= BEEP_DURATION_MS)) {
        noTone(BUZZER_PIN);
        isBeeping = false;
    }

    // 2. Pump & Rain LED Status (Yellow = Standby/Normal, Blue = Pump Running)
    if (isPumpRunning || digitalRead(RELAY_PUMP_PIN) == RELAY_ON) {
        // Pump Active: Blue LED ON, Yellow LED OFF
        digitalWrite(LED_BLUE_PIN, HIGH);
        digitalWrite(LED_YELLOW_PIN, LOW);
    } else if (isRaining) {
        // Rain Detected: Pump is locked out, Blue LED is OFF, Yellow LED is ON
        digitalWrite(LED_BLUE_PIN, LOW);
        digitalWrite(LED_YELLOW_PIN, HIGH);
    } else {
        // Normal Standby: Blue LED OFF, Yellow LED ON
        digitalWrite(LED_BLUE_PIN, LOW);
        digitalWrite(LED_YELLOW_PIN, HIGH);
    }
}
