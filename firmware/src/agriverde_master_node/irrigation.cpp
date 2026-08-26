#include <Arduino.h>
#include "irrigation.h"
#include "config.h"
#include "sensors.h"

void setupIrrigation() {
    pinMode(RELAY_PUMP_PIN, OUTPUT);
    digitalWrite(RELAY_PUMP_PIN, LOW); // Off by default
}

void updateIrrigation() {
    // Simple logic for pump based on soil moisture
    if (soilMoistureValue > MOISTURE_THRESHOLD_DRY) {
        digitalWrite(RELAY_PUMP_PIN, HIGH); // Turn on
    } else if (soilMoistureValue < MOISTURE_THRESHOLD_WET) {
        digitalWrite(RELAY_PUMP_PIN, LOW); // Turn off
    }
}
