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
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(LED_GREEN_PIN, LOW);
    digitalWrite(LED_BLUE_PIN, LOW);
    digitalWrite(LED_RED_PIN, LOW);
}

void updateSystemLogic() {
    // Reset all LEDs first
    digitalWrite(LED_GREEN_PIN, LOW);
    digitalWrite(LED_BLUE_PIN, LOW);
    digitalWrite(LED_RED_PIN, LOW);
    digitalWrite(BUZZER_PIN, LOW);

    bool isAlarm = false;

    // 1. Motion Detection -> Red LED + Buzzer
    if (isMotionDetected) {
        digitalWrite(LED_RED_PIN, HIGH);
        digitalWrite(BUZZER_PIN, HIGH); // Sound alarm
        isAlarm = true;
    }

    // 2. Touch Detection -> Can act as a manual override or another alarm
    if (isTouchDetected) {
        // We'll also sound a quick beep and light Red for touch
        digitalWrite(LED_RED_PIN, HIGH);
        digitalWrite(BUZZER_PIN, HIGH);
        isAlarm = true;
    }

    // 3. Rain Sensor -> Blue LED (Temporarily disabled for testing Pump LED)
    // if (rainSensorValue < 3000) {
    //     digitalWrite(LED_BLUE_PIN, HIGH);
    // }

    // 4. Pump Status -> Blue LED
    if (digitalRead(RELAY_PUMP_PIN) == RELAY_ON) {
        digitalWrite(LED_BLUE_PIN, HIGH);
    }

    // 5. Normal Operation -> Green LED
    // If no alarm, show green.
    if (!isAlarm) {
        digitalWrite(LED_GREEN_PIN, HIGH);
    }
}
