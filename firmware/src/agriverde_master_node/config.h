#ifndef CONFIG_H
#define CONFIG_H

// OLED I2C
#define OLED_SDA 21
#define OLED_SCL 22
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1

// Sensors
#define DHT_PIN 4
#define DHT_TYPE DHT11
#define SOIL_MOISTURE_PIN 34
#define RAIN_SENSOR_PIN 35
#define POTENTIOMETER_PIN 32
#define TOUCH_SENSOR_PIN 18
#define PIR_SENSOR_PIN 14

// Outputs
#define RELAY_PUMP_PIN 19
#define RELAY_ON LOW
#define RELAY_OFF HIGH
#define BUZZER_PIN 13
#define LED_YELLOW_PIN 25
#define LED_GREEN_PIN LED_YELLOW_PIN  // Alias for backward compatibility
#define LED_BLUE_PIN 26
#define LED_RED_PIN 27

// Sensor Calibration & Threshold Settings
#define SOIL_DRY_ADC 4095               // Measured: 4095 in dry air -> 0%
#define SOIL_WET_ADC 1400               // Measured: ~1400 in water -> 100%

// Rain Sensor Calibration (Percentage based):
// Dry air reads ~1850-1880 ADC (0%). Liquid on sensor drops ADC to ~1200 (100%).
#define RAIN_DRY_ADC 1850               // 0% rain (dry in air)
#define RAIN_WET_ADC 1200               // 100% rain (liquid on sensor)
#define RAIN_PERCENT_THRESHOLD 45       // >= 45% intensity is considered WET (raining)

// Irrigation & Pump Safety Settings
#define PUMP_MAX_RUNTIME_MS 10000       // Max 10s continuous run to prevent burn-out
#define PUMP_MIN_RUNTIME_MS 2000        // Min 2s run time to prevent relay chatter
#define PUMP_COOLDOWN_MS 5000           // 5s cooldown between irrigation runs

// Motion Alarm Settings
#define PIR_WARMUP_TIME_MS 25000        // 25s stabilization period for PIR sensor
#define PIR_TRIGGER_CONFIRM_MS 200      // Require signal to hold HIGH for 200ms to confirm real physical movement
#define PIR_COOLDOWN_MS 3000            // 3s cooldown between alarms
#define MOTION_ALARM_HOLD_MS 2000       // Visual alarm hold duration (2s)
#define BEEP_DURATION_MS 150            // Single crisp beep duration (150ms) - does not repeat

#endif // CONFIG_H
