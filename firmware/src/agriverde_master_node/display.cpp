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
    if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
        Serial.println(F("SSD1306 allocation failed"));
        for(;;); // Don't proceed, loop forever
    }
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println("AgriVerde Initializing...");
    display.display();
    delay(1000);
}

void updateDisplay() {
    display.clearDisplay();
    display.setCursor(0, 0);
    display.println("AgriVerde Dashboard");
    
    display.print("Temp: "); display.print(currentTemperature, 1); display.print("C ");
    display.print("Hum: "); display.print(currentHumidity, 1); display.println("%");
    display.print("Soil: "); display.print(soilMoistureValue);
    display.print(" Thr: "); display.println(potentiometerValue);
    
    display.print("Pump: ");
    display.print(digitalRead(RELAY_PUMP_PIN) == RELAY_ON ? "ON " : "OFF ");
    display.print("Touch: ");
    display.println(isTouchDetected ? "YES" : "NO");
    
    if (isMotionDetected) {
        display.println("ALERT: Motion!");
    }
    
    display.display();
}
