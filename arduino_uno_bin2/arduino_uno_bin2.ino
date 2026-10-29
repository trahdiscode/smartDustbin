// ====================================================================
// SMART DUSTBIN 2 (BIN-002) - ARDUINO UNO FIRMWARE (BULLETPROOF V3)
// Configuration: Fill Level Sensor ONLY (HC-SR04)
// ====================================================================

#include <SoftwareSerial.h>

// SoftwareSerial Pin 10 is TX -> Connects to ESP32 Pin 16 (RX2)
SoftwareSerial espSerial(11, 10); // RX (Pin 11 unused), TX (Pin 10)

// ==================== PIN CONFIGURATION ====================
const int LEVEL_TRIG_PIN  = 4; // Sensor Trigger
const int LEVEL_ECHO_PIN  = 5; // Sensor Echo

// Status LEDs
const int GREEN_LED_PIN   = 6;
const int YELLOW_LED_PIN  = 7;
const int RED_LED_PIN     = 8;

// ==================== CALIBRATION (in cm) ====================
// Height of the dustbin:
// Any distance >= 25 cm means the bin is EMPTY (0%)
// Any distance <= 4 cm means the bin is FULL (100%)
const float EMPTY_DISTANCE_CM  = 25.0; 
const float FULL_DISTANCE_CM   = 4.0;  

// Status thresholds (in %)
const int YELLOW_START_PERCENT = 50;
const int RED_START_PERCENT    = 80;

int currentFillPercent = 0;
int currentDistanceCm  = 25;
unsigned long lastTelemetryTime = 0;

// Read distance from HC-SR04
float readDistanceCm(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(4);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH, 30000); // 30ms timeout (~5m)

  // If duration is 0, no object was detected within range (OPEN SPACE / EMPTY BIN)
  if (duration == 0) {
    return 99.0; // Open space
  }

  return (duration * 0.0343 / 2.0);
}

// Convert distance to fill percentage
int distanceToFillPercent(float distanceCm) {
  if (distanceCm >= EMPTY_DISTANCE_CM) return 0;
  if (distanceCm <= FULL_DISTANCE_CM)  return 100;
  
  float fill = ((EMPTY_DISTANCE_CM - distanceCm) / (EMPTY_DISTANCE_CM - FULL_DISTANCE_CM)) * 100.0;
  return (int)constrain(fill, 0, 100);
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
void sendTelemetry(int fill, int dist) {
  String statusStr = "NORMAL";
  if (fill >= RED_START_PERCENT) statusStr = "FULL";
  else if (fill >= YELLOW_START_PERCENT) statusStr = "HALF_FULL";

  String packet = "DATA," + String(fill) + "," + String(dist) + ",N/A," + statusStr;

  espSerial.println(packet); // Sent to ESP32 Pin 16 (RX2)
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

  Serial.println(F("Dustbin 2 Ready (Continuous Stream)"));
  updateIndicators(0);
}

void loop() {
  float dist = readDistanceCm(LEVEL_TRIG_PIN, LEVEL_ECHO_PIN);

  // If open space / nothing in front, treat as empty (25cm)
  if (dist > EMPTY_DISTANCE_CM) {
    currentDistanceCm  = (int)EMPTY_DISTANCE_CM;
    currentFillPercent = 0;
  } else {
    currentDistanceCm  = (int)dist;
    currentFillPercent = distanceToFillPercent(dist);
  }

  // Always update LEDs
  updateIndicators(currentFillPercent);

  // Send telemetry continuously every 300ms so updates are INSTANT
  unsigned long now = millis();
  if (now - lastTelemetryTime >= 300) {
    lastTelemetryTime = now;
    sendTelemetry(currentFillPercent, currentDistanceCm);
  }

  delay(60);
}
