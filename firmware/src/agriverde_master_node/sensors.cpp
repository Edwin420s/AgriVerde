#include <Arduino.h>
#include "sensors.h"
#include "config.h"

float currentTemperature = 0.0;
float currentHumidity = 0.0;
int soilMoistureValue = 0;
int rainSensorValue = 0;
int potentiometerValue = 0;
bool isMotionDetected = false;
bool isTouchDetected = false;

void setupSensors() {
    pinMode(TOUCH_SENSOR_PIN, INPUT);
    pinMode(PIR_SENSOR_PIN, INPUT);
}

void updateSensors() {
    soilMoistureValue = analogRead(SOIL_MOISTURE_PIN);
    rainSensorValue = analogRead(RAIN_SENSOR_PIN);
    potentiometerValue = analogRead(POTENTIOMETER_PIN);
    isMotionDetected = digitalRead(PIR_SENSOR_PIN) == HIGH;
    isTouchDetected = digitalRead(TOUCH_SENSOR_PIN) == HIGH;
}
