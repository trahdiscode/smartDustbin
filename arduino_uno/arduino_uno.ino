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

// Fill-level calibration (in cm)
const float EMPTY_DISTANCE_CM  = 20.0;
const float FULL_DISTANCE_CM   = 4.0;

// Fill thresholds (in %)
const int YELLOW_START_PERCENT = 50;
const int RED_START_PERCENT    = 80;

Servo lidServo;

int lastFillPercent = 0;
float lastLevelDistance = 0;
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
// CONVERT DISTANCE TO FILL PERCENTAGE
// ======================================================
int distanceToFillPercent(float distanceCm) {
  float fill = ((EMPTY_DISTANCE_CM - distanceCm) / (EMPTY_DISTANCE_CM - FULL_DISTANCE_CM)) * 100.0;
  if (fill < 0)   fill = 0;
  if (fill > 100) fill = 100;
  return (int)fill;
}

// ======================================================
// UPDATE STATUS LEDS
// ======================================================
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

// ======================================================
// SEND TELEMETRY TO ESP32 & PC SERIAL
// ======================================================
void sendTelemetry() {
  String statusStr = "NORMAL";
  if (lastFillPercent >= RED_START_PERCENT) statusStr = "FULL";
  else if (lastFillPercent >= YELLOW_START_PERCENT) statusStr = "HALF_FULL";

  String packet = "DATA," + String(lastFillPercent) + "," + 
                  String(lastLevelDistance > 0 ? (int)lastLevelDistance : 0) + "," + 
                  lidState + "," + 
                  statusStr;

  espSerial.println(packet); // To ESP32 Wi-Fi server
  Serial.println(packet);    // To PC Serial Monitor
}

// ======================================================
// SMOOTH, JITTER-FREE LID MOTION
// ======================================================
void openLidThenClose() {
  // 1. Immediately report OPEN to dashboard
  lidState = "OPEN";
  sendTelemetry();
  Serial.println("Lid: OPENING");

  // Attach and sweep smoothly open
  lidServo.attach(SERVO_PIN);
  for (int pos = LID_CLOSED_ANGLE; pos <= LID_OPEN_ANGLE; pos += 2) {
    lidServo.write(pos);
    delay(15);
  }

  // DETACH AT TOP: Kills all buzzing and shaking while waiting open!
  lidServo.detach();

  // Hold open for 3 seconds while continuously reporting OPEN
  for (int i = 0; i < 6; i++) {
    delay(500);
    sendTelemetry();
  }

  // 2. Re-attach to sweep smoothly closed
  lidServo.attach(SERVO_PIN);
  Serial.println("Lid: CLOSING");
  for (int pos = LID_OPEN_ANGLE; pos >= LID_CLOSED_ANGLE; pos -= 2) {
    lidServo.write(pos);
    delay(15);
  }
  delay(200);

  // DETACH AT BOTTOM: Kills all buzzing and shaking while closed!
  lidServo.detach();

  // 3. Immediately report CLOSED to dashboard
  lidState = "CLOSED";
  sendTelemetry();
}

// ======================================================
// SETUP
// ======================================================
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
  Serial.println(F("   SMART DUSTBIN STABILIZED"));
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
  if (lidState == "CLOSED" && levelDistance > 0 && levelDistance < 100) {
    lastLevelDistance = levelDistance;
    lastFillPercent   = distanceToFillPercent(levelDistance);
  }

  // 3. ACT: Update status LEDs
  updateIndicators(lastFillPercent);

  // 4. PERIODIC TELEMETRY: Keep dashboard refreshed every 200ms
  sendTelemetry();

  // 5. LID TRIGGER (Hand detected with noise confirmation)
  if (objectDistance > 0 && objectDistance <= HAND_DETECT_CM) {
    delay(40);
    float confirmDist = readDistanceCm(OBJECT_TRIG_PIN, OBJECT_ECHO_PIN);
    if (confirmDist > 0 && confirmDist <= HAND_DETECT_CM) {
      openLidThenClose();
    }
  }

  delay(200);
}
