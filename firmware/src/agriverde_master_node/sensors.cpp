#include <Arduino.h>
#include <DHT.h>
#include "sensors.h"
#include "config.h"

float currentTemperature = 0.0;
float currentHumidity = 0.0;
int soilMoistureValue = 0;
int soilMoisturePercent = 0;
int rainSensorValue = 0;
int rainPercent = 0;
int potentiometerValue = 0;
int targetMoisturePercent = 0;
bool isMotionDetected = false;
bool isMotionAlarmActive = false;
bool isTouchDetected = false;
bool isRaining = false;

DHT dht(DHT_PIN, DHT_TYPE);

void setupSensors() {
    dht.begin();
    // Enable internal pulldowns to prevent floating inputs and spurious EMI triggers
    pinMode(TOUCH_SENSOR_PIN, INPUT_PULLDOWN);
    pinMode(PIR_SENSOR_PIN, INPUT_PULLDOWN);
    pinMode(SOIL_MOISTURE_PIN, INPUT);
    pinMode(RAIN_SENSOR_PIN, INPUT);
    pinMode(POTENTIOMETER_PIN, INPUT);
}

static unsigned long lastDhtReadTime = 0;
static unsigned long motionHighStartTime = 0;
static unsigned long lastMotionTriggerTime = 0;
static unsigned long lastAlarmEndTime = 0;
static unsigned long touchHighStartTime = 0;

void updateFastSensors() {
    unsigned long now = millis();

    // 1. PIR Sensor Warmup Grace Period:
    // PIR sensors (HC-SR501/AM312) take 25 seconds after power-up to stabilize
    // their pyroelectric differential amplifiers before outputting valid readings.
    bool pirWarmedUp = (now >= PIR_WARMUP_TIME_MS);

    int pirReading = digitalRead(PIR_SENSOR_PIN);
    int touchReading = digitalRead(TOUCH_SENSOR_PIN);

    // 2. Glitch-Filtering, Debounce & Cooldown for PIR Sensor:
    // Real human movement holds the line HIGH for >250ms.
    // Stray RF, convection air currents, or thermal noise spikes are filtered out.
    if (pirWarmedUp && (now - lastAlarmEndTime >= PIR_COOLDOWN_MS)) {
        if (pirReading == HIGH) {
            if (motionHighStartTime == 0) {
                motionHighStartTime = now;
            } else if (now - motionHighStartTime >= PIR_TRIGGER_CONFIRM_MS) {
                if (!isMotionAlarmActive) {
                    isMotionDetected = true;
                    lastMotionTriggerTime = now;
                    isMotionAlarmActive = true;
                }
            }
        } else {
            motionHighStartTime = 0;
            isMotionDetected = false;
        }
    } else {
        motionHighStartTime = 0;
        isMotionDetected = false;
    }

    // Motion Alarm Hold Logic (clears after hold time, then enters cooldown)
    if (isMotionAlarmActive && (now - lastMotionTriggerTime >= MOTION_ALARM_HOLD_MS)) {
        isMotionAlarmActive = false;
        lastAlarmEndTime = now;
    }

    // 3. Touch Debounce (50ms)
    if (touchReading == HIGH) {
        if (touchHighStartTime == 0) {
            touchHighStartTime = now;
        } else if (now - touchHighStartTime >= 50) {
            isTouchDetected = true;
        }
    } else {
        touchHighStartTime = 0;
        isTouchDetected = false;
    }
}

void updateAnalogSensors() {
    // Read analog sensors
    soilMoistureValue = analogRead(SOIL_MOISTURE_PIN);
    rainSensorValue = analogRead(RAIN_SENSOR_PIN);
    potentiometerValue = analogRead(POTENTIOMETER_PIN);

    // Rain percentage: Dry air (1850) -> 0%. Liquid on sensor (1200) -> 100%
    // Higher percentage = more liquid/rain!
    rainPercent = map(rainSensorValue, RAIN_DRY_ADC, RAIN_WET_ADC, 0, 100);
    rainPercent = constrain(rainPercent, 0, 100);

    // Liquid detected if intensity reaches threshold (e.g. >= 45%)
    isRaining = (rainPercent >= RAIN_PERCENT_THRESHOLD);

    // Soil moisture: 4095 in dry air -> 0%, 1400 in water -> 100%
    // Higher percentage = more moisture!
    soilMoisturePercent = map(soilMoistureValue, SOIL_DRY_ADC, SOIL_WET_ADC, 0, 100);
    soilMoisturePercent = constrain(soilMoisturePercent, 0, 100);

    // Target moisture threshold mapped from potentiometer (0 - 100%)
    targetMoisturePercent = map(potentiometerValue, 0, 4095, 0, 100);
    targetMoisturePercent = constrain(targetMoisturePercent, 0, 100);
}

void updateSensors() {
    updateFastSensors();
    updateAnalogSensors();

    // DHT11 sensors require at least 2 seconds between reads.
    unsigned long currentMillis = millis();
    if (currentMillis - lastDhtReadTime >= 2000 || lastDhtReadTime == 0) {
        lastDhtReadTime = currentMillis;
        float t = dht.readTemperature();
        float h = dht.readHumidity();
        if (!isnan(t)) currentTemperature = t;
        if (!isnan(h)) currentHumidity = h;
    }
}
