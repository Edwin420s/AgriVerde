#include <Arduino.h>
#include <DHT.h>
#include "sensors.h"
#include "config.h"

float currentTemperature = 0.0;
float currentHumidity = 0.0;
int soilMoistureValue = 0;
int rainSensorValue = 0;
int potentiometerValue = 0;
bool isMotionDetected = false;
bool isTouchDetected = false;
bool isRaining = false;

DHT dht(DHT_PIN, DHT_TYPE);

void setupSensors() {
    dht.begin();
    pinMode(TOUCH_SENSOR_PIN, INPUT);
    pinMode(PIR_SENSOR_PIN, INPUT);
}

static unsigned long lastDhtReadTime = 0;

void updateSensors() {
    // DHT11 sensors require at least 2 seconds between reads. 
    // Reading them too fast blocks the CPU and causes major lag!
    unsigned long currentMillis = millis();
    if (currentMillis - lastDhtReadTime >= 2000 || lastDhtReadTime == 0) {
        lastDhtReadTime = currentMillis;
        currentTemperature = dht.readTemperature();
        currentHumidity = dht.readHumidity();
    }

    // These sensors can be read at lightning speed every loop
    soilMoistureValue = analogRead(SOIL_MOISTURE_PIN);
    rainSensorValue = analogRead(RAIN_SENSOR_PIN);
    potentiometerValue = analogRead(POTENTIOMETER_PIN);
    isMotionDetected = digitalRead(PIR_SENSOR_PIN) == HIGH;
    isTouchDetected = digitalRead(TOUCH_SENSOR_PIN) == HIGH;
    
    // Rain threshold pushed up to 3500 to ensure it doesn't trigger when dry
    isRaining = (rainSensorValue > 3500);
}
