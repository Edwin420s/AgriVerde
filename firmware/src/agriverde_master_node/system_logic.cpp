#include <Arduino.h>
#include "system_logic.h"
#include "config.h"
#include "sensors.h"
#include "irrigation.h"

void setupSystemLogic() {
    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(LED_GREEN_PIN, OUTPUT);
    pinMode(LED_BLUE_PIN, OUTPUT);
    pinMode(LED_RED_PIN, OUTPUT);
    
    // Turn all off initially
    noTone(BUZZER_PIN);
    digitalWrite(LED_GREEN_PIN, LOW);
    digitalWrite(LED_BLUE_PIN, LOW);
    digitalWrite(LED_RED_PIN, LOW);
}

void updateSystemLogic() {
    // Reset all LEDs first
    digitalWrite(LED_GREEN_PIN, LOW);
    digitalWrite(LED_BLUE_PIN, LOW);
    digitalWrite(LED_RED_PIN, LOW);
    noTone(BUZZER_PIN);

    bool isAlarm = false;

    // 1. Motion Detection -> Red LED + Buzzer
    if (isMotionDetected) {
        digitalWrite(LED_RED_PIN, HIGH);
        tone(BUZZER_PIN, 2000); // Sound alarm at 2000Hz
        isAlarm = true;
    }

    // 2. Touch Detection -> Can act as a manual override or another alarm
    if (isTouchDetected) {
        // We'll also sound a quick beep and light Red for touch
        digitalWrite(LED_RED_PIN, HIGH);
        tone(BUZZER_PIN, 3000); // Sound alarm at 3000Hz
        isAlarm = true;
    }

    // 3 & 4. Rain & Pump Status
    bool pumpRunning = (digitalRead(RELAY_PUMP_PIN) == RELAY_ON);

    if (isRaining) {
        // If it is rain both the pump [LED] and green to be on
        digitalWrite(LED_BLUE_PIN, HIGH);
        if (!isAlarm) digitalWrite(LED_GREEN_PIN, HIGH);
    } else if (pumpRunning) {
        // If it is the pump only one led on (Blue)
        digitalWrite(LED_BLUE_PIN, HIGH);
        digitalWrite(LED_GREEN_PIN, LOW);
    } else {
        // Normal operation
        digitalWrite(LED_BLUE_PIN, LOW);
        if (!isAlarm) digitalWrite(LED_GREEN_PIN, HIGH);
    }
}
