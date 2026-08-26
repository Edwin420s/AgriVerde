#include <Arduino.h>
#include "config.h"
#include "sensors.h"
#include "display.h"
#include "irrigation.h"

void setup() {
    Serial.begin(115200);
    setupSensors();
    setupDisplay();
    setupIrrigation();
}

void loop() {
    // Using millis() for non-blocking delays
    static unsigned long lastSensorUpdate = 0;
    if (millis() - lastSensorUpdate > 2000) {
        updateSensors();
        updateIrrigation();
        updateDisplay();
        lastSensorUpdate = millis();
    }
}
