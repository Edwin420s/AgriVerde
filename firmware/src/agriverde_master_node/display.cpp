#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "display.h"
#include "config.h"
#include "sensors.h"
#include "irrigation.h"

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

void setupDisplay() {
    Wire.begin(OLED_SDA, OLED_SCL);
    // Set 100ms I2C timeout to prevent bus lockup if relay switching causes electrical noise
    Wire.setTimeOut(100);

    if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
        Serial.println(F("SSD1306 allocation failed - check OLED wiring"));
        return;
    }
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println("AgriVerde Initializing...");
    display.display();
    delay(500);
}

void updateDisplay() {
    display.clearDisplay();
    display.setCursor(0, 0);
    display.println("AgriVerde Dashboard");
    
    // DHT Readings
    display.print("Temp: "); display.print(currentTemperature, 1); display.print("C ");
    display.print("Hum: "); display.print(currentHumidity, 0); display.println("%");
    
    // Soil Moisture: Intuitive percentage (0% = dry, 100% = submerged)
    display.print("Soil: "); display.print(soilMoisturePercent); display.print("%");
    display.print("   Tgt: "); display.print(targetMoisturePercent); display.println("%");
    
    // Rain Sensor: Intuitive intensity percentage (0% = dry, 100% = heavy liquid)
    display.print("Rain: "); display.print(rainPercent); display.print("%");
    display.println(isRaining ? " (WET)" : " (DRY)");
    
    // Pump Status & Runtime
    display.print("Pump: ");
    if (isPumpRunning || digitalRead(RELAY_PUMP_PIN) == RELAY_ON) {
        display.print("ON (");
        display.print(pumpCurrentRuntime / 1000);
        display.print("s) ");
    } else {
        display.print("OFF ");
    }
    
    display.print("Tch:");
    display.println(isTouchDetected ? "YES" : "NO");
    
    // Motion Alert / Warmup status
    if (millis() < PIR_WARMUP_TIME_MS) {
        display.print("PIR: Calibrating (");
        display.print((PIR_WARMUP_TIME_MS - millis()) / 1000 + 1);
        display.println("s)");
    } else if (isMotionAlarmActive) {
        display.println("ALERT: Motion Detected!");
    } else {
        display.println("Motion: None (Armed)");
    }
    
    display.display();
}
