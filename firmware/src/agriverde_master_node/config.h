#ifndef CONFIG_H
#define CONFIG_H

// OLED I2C
#define OLED_SDA 21
#define OLED_SCL 22

// Sensors
#define DHT_PIN 4
#define DHT_TYPE 11 // Assuming DHT11 based on previous interactions
#define SOIL_MOISTURE_PIN 34
#define RAIN_SENSOR_PIN 35
#define POTENTIOMETER_PIN 32
#define TOUCH_SENSOR_PIN 18
#define PIR_SENSOR_PIN 14

// Outputs
#define RELAY_PUMP_PIN 19
#define BUZZER_PIN 13
#define LED_GREEN_PIN 25
#define LED_BLUE_PIN 26
#define LED_RED_PIN 27

// Settings
#define MOISTURE_THRESHOLD_DRY 3000
#define MOISTURE_THRESHOLD_WET 1500
#define PUMP_MAX_RUNTIME_MS 10000

#endif // CONFIG_H
