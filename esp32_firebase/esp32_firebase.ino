#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>

// ==========================================
// 1. WI-FI CONFIGURATION (Mobile Hotspot)
// ==========================================
const char* WIFI_SSID = "Nothing Phone(4a)";
const char* WIFI_PASS = "hh676767";

// ==========================================
// 2. FIREBASE REALTIME DATABASE URL
// ==========================================
const char* FIREBASE_HOST = "https://parkos1-default-rtdb.firebaseio.com";

// ==========================================
// 3. HARDWARE SERIAL 2 (RX2 = GPIO 16 from Arduino Pin 10)
// ==========================================
#define RXD2 16
#define TXD2 17

int fillPercent = 0;
int trashDistance = 0;
String lidStatus = "CLOSED";
String binStatus = "NORMAL";

unsigned long lastFirebasePush = 0;
bool stateChanged = false;

// Function to push live telemetry to Firebase
void sendToFirebase(int fill, int dist, String lid, String status) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(F("[Wi-Fi] Reconnecting..."));
    WiFi.reconnect();
    return;
  }

  WiFiClientSecure client;
  client.setInsecure(); // Allows fast HTTPS without needing root certificates

  HTTPClient http;
  String endpoint = String(FIREBASE_HOST) + "/bins/BIN-001.json";

  http.begin(client, endpoint);
  http.addHeader("Content-Type", "application/json");

  // Construct JSON payload
  String jsonPayload = "{";
  jsonPayload += "\"fill\":" + String(fill) + ",";
  jsonPayload += "\"dist\":" + String(dist) + ",";
  jsonPayload += "\"lid\":\"" + lid + "\",";
  jsonPayload += "\"status\":\"" + status + "\"";
  jsonPayload += "}";

  // PATCH updates the record in real time
  int httpResponseCode = http.PATCH(jsonPayload);

  if (httpResponseCode > 0) {
    Serial.printf("[Firebase] 🟢 Sent! Code: %d -> %s\n", httpResponseCode, jsonPayload.c_str());
  } else {
    Serial.printf("[Firebase] 🔴 Failed, error code: %d\n", httpResponseCode);
  }

  http.end();
}

void setup() {
  Serial.begin(115200);

  // Serial2 from Arduino Uno (GPIO 16) at 9600 baud
  Serial2.begin(9600, SERIAL_8N1, RXD2, TXD2);

  Serial.println(F("\n=================================="));
  Serial.println(F("  ESP32 -> Firebase Cloud Bridge"));
  Serial.println(F("=================================="));

  // Connect to Mobile Hotspot
  Serial.print(F("Connecting to Hotspot: "));
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  int timeout = 0;
  while (WiFi.status() != WL_CONNECTED && timeout < 30) {
    delay(500);
    Serial.print(".");
    timeout++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(F("\n[Wi-Fi] Connected successfully!"));
    Serial.print(F("[Wi-Fi] IP Address: "));
    Serial.println(WiFi.localIP());
  } else {
    Serial.println(F("\n[Wi-Fi] Connection failed. Please check if Mobile Hotspot is turned ON!"));
  }
}

void loop() {
  // Read incoming packet from Arduino UNO: "DATA,fill,dist,lidState,status"
  if (Serial2.available()) {
    String line = Serial2.readStringUntil('\n');
    line.trim();

    if (line.startsWith("DATA,")) {
      int c1 = line.indexOf(',');
      int c2 = line.indexOf(',', c1 + 1);
      int c3 = line.indexOf(',', c2 + 1);
      int c4 = line.indexOf(',', c3 + 1);

      if (c1 > 0 && c2 > 0 && c3 > 0 && c4 > 0) {
        int newFill   = line.substring(c1 + 1, c2).toInt();
        int newDist   = line.substring(c2 + 1, c3).toInt();
        String newLid = line.substring(c3 + 1, c4);
        String newStatus = line.substring(c4 + 1);

        // If the lid opens/closes or fill level changes, flag for immediate update
        if (newLid != lidStatus || newFill != fillPercent) {
          stateChanged = true;
        }

        fillPercent   = newFill;
        trashDistance = newDist;
        lidStatus     = newLid;
        binStatus     = newStatus;
      }
    }
  }

  // Push to Firebase:
  // 1. Instantly if state changed (e.g. lid opened/closed)
  // 2. OR at least once every 3 seconds as a heartbeat
  unsigned long now = millis();
  if (stateChanged || (now - lastFirebasePush >= 3000)) {
    lastFirebasePush = now;
    stateChanged = false;

    sendToFirebase(fillPercent, trashDistance, lidStatus, binStatus);
  }
}
