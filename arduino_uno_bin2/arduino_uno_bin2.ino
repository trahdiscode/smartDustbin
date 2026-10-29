// ====================================================================
// SMART DUSTBIN 2 (BIN-002) - ARDUINO UNO FIRMWARE (V2 - ULTRA RESPONSIVE)
// Configuration: Fill Level Sensor ONLY (HC-SR04)
// Anti-lockup HC-SR04 driver + Immediate distance change detection
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
// Empty distance: when bin has no trash (e.g., 30 cm)
// Full distance: when trash is near top (e.g., 4 cm)
const float EMPTY_DISTANCE_CM  = 30.0; 
const float FULL_DISTANCE_CM   = 4.0;  

// Thresholds for status
const int YELLOW_START_PERCENT = 50;
const int RED_START_PERCENT    = 80;

int lastFillPercent = 0;
int lastLevelDistance = 0;
unsigned long lastTelemetryTime = 0;

// Read distance with anti-lockup protection
float readDistanceCm(int trigPin, int echoPin) {
  pinMode(trigPin, OUTPUT);
  digitalWrite(trigPin, LOW);
  delayMicroseconds(4);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  pinMode(echoPin, INPUT);
  long duration = pulseIn(echoPin, HIGH, 35000); // 35ms timeout (~6m)

  if (duration == 0) {
    // HC-SR04 anti-hang reset
    pinMode(echoPin, OUTPUT);
    digitalWrite(echoPin, LOW);
    delayMicroseconds(20);
    pinMode(echoPin, INPUT);
    return -1;
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

  Serial.println(F("Dustbin 2 (BIN-002) Ready"));
  delay(300);
}

void loop() {
  float dist = readDistanceCm(LEVEL_TRIG_PIN, LEVEL_ECHO_PIN);

  if (dist > 0 && dist <= 200) {
    int currentDist = (int)dist;
    int currentFill = distanceToFillPercent(dist);

    // If DISTANCE changes by 2cm or more, or fill changes -> SEND IMMEDIATELY!
    if (abs(currentDist - lastLevelDistance) >= 2 || currentFill != lastFillPercent) {
      lastLevelDistance = currentDist;
      lastFillPercent = currentFill;
      updateIndicators(lastFillPercent);
      sendTelemetry(lastFillPercent, lastLevelDistance);
      lastTelemetryTime = millis();
    }
  }

  // Periodic heartbeat every 2 seconds
  if (millis() - lastTelemetryTime >= 2000) {
    updateIndicators(lastFillPercent);
    sendTelemetry(lastFillPercent, lastLevelDistance);
    lastTelemetryTime = millis();
  }

  delay(100); // Fast 10Hz sampling
}
