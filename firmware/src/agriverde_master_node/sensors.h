#ifndef SENSORS_H
#define SENSORS_H

void setupSensors();
void updateSensors();
void updateFastSensors();
void updateAnalogSensors();

extern float currentTemperature;
extern float currentHumidity;
extern int soilMoistureValue;
extern int soilMoisturePercent;
extern int rainSensorValue;
extern int rainPercent;
extern int potentiometerValue;
extern int targetMoisturePercent;
extern bool isMotionDetected;
extern bool isMotionAlarmActive;
extern bool isTouchDetected;
extern bool isRaining;

#endif
