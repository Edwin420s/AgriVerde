#include <Arduino.h>
#include "irrigation.h"
#include "config.h"
#include "sensors.h"

void setupIrrigation() {
    pinMode(RELAY_PUMP_PIN, OUTPUT);
    digitalWrite(RELAY_PUMP_PIN, RELAY_OFF); // Off by default
}

void updateIrrigation() {
    // The potentiometer sets the threshold for when the soil is considered "DRY"
    int dynamicThreshold = potentiometerValue; 

    // Safety: Do not run the pump if it is currently raining!
    if (isRaining) {
        digitalWrite(RELAY_PUMP_PIN, RELAY_OFF);
        return;
    }

    // Simple logic for pump based on soil moisture
    if (soilMoistureValue > dynamicThreshold) {
        digitalWrite(RELAY_PUMP_PIN, RELAY_ON); // Turn on
    } else if (soilMoistureValue < dynamicThreshold - 300) { // 300 is hysteresis
        digitalWrite(RELAY_PUMP_PIN, RELAY_OFF); // Turn off
    }
}
