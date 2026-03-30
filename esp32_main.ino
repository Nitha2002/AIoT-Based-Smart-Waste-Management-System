/*
 * AIoT Smart Waste Management System
 * ====================================
 * ESP32 Firmware
 *
 * Components:
 *   - Ultrasonic Sensor 1 (Compartment 1 - Recyclable)  : Trig=GPIO23, Echo=GPIO22
 *   - Ultrasonic Sensor 2 (Compartment 2 - Non-Recyclable): Trig=GPIO18, Echo=GPIO5
 *   - Weight Sensor (HX711 Load Cell)                    : SCK=GPIO32, DT=GPIO33
 *   - Servo Motor                                        : GPIO13
 *   - Wi-Fi for sending alerts to backend server
 *
 * Serial Commands from Python ML script:
 *   '1' → Recyclable    → Servo rotates CLOCKWISE     (90°)
 *   '0' → NonRecyclable → Servo rotates ANTI-CLOCKWISE (180°)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>
#include <HX711.h>

// ─── WiFi Credentials ────────────────────────────────────────────────────────
const char* SSID       = "YOUR_WIFI_SSID";
const char* PASSWORD   = "YOUR_WIFI_PASSWORD";

// ─── Backend Server ───────────────────────────────────────────────────────────
// Replace with your server IP (same network)
const char* SERVER_URL = "http://192.168.1.100:5000";

// ─── Pin Definitions ─────────────────────────────────────────────────────────
// Ultrasonic Sensor 1 (Recyclable compartment)
#define TRIG1  23
#define ECHO1  22

// Ultrasonic Sensor 2 (Non-recyclable compartment)
#define TRIG2  18
#define ECHO2  5

// HX711 Weight Sensor
#define HX711_SCK  32
#define HX711_DT   33

// Servo Motor
#define SERVO_PIN  13

// ─── Thresholds ───────────────────────────────────────────────────────────────
#define LEVEL_THRESHOLD_CM  10    // Alert when waste level < 10cm from sensor
#define WEIGHT_THRESHOLD_KG 5.0   // Alert when weight > 5kg

// ─── Objects ─────────────────────────────────────────────────────────────────
Servo wasteServo;
HX711 scale;

// ─── State ───────────────────────────────────────────────────────────────────
bool alertSent1 = false;
bool alertSent2 = false;
bool weightAlertSent = false;

// ─── Helpers ─────────────────────────────────────────────────────────────────
float measureDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  long duration = pulseIn(echoPin, HIGH, 30000);
  return (duration * 0.034) / 2.0;   // cm
}

float readWeight() {
  if (scale.is_ready()) {
    return scale.get_units(5);        // Average of 5 readings in kg
  }
  return -1.0;
}

void sendAlert(String type, float value, String unit) {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  String url = String(SERVER_URL) + "/api/alert";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");

  String body = "{\"type\":\"" + type + "\","
                 "\"value\":" + String(value, 2) + ","
                 "\"unit\":\"" + unit + "\"}";

  int code = http.POST(body);
  Serial.printf("Alert sent [%s=%.2f%s] → HTTP %d\n",
                type.c_str(), value, unit.c_str(), code);
  http.end();
}

void updateBinStatus(float level1, float level2, float weight) {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  String url = String(SERVER_URL) + "/api/bin/status";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");

  String body = "{\"level_recyclable\":" + String(level1, 1) + ","
                 "\"level_nonrecyclable\":" + String(level2, 1) + ","
                 "\"weight\":" + String(weight, 2) + "}";

  http.POST(body);
  http.end();
}

// ─── Servo Control ────────────────────────────────────────────────────────────
void servoClockwise() {
  // Recyclable → rotate to 90°
  wasteServo.write(90);
  delay(1000);
  wasteServo.write(0);   // Return to neutral
}

void servoAntiClockwise() {
  // Non-Recyclable → rotate to 180°
  wasteServo.write(180);
  delay(1000);
  wasteServo.write(0);   // Return to neutral
}

// ─── Setup ───────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(9600);

  // Pin modes
  pinMode(TRIG1, OUTPUT); pinMode(ECHO1, INPUT);
  pinMode(TRIG2, OUTPUT); pinMode(ECHO2, INPUT);

  // Servo
  wasteServo.attach(SERVO_PIN);
  wasteServo.write(0);

  // HX711 Scale
  scale.begin(HX711_DT, HX711_SCK);
  scale.set_scale(2280.f);    // Calibration factor — adjust for your load cell
  scale.tare();                // Reset to zero
  Serial.println("Scale tared.");

  // WiFi
  WiFi.begin(SSID, PASSWORD);
  Serial.print("Connecting to WiFi");
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected. IP: " + WiFi.localIP().toString());
  } else {
    Serial.println("\nWiFi failed. Running offline.");
  }

  Serial.println("AIoT Waste System Ready.");
}

// ─── Main Loop ────────────────────────────────────────────────────────────────
void loop() {

  // 1. Check for ML classification command from Python via Serial
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    if (cmd == '1') {
      Serial.println("Recyclable → Servo CLOCKWISE");
      servoClockwise();
    } else if (cmd == '0') {
      Serial.println("NonRecyclable → Servo ANTI-CLOCKWISE");
      servoAntiClockwise();
    }
  }

  // 2. Read sensors every 5 seconds
  static unsigned long lastRead = 0;
  if (millis() - lastRead >= 5000) {
    lastRead = millis();

    float dist1  = measureDistance(TRIG1, ECHO1);
    float dist2  = measureDistance(TRIG2, ECHO2);
    float weight = readWeight();

    Serial.printf("Level1: %.1fcm | Level2: %.1fcm | Weight: %.2fkg\n",
                  dist1, dist2, weight);

    // 3. Send status update to backend
    updateBinStatus(dist1, dist2, weight);

    // 4. Level alerts
    if (dist1 > 0 && dist1 < LEVEL_THRESHOLD_CM && !alertSent1) {
      sendAlert("level_recyclable", dist1, "cm");
      alertSent1 = true;
    } else if (dist1 >= LEVEL_THRESHOLD_CM) {
      alertSent1 = false;   // Reset when bin is emptied
    }

    if (dist2 > 0 && dist2 < LEVEL_THRESHOLD_CM && !alertSent2) {
      sendAlert("level_nonrecyclable", dist2, "cm");
      alertSent2 = true;
    } else if (dist2 >= LEVEL_THRESHOLD_CM) {
      alertSent2 = false;
    }

    // 5. Weight alert
    if (weight > WEIGHT_THRESHOLD_KG && !weightAlertSent) {
      sendAlert("weight", weight, "kg");
      weightAlertSent = true;
    } else if (weight <= WEIGHT_THRESHOLD_KG) {
      weightAlertSent = false;
    }
  }
}
