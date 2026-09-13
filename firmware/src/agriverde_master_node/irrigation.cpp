#include <Arduino.h>
#include "irrigation.h"
#include "config.h"
#include "sensors.h"

bool isPumpRunning = false;
unsigned long pumpCurrentRuntime = 0;
static unsigned long pumpStartTime = 0;
static unsigned long pumpStopTime = 0;

void stopPump() {
    digitalWrite(RELAY_PUMP_PIN, RELAY_OFF);
    if (isPumpRunning) {
        pumpStopTime = millis();
        isPumpRunning = false;
    }
}

void setupIrrigation() {
    // Write OFF state to output latch BEFORE setting pinMode as OUTPUT
    // to prevent active-LOW relay glitch during boot/reboot!
    digitalWrite(RELAY_PUMP_PIN, RELAY_OFF);
    pinMode(RELAY_PUMP_PIN, OUTPUT);
    digitalWrite(RELAY_PUMP_PIN, RELAY_OFF);
    isPumpRunning = false;
}

void updateIrrigation() {
    unsigned long now = millis();

    // Safety 1: Never run the pump if it is raining!
    if (isRaining) {
        if (isPumpRunning) {
            stopPump();
        }
        return;
    }

    if (isPumpRunning) {
        pumpCurrentRuntime = now - pumpStartTime;

        // Safety 2: Max runtime cutoff to protect pump and avoid flooding
        if (pumpCurrentRuntime >= PUMP_MAX_RUNTIME_MS) {
            stopPump();
            return;
        }

        // Check if soil has reached target moisture (+ 5% hysteresis)
        // Ensure minimum runtime to avoid rapid cycling/relay chatter
        if (pumpCurrentRuntime >= PUMP_MIN_RUNTIME_MS && soilMoisturePercent >= (targetMoisturePercent + 5)) {
            stopPump();
            return;
        }
    } else {
        pumpCurrentRuntime = 0;

        // Safety 3: Enforce cooldown period between irrigation cycles
        if (now - pumpStopTime < PUMP_COOLDOWN_MS) {
            return;
        }

        // Start pump if soil moisture is below target threshold
        if (soilMoisturePercent < targetMoisturePercent) {
            digitalWrite(RELAY_PUMP_PIN, RELAY_ON);
            pumpStartTime = now;
            isPumpRunning = true;
        }
    }
}
