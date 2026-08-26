#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <SPIFFS.h>
#include <DHT.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ==============================
// CONFIGURATION (change these)
// ==============================
#define WIFI_SSID "your_wifi_ssid"
#define WIFI_PASSWORD "your_wifi_password"
#define API_ENDPOINT "http://your_fedora_ip:8000/api/v1/telemetry"
#define DEVICE_ID "AGR-NODE-001"
#define FIRMWARE_VERSION "0.4.0"

// Pin definitions
#define DHTPIN 4
#define SOIL_PIN 34
#define RAIN_PIN 35
#define POT_PIN 32
#define TOUCH_PIN 18
#define PIR_PIN 14
#define RELAY_PIN 19
#define BUZZER_PIN 13
#define LED_GREEN 25
#define LED_BLUE 26
#define LED_RED 27

#define DHTTYPE DHT11
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1

// Calibration (tune these)
#define SOIL_DRY 4095
#define SOIL_WET 1500
#define RAIN_THRESHOLD 3000
#define TEMP_ALARM_THRESHOLD 30.0
#define MAX_PUMP_RUNTIME_MS 60000  // 60 seconds safety

// Timing
#define SENSOR_INTERVAL_MS 2000
#define TELEMETRY_INTERVAL_MS 5000

// ==============================
// Globals
// ==============================
DHT dht(DHTPIN, DHTTYPE);
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// State machine
enum SystemState {
  STATE_BOOT,
  STATE_MONITORING,
  STATE_IRRIGATING,
  STATE_RAIN_LOCK,
  STATE_FAULT,
  STATE_MANUAL
};
SystemState currentState = STATE_BOOT;

// Sensor snapshot
struct SensorData {
  float temperature;
  float humidity;
  int soilADC;
  int soilPercent;
  int targetMoisture;
  int rainADC;
  bool raining;
  bool motion;
  bool sensorFault;
  uint32_t sequence;
} currentData;

unsigned long lastSensorRead = 0;
unsigned long lastTelemetrySend = 0;
unsigned long pumpStartTime = 0;
unsigned long lastWifiCheck = 0;
uint32_t sequenceCounter = 0;

bool manualOverride = false;
bool manualPumpState = false;
bool lastTouchState = LOW;
unsigned long lastDebounceTime = 0;

// Wi‑Fi status
bool wifiConnected = false;
bool wifiLastAttempt = false;

// ==============================
// Setup
// ==============================
void setup() {
  Serial.begin(115200);
  
  // Pins
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_BLUE, OUTPUT);
  pinMode(LED_RED, OUTPUT);
  pinMode(TOUCH_PIN, INPUT);
  pinMode(PIR_PIN, INPUT);
  digitalWrite(RELAY_PIN, LOW);
  
  // Sensors
  dht.begin();
  
  // OLED
  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED init failed");
  }
  display.clearDisplay();
  display.setTextColor(WHITE);
  
  // SPIFFS for offline buffer
  if(!SPIFFS.begin(true)) {
    Serial.println("SPIFFS mount failed");
  }
  
  // Wi‑Fi non‑blocking start
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  currentState = STATE_MONITORING;
  Serial.println("AgriVerde Edge Node v0.4.0 started");
}

// ==============================
// Main loop
// ==============================
void loop() {
  unsigned long now = millis();
  
  handleManualTouch(now);
  handleWiFi(now);
  
  if (now - lastSensorRead >= SENSOR_INTERVAL_MS) {
    readSensors(now);
    runIrrigationEngine(now);
    updateDisplay();
    lastSensorRead = now;
  }
  
  if (now - lastTelemetrySend >= TELEMETRY_INTERVAL_MS) {
    sendTelemetry();  // sends buffered + current
    lastTelemetrySend = now;
  }
}

// ==============================
// Subsystems
// ==============================

void readSensors(unsigned long now) {
  // DHT
  currentData.temperature = dht.readTemperature();
  currentData.humidity = dht.readHumidity();
  currentData.sensorFault = isnan(currentData.temperature) || isnan(currentData.humidity);
  
  // Soil
  currentData.soilADC = analogRead(SOIL_PIN);
  currentData.soilPercent = map(currentData.soilADC, SOIL_DRY, SOIL_WET, 0, 100);
  currentData.soilPercent = constrain(currentData.soilPercent, 0, 100);
  
  // Rain
  currentData.rainADC = analogRead(RAIN_PIN);
  currentData.raining = (currentData.rainADC < RAIN_THRESHOLD);
  
  // Potentiometer -> target moisture
  int pot = analogRead(POT_PIN);
  currentData.targetMoisture = map(pot, 0, 4095, 0, 100);
  currentData.targetMoisture = constrain(currentData.targetMoisture, 0, 100);
  
  // PIR
  currentData.motion = digitalRead(PIR_PIN) == HIGH;
  
  // Sequence
  currentData.sequence = sequenceCounter++;
}

void runIrrigationEngine(unsigned long now) {
  // Safety hierarchy
  bool pumpShouldBeOn = false;
  
  // 1. Manual override highest priority
  if (manualOverride) {
    currentState = STATE_MANUAL;
    pumpShouldBeOn = manualPumpState;
  }
  // 2. Sensor fault
  else if (currentData.sensorFault || currentData.temperature >= TEMP_ALARM_THRESHOLD) {
    currentState = STATE_FAULT;
    pumpShouldBeOn = false;
  }
  // 3. Rain lock
  else if (currentData.raining) {
    currentState = STATE_RAIN_LOCK;
    pumpShouldBeOn = false;
  }
  // 4. Normal operation
  else {
    if (currentState == STATE_MONITORING && currentData.soilPercent < currentData.targetMoisture) {
      currentState = STATE_IRRIGATING;
      pumpStartTime = now;
      pumpShouldBeOn = true;
    } else if (currentState == STATE_IRRIGATING) {
      // Safety max runtime
      if (now - pumpStartTime > MAX_PUMP_RUNTIME_MS) {
        currentState = STATE_FAULT;
        pumpShouldBeOn = false;
      } else if (currentData.soilPercent > (currentData.targetMoisture + 10)) {
        currentState = STATE_MONITORING;
        pumpShouldBeOn = false;
      } else {
        pumpShouldBeOn = true;
      }
    } else {
      currentState = STATE_MONITORING;
      pumpShouldBeOn = false;
    }
  }
  
  digitalWrite(RELAY_PIN, pumpShouldBeOn ? HIGH : LOW);
  digitalWrite(LED_BLUE, pumpShouldBeOn ? HIGH : LOW);
  digitalWrite(LED_GREEN, (currentState == STATE_MONITORING) ? HIGH : LOW);
  digitalWrite(LED_RED, (currentState == STATE_FAULT) ? HIGH : LOW);
  
  if (currentState == STATE_FAULT) {
    tone(BUZZER_PIN, 1000, 100);
  }
}

void handleManualTouch(unsigned long now) {
  int reading = digitalRead(TOUCH_PIN);
  if (reading != lastTouchState) {
    lastDebounceTime = now;
  }
  if ((now - lastDebounceTime) > 50) {
    if (reading == HIGH && !manualOverride) {
      manualOverride = true;
      manualPumpState = !manualPumpState;
    } else if (reading == LOW) {
      manualOverride = false;
    }
  }
  lastTouchState = reading;
}

void handleWiFi(unsigned long now) {
  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
  } else {
    if (now - lastWifiCheck > 10000) {
      WiFi.reconnect();
      lastWifiCheck = now;
    }
    wifiConnected = false;
  }
}

void updateDisplay() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("AgriVerde v"); display.print(FIRMWARE_VERSION);
  display.drawLine(0, 10, 128, 10, WHITE);
  
  display.setCursor(0, 15); display.print("Soil: "); display.print(currentData.soilPercent); display.print("%");
  display.setCursor(64, 15); display.print("Tgt: "); display.print(currentData.targetMoisture); display.print("%");
  display.setCursor(0, 25); display.print("Temp: "); display.print(currentData.temperature, 1); display.print("C");
  display.setCursor(0, 35);
  display.print("State: ");
  switch(currentState) {
    case STATE_MONITORING: display.print("MONITR"); break;
    case STATE_IRRIGATING: display.print("IRRIG"); break;
    case STATE_RAIN_LOCK:  display.print("RAIN_L"); break;
    case STATE_FAULT:      display.print("FAULT"); break;
    case STATE_MANUAL:     display.print("MANUAL"); break;
  }
  display.setCursor(0, 50);
  display.print(wifiConnected ? "WIFI:OK" : "WIFI:ERR");
  display.display();
}

// ==============================
// Telemetry + Offline Buffer
// ==============================

void sendTelemetry() {
  // Prepare JSON
  StaticJsonDocument<512> doc;
  doc["device_id"] = DEVICE_ID;
  doc["timestamp"] = (uint32_t)(millis() / 1000);  // will be replaced by NTP later
  doc["temperature_c"] = currentData.temperature;
  doc["humidity_percent"] = currentData.humidity;
  doc["soil_moisture_percent"] = currentData.soilPercent;
  doc["soil_adc"] = currentData.soilADC;
  doc["rain_detected"] = currentData.raining;
  doc["rain_adc"] = currentData.rainADC;
  doc["target_moisture_percent"] = currentData.targetMoisture;
  doc["motion_detected"] = currentData.motion;
  doc["pump_active"] = digitalRead(RELAY_PIN) == HIGH;
  doc["manual_override"] = manualOverride;
  doc["firmware_version"] = FIRMWARE_VERSION;
  doc["sequence"] = currentData.sequence;
  
  String jsonStr;
  serializeJson(doc, jsonStr);
  
  // If Wi‑Fi is up, try to send
  bool sent = false;
  if (wifiConnected) {
    HTTPClient http;
    http.begin(API_ENDPOINT);
    http.addHeader("Content-Type", "application/json");
    int code = http.POST(jsonStr);
    if (code == 200 || code == 201) {
      sent = true;
      Serial.println("Telemetry sent successfully");
    } else {
      Serial.printf("HTTP POST failed: %d\n", code);
    }
    http.end();
  }
  
  // If not sent, store to SPIFFS
  if (!sent) {
    storeTelemetry(jsonStr);
    Serial.println("Telemetry buffered to SPIFFS");
  } else {
    // After a successful send, try to flush any buffered data
    flushBuffer();
  }
}

void storeTelemetry(String json) {
  File file = SPIFFS.open("/buffer.log", FILE_APPEND);
  if (file) {
    file.println(json);
    file.close();
  } else {
    Serial.println("Failed to open buffer file");
  }
}

void flushBuffer() {
  if (!wifiConnected) return;
  File file = SPIFFS.open("/buffer.log", FILE_READ);
  if (!file) return;
  
  String line;
  while (file.available()) {
    line = file.readStringUntil('\n');
    if (line.length() > 0) {
      // Try to send this buffered entry
      HTTPClient http;
      http.begin(API_ENDPOINT);
      http.addHeader("Content-Type", "application/json");
      int code = http.POST(line);
      if (code != 200 && code != 201) {
        // If send fails, stop flushing and keep remaining entries
        http.end();
        file.close();
        return;
      }
      http.end();
    }
  }
  file.close();
  // After all sent, delete the buffer file
  SPIFFS.remove("/buffer.log");
  Serial.println("Buffer flushed");
}