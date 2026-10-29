// ====================================================================
// SMART DUSTBIN 2 (BIN-002) - ARDUINO UNO FIRMWARE
// Configuration: Fill Level Sensor ONLY (HC-SR04), NO Servo, NO Proximity Sensor
// ====================================================================

#include <SoftwareSerial.h>

// SoftwareSerial TX on Pin 10 -> Connected to ESP32 Pin 16 (RX2)
SoftwareSerial espSerial(11, 10); // RX (Pin 11 unused), TX (Pin 10)

// ==================== PIN CONFIGURATION ====================
const int LEVEL_TRIG_PIN  = 4; // Trash fill-level sensor Trigger
const int LEVEL_ECHO_PIN  = 5; // Trash fill-level sensor Echo

// Optional Status LEDs (if connected)
const int GREEN_LED_PIN   = 6;
const int YELLOW_LED_PIN  = 7;
const int RED_LED_PIN     = 8;

// ==================== CALIBRATION (in cm) ====================
// Adjust these to match the height of your second dustbin
const float EMPTY_DISTANCE_CM  = 20.0; // Distance when bin is completely empty
const float FULL_DISTANCE_CM   = 4.0;  // Distance when trash is near the top

// Thresholds for alerts
const int YELLOW_START_PERCENT = 50;
const int RED_START_PERCENT    = 80;

int lastFillPercent = 0;
float lastLevelDistance = 0;
unsigned long lastTelemetryTime = 0;

// Read distance from HC-SR04
float readDistanceCm(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH, 25000); // 25ms timeout (~4m max)
  if (duration == 0) return -1;
  return (duration * 0.0343 / 2.0);
}

// Convert distance to fill percentage
int distanceToFillPercent(float distanceCm) {
  float fill = ((EMPTY_DISTANCE_CM - distanceCm) / (EMPTY_DISTANCE_CM - FULL_DISTANCE_CM)) * 100.0;
  if (fill < 0)   fill = 0;
  if (fill > 100) fill = 100;
  return (int)fill;
}

// Update Traffic LEDs
void updateIndicators(int fillPercent) {
  if (fillPercent >= RED_START_PERCENT) {
    digitalWrite(GREEN_LED_PIN, LOW);
    digitalWrite(YELLOW_LED_PIN, LOW);
    digitalWrite(RED_LED_PIN, HIGH);
  } else if (fillPercent >= YELLOW_START_PERCENT) {
    digitalWrite(GREEN_LED_PIN, LOW);
    digitalWrite(YELLOW_LED_PIN, HIGH);
    digitalWrite(RED_LED_PIN, LOW);
  } else {
    digitalWrite(GREEN_LED_PIN, HIGH);
    digitalWrite(YELLOW_LED_PIN, LOW);
    digitalWrite(RED_LED_PIN, LOW);
  }
}

// Send telemetry packet to ESP32 and USB Serial
void sendTelemetry() {
  String statusStr = "NORMAL";
  if (lastFillPercent >= RED_START_PERCENT) statusStr = "FULL";
  else if (lastFillPercent >= YELLOW_START_PERCENT) statusStr = "HALF_FULL";

  // Packet format: DATA,fill,dist,lid,status
  // Lid is reported as "N/A" since Bin 2 has no servo
  String packet = "DATA," + String(lastFillPercent) + "," + 
                  String(lastLevelDistance > 0 ? (int)lastLevelDistance : 0) + "," + 
                  "N/A," + 
                  statusStr;

  espSerial.println(packet); // Sent to ESP32 Pin 16
  Serial.println(packet);    // Sent to PC USB Serial
}

void setup() {
  Serial.begin(9600);
  espSerial.begin(9600);

  pinMode(LEVEL_TRIG_PIN, OUTPUT);
  pinMode(LEVEL_ECHO_PIN, INPUT);

  pinMode(GREEN_LED_PIN, OUTPUT);
  pinMode(YELLOW_LED_PIN, OUTPUT);
  pinMode(RED_LED_PIN, OUTPUT);

  Serial.println(F("Dustbin 2 (BIN-002) Initialized - Sensor on Pins 4 & 5"));
  delay(500);
}

void loop() {
  // Read ultrasonic level sensor
  float dist = readDistanceCm(LEVEL_TRIG_PIN, LEVEL_ECHO_PIN);

  if (dist > 0 && dist <= 100) {
    lastLevelDistance = dist;
    int currentFill = distanceToFillPercent(dist);

    // If fill level changed significantly, send telemetry immediately
    if (abs(currentFill - lastFillPercent) >= 2) {
      lastFillPercent = currentFill;
      updateIndicators(lastFillPercent);
      sendTelemetry();
      lastTelemetryTime = millis();
    }
  }

  // Heartbeat telemetry every 2 seconds
  if (millis() - lastTelemetryTime >= 2000) {
    updateIndicators(lastFillPercent);
    sendTelemetry();
    lastTelemetryTime = millis();
  }

  delay(200); // 5Hz sampling rate
}
