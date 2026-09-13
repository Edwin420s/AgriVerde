#include <Arduino.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include "config.h"
#include "sensors.h"
#include "display.h"
#include "irrigation.h"
#include "system_logic.h"

void setup() {
    // Disable ESP32 hardware brownout detector to prevent reboots on relay/pump inrush current
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

    Serial.begin(115200);
    setupSensors();
    setupDisplay();
    setupIrrigation();
    setupSystemLogic();
    Serial.println(F("AgriVerde Master Node Initialized Successfully."));
}

void loop() {
    unsigned long now = millis();

    // 1. FAST LOOP (~30ms): Motion, Touch, Alarm tone, and LED response
    static unsigned long lastFastUpdate = 0;
    if (now - lastFastUpdate >= 30) {
        updateFastSensors();
        updateSystemLogic();
        lastFastUpdate = now;
    }

    // 2. MEDIUM LOOP (200ms): Soil moisture, Rain sensor, Potentiometer, and Irrigation state machine
    static unsigned long lastMediumUpdate = 0;
    if (now - lastMediumUpdate >= 200) {
        updateAnalogSensors();
        updateIrrigation();
        lastMediumUpdate = now;
    }

    // 3. DISPLAY LOOP (500ms): OLED dashboard refresh & Serial telemetry
    static unsigned long lastDisplayUpdate = 0;
    if (now - lastDisplayUpdate >= 500) {
        updateDisplay();
        Serial.printf("TELEMETRY: PIR_PIN=%d, TOUCH_PIN=%d, RAIN_PCT=%d%%, SOIL_PCT=%d%%, POT_PCT=%d%%, RAIN_STATE=%s, PUMP=%s\n",
                      digitalRead(PIR_SENSOR_PIN),
                      digitalRead(TOUCH_SENSOR_PIN),
                      rainPercent,
                      soilMoisturePercent,
                      targetMoisturePercent,
                      isRaining ? "WET" : "DRY",
                      isPumpRunning ? "ON" : "OFF");
        lastDisplayUpdate = now;
    }

    // 4. SLOW LOOP (2000ms): DHT11 temperature & humidity read
    static unsigned long lastSlowUpdate = 0;
    if (now - lastSlowUpdate >= 2000) {
        updateSensors(); // Triggers non-blocking DHT read
        lastSlowUpdate = now;
    }
}
