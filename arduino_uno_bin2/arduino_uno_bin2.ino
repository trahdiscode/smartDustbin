// ====================================================================
// SMART DUSTBIN 2 (BIN-002) - ARDUINO UNO FIRMWARE
// 
// DUSTBIN CALIBRATION (Height: 16 cm):
// - Distance 16 cm down to 8 cm (Trash depth 0 to 8 cm / < 50%): GREEN LED
// - Distance 8 cm down to 4 cm (Trash depth 8 to 12 cm / 50% to 74%): ORANGE/YELLOW LED
// - Distance < 4 cm (Trash depth 12 to 16 cm / >= 75%): RED LED
// 
// PINS:
// - Sensor: Trig -> Pin 4, Echo -> Pin 5
// - LEDs: Green -> Pin 7, Yellow/Orange -> Pin 8, Red -> Pin 9
// - Telemetry: TX -> Pin 10 (to ESP32 Pin 16 / RX2)
// ====================================================================

#include <SoftwareSerial.h>

// Communication to ESP32 Pin 16 (RX2)
SoftwareSerial espSerial(11, 10); // RX (Pin 11 unused), TX (Pin 10)

// ==================== PIN CONFIGURATION ====================
const int LEVEL_TRIG_PIN  = 4; // Trash fill-level sensor Trigger
const int LEVEL_ECHO_PIN  = 5; // Trash fill-level sensor Echo

const int GREEN_LED_PIN   = 7;
const int YELLOW_LED_PIN  = 8; // Yellow / Orange LED
const int RED_LED_PIN     = 9;

// ==================== CALIBRATION (in cm) ====================
const float DUSTBIN_HEIGHT_CM = 16.0; // Total height: 16 cm

// Fill level percentage thresholds
const int YELLOW_START_PERCENT = 50; // 8 cm trash fillness (distance <= 8 cm)
const int RED_START_PERCENT    = 75; // 12 cm trash fillness (distance <= 4 cm)

int lastFillPercent = 0;
int lastLevelDistance = 16;

// Read distance with filtered timing
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

// Convert distance to fill percentage for a 16 cm bin
int distanceToFillPercent(float distanceCm) {
  if (distanceCm >= DUSTBIN_HEIGHT_CM) return 0;
  if (distanceCm <= 0) return 100;
  
  float fill = ((DUSTBIN_HEIGHT_CM - distanceCm) / DUSTBIN_HEIGHT_CM) * 100.0;
  return (int)constrain(fill, 0, 100);
}

// Update Traffic LEDs based on the user's exact thresholds
void updateIndicators(int fillPercent) {
  if (fillPercent >= RED_START_PERCENT) {
    // Fill >= 75% (Trash 12 cm to 16 cm / Distance < 4 cm): RED LED
    digitalWrite(GREEN_LED_PIN, LOW);
    digitalWrite(YELLOW_LED_PIN, LOW);
    digitalWrite(RED_LED_PIN, HIGH);
  } else if (fillPercent >= YELLOW_START_PERCENT) {
    // Fill 50% to 74% (Trash 8 cm to 12 cm / Distance 4 to 8 cm): ORANGE/YELLOW LED
    digitalWrite(GREEN_LED_PIN, LOW);
    digitalWrite(YELLOW_LED_PIN, HIGH);
    digitalWrite(RED_LED_PIN, LOW);
  } else {
    // Fill < 50% (Trash 0 to 8 cm / Distance 8 to 16 cm): GREEN LED
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
  Serial.println(F("Dustbin 2 Initialized (16cm Height Calibrated)"));
}

void loop() {
  // SENSE: Read distance from HC-SR04
  float levelDistance = readDistanceCm(LEVEL_TRIG_PIN, LEVEL_ECHO_PIN);

  // DECIDE: Valid echo within dustbin range
  if (levelDistance > 1 && levelDistance <= 50) {
    lastLevelDistance = (int)levelDistance;
    lastFillPercent   = distanceToFillPercent(levelDistance);
  } else if (levelDistance > 50 || levelDistance < 0) {
    // Empty bin / open space
    lastLevelDistance = 16;
    lastFillPercent   = 0;
  }

  // ACT: Update LEDs (Green / Orange / Red)
  updateIndicators(lastFillPercent);

  // TELEMETRY: Send update to ESP32 & cloud
  sendTelemetry();

  delay(200); // 5Hz sampling rate
}
