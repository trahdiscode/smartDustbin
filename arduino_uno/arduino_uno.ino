#include <Servo.h>
#include <SoftwareSerial.h>

// Communication to ESP32 RX2 (Pin 10 is TX to ESP32 RX2)
SoftwareSerial espSerial(11, 10); // RX (unused), TX (Pin 10)

// ==================== PIN CONFIGURATION ====================
const int OBJECT_TRIG_PIN = 2; // Hand detection sensor
const int OBJECT_ECHO_PIN = 3;

const int LEVEL_TRIG_PIN  = 4; // Trash fill-level sensor
const int LEVEL_ECHO_PIN  = 5;

const int GREEN_LED_PIN   = 6;
const int YELLOW_LED_PIN  = 7;
const int RED_LED_PIN     = 8;

const int SERVO_PIN       = 9;

// ==================== SETTINGS ====================
const int HAND_DETECT_CM       = 20;

// Angles tuned to prevent mechanical gear and hinge strain:
const int LID_CLOSED_ANGLE     = 10; // Relaxes bottom end-stop
const int LID_OPEN_ANGLE       = 80; // Relaxes top hinge limit (prevents shaking)
const int LID_OPEN_TIME_MS     = 3000;

// Fill-level calibration (16 cm height)
const float DUSTBIN_HEIGHT_CM  = 16.0;

// Fill thresholds (in %)
const int YELLOW_START_PERCENT = 50; // 8 cm trash fillness (distance <= 8 cm)
const int RED_START_PERCENT    = 75; // 12 cm trash fillness (distance <= 4 cm)

Servo lidServo;

int lastFillPercent = 0;
float lastLevelDistance = 16.0;
String lidState = "CLOSED";

// ======================================================
// READ DISTANCE FROM HC-SR04 (WITH TIMEOUT FILTER)
// ======================================================
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

// ======================================================
// CONVERT DISTANCE TO FILL PERCENTAGE (16 cm Dustbin)
// ======================================================
int distanceToFillPercent(float distanceCm) {
  if (distanceCm >= DUSTBIN_HEIGHT_CM) return 0;
  if (distanceCm <= 0) return 100;
  
  float fill = ((DUSTBIN_HEIGHT_CM - distanceCm) / DUSTBIN_HEIGHT_CM) * 100.0;
  return (int)constrain(fill, 0, 100);
}

// ======================================================
// UPDATE STATUS LEDS
// ======================================================
void updateIndicators(int fillPercent) {
  if (fillPercent >= RED_START_PERCENT) {
    // Fill >= 75% (Trash 12 to 16 cm): RED LED
    digitalWrite(GREEN_LED_PIN, LOW);
    digitalWrite(YELLOW_LED_PIN, LOW);
    digitalWrite(RED_LED_PIN, HIGH);
  } else if (fillPercent >= YELLOW_START_PERCENT) {
    // Fill 50% to 74% (Trash 8 to 12 cm): ORANGE/YELLOW LED
    digitalWrite(GREEN_LED_PIN, LOW);
    digitalWrite(YELLOW_LED_PIN, HIGH);
    digitalWrite(RED_LED_PIN, LOW);
  } else {
    // Fill < 50% (Trash 0 to 8 cm): GREEN LED
    digitalWrite(GREEN_LED_PIN, HIGH);
    digitalWrite(YELLOW_LED_PIN, LOW);
    digitalWrite(RED_LED_PIN, LOW);
  }
}

// ======================================================
// SEND TELEMETRY TO ESP32 & PC SERIAL
// ======================================================
void sendTelemetry() {
  String statusStr = "NORMAL";
  if (lastFillPercent >= RED_START_PERCENT) statusStr = "FULL";
  else if (lastFillPercent >= YELLOW_START_PERCENT) statusStr = "HALF_FULL";

  String packet = "DATA," + String(lastFillPercent) + "," + 
                  String(lastLevelDistance > 0 ? (int)lastLevelDistance : 16) + "," + 
                  lidState + "," + 
                  statusStr;

  espSerial.println(packet); // To ESP32 Wi-Fi server
  Serial.println(packet);    // To PC Serial Monitor
}

// ======================================================
// SMOOTH SERVO MOTION (PREVENTS JITTER & POWER DIPS)
// ======================================================
void smoothMove(int fromAngle, int toAngle, int stepDelayMs) {
  lidServo.attach(SERVO_PIN);
  if (fromAngle < toAngle) {
    for (int pos = fromAngle; pos <= toAngle; pos++) {
      lidServo.write(pos);
      delay(stepDelayMs);
    }
  } else {
    for (int pos = fromAngle; pos >= toAngle; pos--) {
      lidServo.write(pos);
      delay(stepDelayMs);
    }
  }
}

// ======================================================
// OPEN AND CLOSE CYCLE
// ======================================================
void openLidThenClose() {
  lidState = "OPEN";
  sendTelemetry(); // Push "OPEN" immediately to cloud!

  // Smooth open from 10 deg to 80 deg
  smoothMove(LID_CLOSED_ANGLE, LID_OPEN_ANGLE, 12);
  lidServo.detach(); // Relax motor in open position

  // Hold open for 3 seconds, keeping cloud updated
  unsigned long startHold = millis();
  while (millis() - startHold < LID_OPEN_TIME_MS) {
    sendTelemetry();
    delay(200);
  }

  // Smooth close from 80 deg back to 10 deg
  smoothMove(LID_OPEN_ANGLE, LID_CLOSED_ANGLE, 15);
  lidServo.detach(); // Relax motor in closed position

  lidState = "CLOSED";
  sendTelemetry(); // Push "CLOSED" immediately to cloud!
}

void setup() {
  Serial.begin(9600);
  espSerial.begin(9600);

  pinMode(OBJECT_TRIG_PIN, OUTPUT);
  pinMode(OBJECT_ECHO_PIN, INPUT);
  pinMode(LEVEL_TRIG_PIN, OUTPUT);
  pinMode(LEVEL_ECHO_PIN, INPUT);

  pinMode(GREEN_LED_PIN, OUTPUT);
  pinMode(YELLOW_LED_PIN, OUTPUT);
  pinMode(RED_LED_PIN, OUTPUT);

  // Initial servo calibration to closed position
  lidServo.attach(SERVO_PIN);
  lidServo.write(LID_CLOSED_ANGLE);
  delay(400);
  lidServo.detach(); // Relax motor immediately

  digitalWrite(GREEN_LED_PIN, LOW);
  digitalWrite(YELLOW_LED_PIN, LOW);
  digitalWrite(RED_LED_PIN, LOW);

  sendTelemetry();
  Serial.println(F("================================="));
  Serial.println(F("   SMART DUSTBIN 1 INITIALIZED   "));
  Serial.println(F("================================="));
}

// ======================================================
// MAIN LOOP
// ======================================================
void loop() {
  // 1. SENSE
  float objectDistance = readDistanceCm(OBJECT_TRIG_PIN, OBJECT_ECHO_PIN);
  delay(40);
  float levelDistance  = readDistanceCm(LEVEL_TRIG_PIN, LEVEL_ECHO_PIN);

  // 2. DECIDE: Measure trash fill level ONLY when lid is resting CLOSED
  if (lidState == "CLOSED" && levelDistance > 1 && levelDistance <= 50) {
    lastLevelDistance = levelDistance;
    lastFillPercent   = distanceToFillPercent(levelDistance);
  } else if (levelDistance > 50 || levelDistance < 0) {
    lastLevelDistance = 16.0;
    lastFillPercent   = 0;
  }

  // 3. ACT: Update status LEDs
  updateIndicators(lastFillPercent);

  // 4. PERIODIC TELEMETRY: Keep dashboard refreshed
  sendTelemetry();

  // 5. LID TRIGGER (Hand detected)
  if (objectDistance > 0 && objectDistance <= HAND_DETECT_CM) {
    delay(40);
    float confirmDist = readDistanceCm(OBJECT_TRIG_PIN, OBJECT_ECHO_PIN);
    if (confirmDist > 0 && confirmDist <= HAND_DETECT_CM) {
      openLidThenClose();
    }
  }

  delay(200);
}
