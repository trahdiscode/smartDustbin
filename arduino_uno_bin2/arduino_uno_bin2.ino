// ====================================================================
// SMART DUSTBIN 2 (BIN-002) - ARDUINO UNO FIRMWARE
// Uses the EXACT SAME stable sensing logic as Dustbin 1 (smooth & flicker-free)
// LED Pins: 7 (Green), 8 (Yellow), 9 (Red)
// Sensor Pins: 4 (Trig), 5 (Echo)
// ====================================================================

#include <SoftwareSerial.h>

// Communication to ESP32 Pin 16 (RX2)
SoftwareSerial espSerial(11, 10); // RX (Pin 11 unused), TX (Pin 10)

// ==================== PIN CONFIGURATION ====================
const int LEVEL_TRIG_PIN  = 4; // Trash fill-level sensor Trigger
const int LEVEL_ECHO_PIN  = 5; // Trash fill-level sensor Echo

const int GREEN_LED_PIN   = 7;
const int YELLOW_LED_PIN  = 8;
const int RED_LED_PIN     = 9;

// ==================== CALIBRATION (in cm) ====================
// Exactly tuned for smooth trash monitoring
const float EMPTY_DISTANCE_CM  = 25.0; // Empty depth
const float FULL_DISTANCE_CM   = 4.0;  // Full depth

const int YELLOW_START_PERCENT = 50;
const int RED_START_PERCENT    = 80;

int lastFillPercent = 0;
int lastLevelDistance = 25;

// Read distance with identical timing to Dustbin 1
float readDistanceCm(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH, 25000);
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

  String packet = "DATA," + String(lastFillPercent) + "," + 
                  String(lastLevelDistance) + "," + 
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

  digitalWrite(GREEN_LED_PIN, LOW);
  digitalWrite(YELLOW_LED_PIN, LOW);
  digitalWrite(RED_LED_PIN, LOW);

  sendTelemetry();
  Serial.println(F("Dustbin 2 Initialized"));
}

void loop() {
  // SENSE: Read distance
  float levelDistance = readDistanceCm(LEVEL_TRIG_PIN, LEVEL_ECHO_PIN);

  // DECIDE: Update ONLY on valid echo (identical to Dustbin 1)
  // This filters out all noise and prevents flickering/freezing
  if (levelDistance > 2 && levelDistance <= 100) {
    lastLevelDistance = (int)levelDistance;
    lastFillPercent   = distanceToFillPercent(levelDistance);
  } else if (levelDistance > 100) {
    // Open space / ceiling
    lastLevelDistance = 25;
    lastFillPercent   = 0;
  }

  // ACT: Update LEDs
  updateIndicators(lastFillPercent);

  // TELEMETRY: Send smooth updates
  sendTelemetry();

  delay(200); // 5Hz sampling rate (rock solid)
}
