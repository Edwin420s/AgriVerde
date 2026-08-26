#ifndef SENSORS_H
#define SENSORS_H

void setupSensors();
void updateSensors();

extern float currentTemperature;
extern float currentHumidity;
extern int soilMoistureValue;
extern int rainSensorValue;
extern int potentiometerValue;
extern bool isMotionDetected;
extern bool isTouchDetected;
extern bool isRaining;

#endif
