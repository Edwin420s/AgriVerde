#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <SPIFFS.h>
#include <DHT.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <BluetoothSerial.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

// ============================================================
// CONFIGURATION
// ============================================================
#define WIFI_SSID "Jerusalem Main"
#define WIFI_PASSWORD "@main020"
#define API_ENDPOINT "http://192.168.100.244:8000/api/v1/telemetry"
#define DEVICE_ID "AGR-NODE-001"
#define BT_DEVICE_NAME "AgriVerde-Node"
#define FIRMWARE_VERSION "0.6.1"


// Pin Definitions
#define DHTPIN 4
#define DHTTYPE DHT11
#define SOIL_PIN 34
#define RAIN_PIN 35
#define POT_PIN 32
#define TOUCH_PIN 18
#define PIR_PIN 14
#define PIR_PIN_ALT 12

// Outputs & Relays
#define RELAY_PIN 19
#define RELAY_ON LOW     // Active-LOW relay module: LOW = ON
#define RELAY_OFF HIGH   // HIGH = OFF
#define BUZZER_PIN 13
#define LED_GREEN 25
#define LED_BLUE 26
#define LED_RED 27

// OLED Display (SSD1306 128x64 I2C)
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1

// Sensor Calibration Thresholds
#define SOIL_DRY_ADC 4095
#define SOIL_WET_ADC 1400

#define RAIN_DRY_ADC 1850
#define RAIN_WET_ADC 1200
#define RAIN_PERCENT_THRESHOLD 45  // >= 45% moisture on sensor is considered raining

#define TEMP_ALARM_THRESHOLD 38.0  // Deg C alarm cutoff
#define MAX_PUMP_RUNTIME_MS 600000 // 10 minutes emergency safety limit
#define PIR_WARMUP_TIME_MS 2500    // 2.5s sensor warmup on boot
#define MOTION_ALARM_HOLD_MS 1000  // 1.0s continuous alarm & Red LED alert
#define BEEP_DURATION_MS 100       // Default 100ms chirp for touch feedback



// Loop Intervals
#define SENSOR_INTERVAL_MS 2000
#define TELEMETRY_INTERVAL_MS 15000   // 15s telemetry interval to keep Wi-Fi radio calm and quiet

// ============================================================
// Global Instances & States
// ============================================================
DHT dht(DHTPIN, DHTTYPE);
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
BluetoothSerial SerialBT;
bool btClientConnected = false;

enum SystemState {
  STATE_BOOT,
  STATE_MONITORING,
  STATE_IRRIGATING,
  STATE_RAIN_LOCK,
  STATE_FAULT,
  STATE_MANUAL
};
SystemState currentState = STATE_BOOT;

struct SensorData {
  float temperature;
  float humidity;
  int soilADC;
  int soilPercent;
  int targetMoisture;
  int rainADC;
  int rainPercent;
  bool raining;
  bool motion;
  bool sensorFault;
  uint32_t sequence;
} currentData;

unsigned long lastSensorRead = 0;
unsigned long lastTelemetrySend = 0;
unsigned long pumpStartTime = 0;
unsigned long pumpStopTime = 0;
unsigned long lastWifiCheck = 0;
uint32_t sequenceCounter = 0;

// Motion & Touch Tracking Variables
const int PIR_ACTIVE_LEVEL = HIGH; // Standard HC-SR501 Active-HIGH logic
bool pirActiveLowMode = false;
unsigned long motionDetectStartTime = 0;
unsigned long motionAlarmStartTime = 0;
unsigned long motionAlarmEndTime = 0;
bool isMotionConfirmed = false;
bool isMotionAlarmActive = false;

// Audio feedback tracking
bool isBeeping = false;
unsigned long beepStartTime = 0;
unsigned long beepDuration = 100;

bool manualOverride = false;
bool manualPumpState = false;
bool lastTouchState = LOW;
unsigned long lastTouchDebounceTime = 0;

bool isPumpRunning = false;
bool wifiConnected = false;
int bufferedCount = 0;
unsigned long lastWifiTxTime = 0;
unsigned long lastRelaySwitchTime = 0;

// Forward declarations
void handleSerialCommands(unsigned long now);
void readSensors(unsigned long now);
void runIrrigationEngine(unsigned long now);
void handleManualTouch(unsigned long now);
void handleMotion(unsigned long now);
void updateAlarmsAndLEDs(unsigned long now);
void triggerBuzzerBeep(unsigned int frequency, unsigned long durationMs, unsigned long now);
void handleWiFi(unsigned long now);
void updateDisplay();
void sendTelemetry();
void storeTelemetry(const String& json);
void flushBuffer();

// ============================================================
// Setup
// ============================================================
void setup() {
  // 1. Disable hardware brownout detector to prevent reboot loops on pump inrush
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

  Serial.begin(115200);

  // 2. Safe Relay Initialization (LATCH HIGH BEFORE PINMODE)
  // This prevents the active-LOW relay from clicking ON during boot/reset!
  digitalWrite(RELAY_PIN, RELAY_OFF);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, RELAY_OFF);
  isPumpRunning = false;

  // 3. LED & Alarm Pins
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_BLUE, OUTPUT);
  pinMode(LED_RED, OUTPUT);
  noTone(BUZZER_PIN);
  digitalWrite(BUZZER_PIN, LOW);

  // Audible & Visual Hardware Self-Test on Boot (Dual active + passive buzzer test)
  digitalWrite(LED_GREEN, HIGH);
  digitalWrite(LED_BLUE, HIGH);
  digitalWrite(LED_RED, HIGH);
  digitalWrite(BUZZER_PIN, HIGH); // DC level for Active Buzzer
  tone(BUZZER_PIN, 2000, 100);    // PWM tone for Passive Buzzer
  delay(120);
  noTone(BUZZER_PIN);
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(LED_GREEN, LOW);
  digitalWrite(LED_BLUE, LOW);
  digitalWrite(LED_RED, LOW);
  delay(80);
  // Second quick chirp
  digitalWrite(BUZZER_PIN, HIGH);
  tone(BUZZER_PIN, 2500, 80);
  delay(100);
  noTone(BUZZER_PIN);
  digitalWrite(BUZZER_PIN, LOW);

  // 4. Input Pins (internal pulldowns to prevent floating EMI triggers)
  pinMode(TOUCH_PIN, INPUT_PULLDOWN);
  pinMode(PIR_PIN, INPUT_PULLDOWN);
  pinMode(PIR_PIN_ALT, INPUT_PULLDOWN);
  pinMode(15, INPUT_PULLDOWN);

  // 5. Sensors
  dht.begin();

  // 6. OLED Setup with timeout to prevent I2C bus lockup
  Wire.begin(21, 22);
  Wire.setClock(400000); // Fast 400kHz I2C bus speed
  Wire.setTimeOut(100);
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("OLED init failed - continuing headless"));
  } else {
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println(F("AgriVerde Edge Node"));
    display.println(F("Initializing..."));
    display.display();
  }

  // 7. SPIFFS Offline Buffer Setup
  if (!SPIFFS.begin(true)) {
    Serial.println(F("SPIFFS mount failed"));
  } else {
    Serial.println(F("SPIFFS mounted successfully"));
    if (SPIFFS.exists("/buffer.log")) {
      SPIFFS.remove("/buffer.log");
      bufferedCount = 0;
      Serial.println(F("Stale offline buffer purged on boot."));
    }
  }

  // 8. Non-blocking Wi-Fi start with reduced RF TX power (15dBm) to eliminate PIR false triggers
  WiFi.mode(WIFI_STA);
  WiFi.setTxPower(WIFI_POWER_15dBm);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  // 9. Start Bluetooth Classic SPP
  if (!SerialBT.begin(BT_DEVICE_NAME)) {
    Serial.println(F("[BT] Bluetooth initialization failed"));
  } else {
    Serial.printf("[BT] Bluetooth Classic SPP started! Discoverable as '%s'\n", BT_DEVICE_NAME);
  }

  currentState = STATE_MONITORING;
  Serial.printf("AgriVerde Edge Node v%s Initialized Successfully.\n", FIRMWARE_VERSION);
}

// ============================================================
// Main Loop
// ============================================================
void loop() {
  unsigned long now = millis();

  // Bluetooth Connection Event Tracking
  bool currentBtClient = SerialBT.hasClient();
  if (currentBtClient != btClientConnected) {
    btClientConnected = currentBtClient;
    if (btClientConnected) {
      Serial.println(F("[BT] Remote client connected!"));
      SerialBT.println(F("\n========================================"));
      SerialBT.printf( " AgriVerde Edge Node v%s\n", FIRMWARE_VERSION);
      SerialBT.println(F(" Bluetooth Command & Telemetry Console"));
      SerialBT.println(F(" Type 'HELP' for list of commands."));
      SerialBT.println(F("========================================\n"));
    } else {
      Serial.println(F("[BT] Remote client disconnected."));
    }
    updateDisplay();
  }

  // Command Handlers (USB Serial & Bluetooth Serial)
  handleSerialCommands(now);

  // Fast loop: touch, motion checks, instant LED/buzzer reaction, continuous pump control
  handleManualTouch(now);
  handleMotion(now);
  updateAlarmsAndLEDs(now);
  runIrrigationEngine(now);
  handleWiFi(now);

  // Medium loop: sensors and display
  if (now - lastSensorRead >= SENSOR_INTERVAL_MS) {
    readSensors(now);
    updateDisplay();
    lastSensorRead = now;
  }

  // Telemetry loop: Wi-Fi dispatch or offline buffering
  if (now - lastTelemetrySend >= TELEMETRY_INTERVAL_MS) {
    sendTelemetry();
    lastTelemetrySend = now;
  }
}

// ============================================================
// Subsystems & Logic
// ============================================================

void triggerBuzzerBeep(unsigned int frequency, unsigned long durationMs, unsigned long now) {
  digitalWrite(BUZZER_PIN, HIGH);        // DC level for active buzzer
  tone(BUZZER_PIN, frequency, durationMs); // PWM wave for passive buzzer
  beepStartTime = now;
  beepDuration = durationMs;
  isBeeping = true;
}

void updateAlarmsAndLEDs(unsigned long now) {
  // 1. Red LED: ON during system fault OR active motion alarm hold
  bool redLedState = (currentState == STATE_FAULT || isMotionAlarmActive);
  digitalWrite(LED_RED, redLedState ? HIGH : LOW);

  // 2. Blue LED: Pump active indicator
  digitalWrite(LED_BLUE, isPumpRunning ? HIGH : LOW);

  // 3. Green/Yellow LED: Normal standby or rain lock
  digitalWrite(LED_GREEN, (currentState == STATE_MONITORING || currentState == STATE_RAIN_LOCK) ? HIGH : LOW);

  // 4. Buzzer control:
  // Continuous alarm while motion alarm is active (sounds continuously until LED turns off!)
  if (isMotionAlarmActive) {
    digitalWrite(BUZZER_PIN, HIGH);
    tone(BUZZER_PIN, 2200);
  } else if (isBeeping) {
    // Short feedback beep (e.g. touch tap or serial test)
    if (now - beepStartTime >= beepDuration) {
      noTone(BUZZER_PIN);
      digitalWrite(BUZZER_PIN, LOW);
      isBeeping = false;
    }
  } else {
    // Completely silent when no alarm or beep is active
    noTone(BUZZER_PIN);
    digitalWrite(BUZZER_PIN, LOW);
  }
}

void processCommand(Stream& port, String cmd, unsigned long now) {
  cmd.trim();
  if (cmd.length() == 0) return;

  if (cmd.equalsIgnoreCase("HELP") || cmd.equalsIgnoreCase("?")) {
    port.println(F("\n--- AgriVerde Node Commands ---"));
    port.println(F("STATUS    : Full sensor audit & state"));
    port.println(F("PUMP ON   : Manual pump relay ON"));
    port.println(F("PUMP OFF  : Manual pump relay OFF"));
    port.println(F("PUMP AUTO : Resume automatic irrigation"));
    port.println(F("LED TEST  : Cycle Green, Blue, and Red LEDs"));
    port.println(F("LED BLUE ON / OFF : Force Blue LED (GPIO 26) state"));
    port.println(F("TEST      : Buzzer & Red LED self-test"));
    port.println(F("TGT <val> : Set target soil moisture (0-100)"));
    port.println(F("JSON      : Dump telemetry JSON packet"));
    port.println(F("WIFI      : Wi-Fi status, IP, and signal RSSI"));
    port.println(F("BT        : Bluetooth status, device name, and MAC"));
    port.println(F("PIR_HIGH  : Set PIR to Active-HIGH"));
    port.println(F("PIR_LOW   : Set PIR to Active-LOW"));
    port.println(F("-------------------------------\n"));
  } else if (cmd.equalsIgnoreCase("STATUS") || cmd.equalsIgnoreCase("AUDIT")) {
    port.printf("[STATUS] Soil=%d%% (ADC:%d, Tgt:%d%%) | Rain=%d%% %s | Temp=%.1fC | Hum=%.0f%% | Pump=%s | Motion=%s | D14=%d | D18=%d | Blue(D26)=%d | Green(D25)=%d | Red(D27)=%d | WiFi=%s (%s)\n",
                currentData.soilPercent, currentData.soilADC, currentData.targetMoisture,
                currentData.rainPercent, currentData.raining ? "[WET]" : "[DRY]",
                currentData.temperature, currentData.humidity,
                isPumpRunning ? "ON" : "OFF",
                isMotionAlarmActive ? "ALARM" : (digitalRead(PIR_PIN) ? "DETECTED" : "CLEAR"),
                digitalRead(PIR_PIN), digitalRead(TOUCH_PIN),
                digitalRead(LED_BLUE), digitalRead(LED_GREEN), digitalRead(LED_RED),
                wifiConnected ? "CONNECTED" : "DISCONNECTED",
                wifiConnected ? WiFi.localIP().toString().c_str() : "No IP");
  } else if (cmd.equalsIgnoreCase("LED TEST")) {
    port.println(F("[LED TEST] Starting diagnostic LED sweep..."));
    port.println(F("[LED TEST] 1/3: Green LED (GPIO 25) ON"));
    digitalWrite(LED_GREEN, HIGH);
    delay(1000);
    digitalWrite(LED_GREEN, LOW);

    port.println(F("[LED TEST] 2/3: Blue LED (GPIO 26) ON"));
    digitalWrite(LED_BLUE, HIGH);
    delay(1000);
    digitalWrite(LED_BLUE, LOW);

    port.println(F("[LED TEST] 3/3: Red LED (GPIO 27) ON"));
    digitalWrite(LED_RED, HIGH);
    delay(1000);
    digitalWrite(LED_RED, LOW);

    port.println(F("[LED TEST] Sweep completed!"));
  } else if (cmd.equalsIgnoreCase("LED BLUE ON")) {
    digitalWrite(LED_BLUE, HIGH);
    port.println(F("[CMD] >>> GPIO 26 (Blue LED) forced HIGH (3.3V) <<<"));
  } else if (cmd.equalsIgnoreCase("LED BLUE OFF")) {
    digitalWrite(LED_BLUE, LOW);
    port.println(F("[CMD] >>> GPIO 26 (Blue LED) forced LOW (0V) <<<"));
  } else if (cmd.equalsIgnoreCase("PUMP ON")) {
    manualOverride = true;
    manualPumpState = true;
    digitalWrite(RELAY_PIN, RELAY_ON);
    isPumpRunning = true;
    digitalWrite(LED_BLUE, HIGH);
    pumpStartTime = now;
    lastRelaySwitchTime = now;
    updateDisplay();
    port.println(F("[CMD] >>> MANUAL PUMP: FORCED ON <<<"));
  } else if (cmd.equalsIgnoreCase("PUMP OFF")) {
    manualOverride = true;
    manualPumpState = false;
    digitalWrite(RELAY_PIN, RELAY_OFF);
    isPumpRunning = false;
    digitalWrite(LED_BLUE, LOW);
    pumpStopTime = now;
    lastRelaySwitchTime = now;
    updateDisplay();
    port.println(F("[CMD] >>> MANUAL PUMP: FORCED OFF <<<"));
  } else if (cmd.equalsIgnoreCase("PUMP AUTO")) {
    manualOverride = false;
    manualPumpState = false;
    updateDisplay();
    port.println(F("[CMD] >>> MANUAL OVERRIDE CLEARED (Auto irrigation resumed) <<<"));
  } else if (cmd.equalsIgnoreCase("TEST") || cmd.equalsIgnoreCase("BEEP")) {
    triggerBuzzerBeep(2400, 300, now);
    digitalWrite(LED_RED, HIGH);
    delay(300);
    digitalWrite(LED_RED, LOW);
    port.println(F("[CMD] >>> BUZZER & RED LED SELF-TEST OK! <<<"));
  } else if (cmd.startsWith("TGT ") || cmd.startsWith("tgt ")) {
    int val = cmd.substring(4).toInt();
    val = constrain(val, 0, 100);
    currentData.targetMoisture = val;
    port.printf("[CMD] >>> Target moisture threshold set to %d%% <<<\n", val);
  } else if (cmd.equalsIgnoreCase("JSON")) {
    StaticJsonDocument<512> d;
    d["device_id"] = DEVICE_ID;
    d["temp"] = currentData.temperature;
    d["humidity"] = currentData.humidity;
    d["soil"] = currentData.soilPercent;
    d["target"] = currentData.targetMoisture;
    d["rain"] = currentData.raining;
    d["motion"] = currentData.motion;
    d["pump"] = isPumpRunning;
    serializeJson(d, port);
    port.println();
  } else if (cmd.equalsIgnoreCase("WIFI")) {
    port.printf("[WIFI] Status: %s | SSID: %s | IP: %s | RSSI: %d dBm\n",
                wifiConnected ? "CONNECTED" : "DISCONNECTED",
                WIFI_SSID,
                wifiConnected ? WiFi.localIP().toString().c_str() : "0.0.0.0",
                wifiConnected ? WiFi.RSSI() : 0);
  } else if (cmd.equalsIgnoreCase("BT")) {
    port.printf("[BT] Device: %s | Status: %s | MAC: %s\n",
                BT_DEVICE_NAME,
                SerialBT.hasClient() ? "CLIENT CONNECTED" : "ADVERTISING (READY)",
                SerialBT.getBtAddressString().c_str());
  } else if (cmd.equalsIgnoreCase("PIR_LOW")) {
    pirActiveLowMode = true;
    port.println(F("[CMD] >>> PIR Polarity switched to ACTIVE-LOW <<<"));
  } else if (cmd.equalsIgnoreCase("PIR_HIGH")) {
    pirActiveLowMode = false;
    port.println(F("[CMD] >>> PIR Polarity switched to ACTIVE-HIGH <<<"));
  } else {
    port.printf("Unknown command: '%s'. Type HELP for command list.\n", cmd.c_str());
  }
}

void handleSerialCommands(unsigned long now) {
  // Read from USB Serial
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    processCommand(Serial, cmd, now);
  }

  // Read from Bluetooth Serial
  if (SerialBT.available()) {
    String cmd = SerialBT.readStringUntil('\n');
    processCommand(SerialBT, cmd, now);
  }
}

// ============================================================
// Motion Sensor Handling (GPIO 14 - Zero Latency Instant Trigger)
// ============================================================
bool motionReady = true;

void handleMotion(unsigned long now) {
  // 1. Boot Warmup & Transient Radio/Relay Guard
  if (now < PIR_WARMUP_TIME_MS) return;
  if (now - lastWifiTxTime < 150 || now - lastRelaySwitchTime < 250) return;

  // Read Pin 14 only (User connected PIR signal to G14)
  int raw14 = digitalRead(PIR_PIN);
  bool motionRaw = (!pirActiveLowMode) ? (raw14 == HIGH) : (raw14 == LOW);

  static int lastLogged14 = -1;
  if (raw14 != lastLogged14) {
    Serial.printf("[PIN 14] Level changed -> %s (%d)\n", raw14 == HIGH ? "HIGH (3.3V)" : "LOW (0V)", raw14);
    lastLogged14 = raw14;
  }

  // 2. Active Alarm Timer Handling: Keep Buzzer & Red LED ON continuously for full duration
  if (isMotionAlarmActive) {
    if (now - motionAlarmStartTime >= MOTION_ALARM_HOLD_MS) {
      isMotionAlarmActive = false;
      currentData.motion = false;

      // Turn both Red LED and Buzzer OFF simultaneously
      digitalWrite(LED_RED, LOW);
      noTone(BUZZER_PIN);
      digitalWrite(BUZZER_PIN, LOW);

      updateDisplay();
      Serial.println(F("[PIR EVENT] --- Motion alert ended (Buzzer & LED OFF). Ready for next wave."));
    }
    return;
  }

  // 3. Sensor Re-arm: As soon as sensor drops back to LOW (idle), re-arm for next wave
  if (!motionRaw) {
    motionReady = true;
  }

  // 4. Instant Zero-Latency Trigger on Hand Wave (Fires in 0ms on rising edge!)
  if (motionRaw && motionReady) {
    motionReady = false; // Disarm until wave ends and sensor drops LOW
    isMotionAlarmActive = true;
    motionAlarmStartTime = now;
    currentData.motion = true;

    // Immediately light Red LED and sound continuous 2200Hz buzzer tone
    digitalWrite(LED_RED, HIGH);
    digitalWrite(BUZZER_PIN, HIGH);
    tone(BUZZER_PIN, 2200);

    // Immediately update OLED to [MOT!]
    updateDisplay();

    Serial.printf("[PIR EVENT] >>> INSTANT MOTION DETECTED! Alarm & Red LED ON (D14=%d)\n", raw14);
  }
}

// ============================================================
// Capacitive Touch Handling (GPIO 18 - Instant Tactile Feedback)
// ============================================================
static bool touchLatched = false;
static unsigned long lastTouchTime = 0;

void handleManualTouch(unsigned long now) {
  int touchVal = digitalRead(TOUCH_PIN);

  // Instant trigger when touched (minimum 120ms between deliberate taps)
  if (touchVal == HIGH && !touchLatched && (now - lastTouchTime >= 120)) {
    touchLatched = true;
    lastTouchTime = now;

    // Toggle whatever the current pump state is
    manualOverride = true; // Engage manual override to lock the user's manual choice
    manualPumpState = !isPumpRunning;

    // Immediate Relay & Blue LED Actuation (Zero Latency!)
    isPumpRunning = manualPumpState;
    digitalWrite(RELAY_PIN, manualPumpState ? RELAY_ON : RELAY_OFF);
    digitalWrite(LED_BLUE, manualPumpState ? HIGH : LOW);

    // Instant audible chirp confirmation
    triggerBuzzerBeep(2800, 100, now);

    // Immediate OLED update
    updateDisplay();

    Serial.printf("[TOUCH] >>> MANUAL PUMP TOGGLED: %s | Relay=%s | Blue LED=%s\n",
                  manualPumpState ? "ON" : "OFF",
                  manualPumpState ? "ACTIVE (LOW)" : "OFF (HIGH)",
                  manualPumpState ? "ON (HIGH)" : "OFF (LOW)");
  } else if (touchVal == LOW && touchLatched) {
    // Unlatch immediately when finger leaves the touch sensor
    touchLatched = false;
    lastTouchTime = now;
  }
}

void readSensors(unsigned long now) {
  // DHT Readings
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  if (!isnan(t)) currentData.temperature = t;
  if (!isnan(h)) currentData.humidity = h;
  currentData.sensorFault = isnan(t) || isnan(h);

  // Soil Moisture Calibration
  currentData.soilADC = analogRead(SOIL_PIN);
  currentData.soilPercent = map(currentData.soilADC, SOIL_DRY_ADC, SOIL_WET_ADC, 0, 100);
  currentData.soilPercent = constrain(currentData.soilPercent, 0, 100);

  // Rain Sensor Calibration (Dry ~1850-4095 -> 0%, Wet ~1200 -> 100%)
  currentData.rainADC = analogRead(RAIN_PIN);
  currentData.rainPercent = map(currentData.rainADC, RAIN_DRY_ADC, RAIN_WET_ADC, 0, 100);
  currentData.rainPercent = constrain(currentData.rainPercent, 0, 100);
  // Raining if liquid intensity reaches threshold
  currentData.raining = (currentData.rainPercent >= RAIN_PERCENT_THRESHOLD);

  // Potentiometer -> Target Moisture Threshold (0 - 100%)
  int pot = analogRead(POT_PIN);
  int newTarget = map(pot, 0, 4095, 0, 100);
  newTarget = constrain(newTarget, 0, 100);
  if (newTarget <= 5) newTarget = 0;

  // If user adjusts the target potentiometer knob, automatically resume Auto mode!
  static int lastPotVal = -1;
  if (lastPotVal >= 0 && abs(newTarget - lastPotVal) >= 4) {
    if (manualOverride) {
      manualOverride = false;
      Serial.println(F("[POT] Knob adjusted -> Auto irrigation mode resumed."));
    }
  }
  lastPotVal = newTarget;
  currentData.targetMoisture = newTarget;

  // Telemetry Sequence Counter
  currentData.sequence = sequenceCounter++;

  Serial.printf("[PIN AUDIT] D14(PIR)=%d | D18(Touch)=%d | D26(Blue)=%d | D25(Green)=%d | D27(Red)=%d | Soil=%d%% | Tgt=%d%%\n",
                digitalRead(PIR_PIN),
                digitalRead(TOUCH_PIN),
                digitalRead(LED_BLUE),
                digitalRead(LED_GREEN),
                digitalRead(LED_RED),
                currentData.soilPercent,
                currentData.targetMoisture);
}

// ============================================================
// Irrigation Control Engine (Continuous Operation Without Pulsing)
// ============================================================
void runIrrigationEngine(unsigned long now) {
  bool pumpShouldBeOn = false;

  // Safety & Operational Hierarchy
  // 1. Manual Mode has highest priority (forced ON or forced OFF via touch or command)
  if (manualOverride) {
    currentState = STATE_MANUAL;
    pumpShouldBeOn = manualPumpState;
  }
  // 2. Sensor Fault or Extreme Temperature Safety Cutoff
  else if (currentData.sensorFault || currentData.temperature >= TEMP_ALARM_THRESHOLD) {
    currentState = STATE_FAULT;
    pumpShouldBeOn = false;
  }
  // 3. Rain Lock (strictly lockout irrigation if rain is detected)
  else if (currentData.raining) {
    currentState = STATE_RAIN_LOCK;
    pumpShouldBeOn = false;
  }
  // 4. Autonomous Soil Moisture Irrigation
  else {
    // If target moisture is 0% (potentiometer turned down), Auto-irrigation is OFF
    if (currentData.targetMoisture == 0) {
      pumpShouldBeOn = false;
      if (currentState == STATE_IRRIGATING) {
        currentState = STATE_MONITORING;
      }
    } else if (isPumpRunning) {
      // Pump is currently running: keep it CONTINUOUSLY ON until target moisture is satisfied!
      // Emergency runaway protection: 10 minutes max in case reservoir runs dry
      if (now - pumpStartTime >= MAX_PUMP_RUNTIME_MS) {
        pumpShouldBeOn = false;
        currentState = STATE_MONITORING;
        Serial.println(F("[SAFETY] Max pump runtime reached (10 min safety cutoff)."));
      } else if (currentData.soilPercent >= currentData.targetMoisture) {
        // Target moisture satisfied! Turn off pump.
        pumpShouldBeOn = false;
        currentState = STATE_MONITORING;
      } else {
        // Soil still below target moisture: KEEP PUMP CONTINUOUSLY RUNNING!
        pumpShouldBeOn = true;
        currentState = STATE_IRRIGATING;
      }
    } else {
      // Pump is currently off: if soil is dry, turn pump ON!
      if (currentData.soilPercent < currentData.targetMoisture) {
        pumpShouldBeOn = true;
        currentState = STATE_IRRIGATING;
      } else {
        pumpShouldBeOn = false;
        currentState = STATE_MONITORING;
      }
    }
  }

  // Actuate Relay & Blue LED (Active-LOW: RELAY_ON = LOW, RELAY_OFF = HIGH)
  if (pumpShouldBeOn && !isPumpRunning) {
    digitalWrite(RELAY_PIN, RELAY_ON);
    pumpStartTime = now;
    lastRelaySwitchTime = now;
    isPumpRunning = true;
    digitalWrite(LED_BLUE, HIGH);
    Serial.println(F("PUMP ENGAGED (Relay ON, Blue LED ON)"));
  } else if (!pumpShouldBeOn && isPumpRunning) {
    digitalWrite(RELAY_PIN, RELAY_OFF);
    pumpStopTime = now;
    lastRelaySwitchTime = now;
    isPumpRunning = false;
    digitalWrite(LED_BLUE, LOW);
    Serial.println(F("PUMP DISENGAGED (Relay OFF, Blue LED OFF)"));
  }
}

void handleWiFi(unsigned long now) {
  wl_status_t status = WiFi.status();
  if (status == WL_CONNECTED) {
    if (!wifiConnected) {
      wifiConnected = true;
      Serial.print(F("WiFi Connected! IP: "));
      Serial.println(WiFi.localIP());
    }
  } else {
    if (wifiConnected) {
      wifiConnected = false;
      Serial.println(F("WiFi connection lost."));
    }
    if (now - lastWifiCheck > 15000) {
      if (status != WL_IDLE_STATUS) {
        WiFi.disconnect();
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
      }
      lastWifiCheck = now;
    }
  }
}

void updateDisplay() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print(F("AgriVerde v")); display.print(F(FIRMWARE_VERSION));
  display.drawLine(0, 9, 128, 9, SSD1306_WHITE);

  // Line 1: Soil Moisture & Target
  display.setCursor(0, 12);
  display.print(F("Soil: ")); display.print(currentData.soilPercent); display.print(F("%"));
  display.setCursor(64, 12);
  if (currentData.targetMoisture == 0) {
    display.print(F("Tgt: OFF"));
  } else {
    display.print(F("Tgt: ")); display.print(currentData.targetMoisture); display.print(F("%"));
  }

  // Line 2: Temperature & Humidity
  display.setCursor(0, 22);
  display.print(F("T: ")); display.print(currentData.temperature, 1); display.print(F("C "));
  display.print(F("H: ")); display.print(currentData.humidity, 0); display.print(F("%"));

  // Line 3: Rain Intensity & State
  display.setCursor(0, 32);
  display.print(F("Rain: ")); display.print(currentData.rainPercent); display.print(F("% "));
  display.print(currentData.raining ? F("[WET]") : F("[DRY]"));

  // Line 4: System State & Pump Status
  display.setCursor(0, 42);
  display.print(F("State: "));
  switch (currentState) {
    case STATE_MONITORING: display.print(F("MONITOR")); break;
    case STATE_IRRIGATING: display.print(F("IRRIGATE")); break;
    case STATE_RAIN_LOCK:  display.print(F("RAIN_LOCK")); break;
    case STATE_FAULT:      display.print(F("FAULT")); break;
    case STATE_MANUAL:     display.print(F("MANUAL")); break;
    default:               display.print(F("BOOT")); break;
  }

  // Line 5: Connectivity, Pump & Motion
  display.setCursor(0, 53);
  display.print(wifiConnected ? F("W:OK ") : F("W:-- "));
  display.print(SerialBT.hasClient() ? F("B:OK ") : F("B:-- "));
  display.print(isPumpRunning ? F("P:ON ") : F("P:-- "));
  if (isMotionAlarmActive) {
    display.print(F("[MOT!]"));
  } else {
    display.print(F("[RDY]"));
  }

  display.display();
}

// ============================================================
// Telemetry Ingestion & Store-and-Forward Buffer
// ============================================================

void sendTelemetry() {
  StaticJsonDocument<768> doc;
  doc["device_id"] = DEVICE_ID;
  doc["sequence"] = currentData.sequence;
  doc["firmware_version"] = FIRMWARE_VERSION;

  // Primary API Fields
  doc["temperature"] = currentData.temperature;
  doc["humidity"] = currentData.humidity;
  doc["soil_moisture"] = currentData.soilPercent;
  doc["target_moisture"] = currentData.targetMoisture;
  doc["rain_detected"] = currentData.raining;
  doc["motion_detected"] = currentData.motion;
  doc["pump_active"] = isPumpRunning;
  doc["manual_override"] = manualOverride;
  doc["soil_raw"] = currentData.soilADC;
  doc["rain_raw"] = currentData.rainADC;
  doc["pir_raw"] = digitalRead(PIR_PIN);

  // Extended Research Fields
  doc["temperature_c"] = currentData.temperature;
  doc["humidity_percent"] = currentData.humidity;
  doc["soil_moisture_percent"] = currentData.soilPercent;
  doc["target_moisture_percent"] = currentData.targetMoisture;
  doc["soil_adc"] = currentData.soilADC;
  doc["rain_adc"] = currentData.rainADC;

  String jsonStr;
  serializeJson(doc, jsonStr);

  bool sent = false;
  if (wifiConnected) {
    HTTPClient http;
    http.begin(API_ENDPOINT);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(400); // 400ms non-blocking fast network timeout
    int code = http.POST(jsonStr);
    lastWifiTxTime = millis(); // Record Wi-Fi transmission time for EMI guard!
    if (code == 200 || code == 201) {
      sent = true;
      Serial.println(F("Live telemetry dispatched successfully."));
    } else {
      Serial.printf("HTTP POST failed with code %d\n", code);
    }
    http.end();
  }

  // If transmission failed or Wi-Fi was down, queue in offline SPIFFS flash
  if (!sent) {
    storeTelemetry(jsonStr);
  } else {
    // Flush at most one previously stored measurement to prevent loop freeze
    flushBuffer();
  }

  // Stream live telemetry to connected Bluetooth client
  if (SerialBT.hasClient()) {
    SerialBT.println(jsonStr);
  }
}

void storeTelemetry(const String& json) {
  File file = SPIFFS.open("/buffer.log", FILE_APPEND);
  if (file) {
    file.println(json);
    file.close();
    bufferedCount++;
    Serial.printf("Telemetry buffered to SPIFFS (Queue: %d)\n", bufferedCount);
  } else {
    Serial.println(F("Failed to open /buffer.log for append"));
  }
}

void flushBuffer() {
  if (!wifiConnected || !SPIFFS.exists("/buffer.log")) return;

  File file = SPIFFS.open("/buffer.log", FILE_READ);
  if (!file) return;

  String firstLine = "";
  if (file.available()) {
    firstLine = file.readStringUntil('\n');
    firstLine.trim();
  }

  // Gather any remaining lines to write back (prevents blocking loop)
  String remaining = "";
  int remCount = 0;
  while (file.available()) {
    String l = file.readStringUntil('\n');
    l.trim();
    if (l.length() > 0) {
      remaining += l + "\n";
      remCount++;
    }
  }
  file.close();

  if (firstLine.length() > 0) {
    HTTPClient http;
    http.begin(API_ENDPOINT);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(400);
    int code = http.POST(firstLine);
    lastWifiTxTime = millis();
    http.end();

    if (code == 200 || code == 201) {
      if (remaining.length() > 0) {
        File rewrite = SPIFFS.open("/buffer.log", FILE_WRITE);
        if (rewrite) {
          rewrite.print(remaining);
          rewrite.close();
        }
        bufferedCount = remCount;
      } else {
        SPIFFS.remove("/buffer.log");
        bufferedCount = 0;
      }
      Serial.printf("Buffered record flushed. Remaining in queue: %d\n", bufferedCount);
    }
  }
}