// ====================================================================
// SMART DUSTBIN 2 (BIN-002) - ESP32 CLOUD BRIDGE
// Reads from Arduino Uno (Pin 10 -> ESP32 GPIO 16) and streams to Firebase
// Target: /bins/BIN-002.json
// ====================================================================

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

// Target node for Dustbin 2:
const char* FIREBASE_PATH = "/bins/BIN-002.json";

// ==========================================
// 3. HARDWARE SERIAL 2 (RX2 = GPIO 16 from Arduino Pin 10)
// ==========================================
#define RXD2 16
#define TXD2 17

int fillPercent = 0;
int trashDistance = 0;
String lidStatus = "N/A";
String binStatus = "NORMAL";

unsigned long lastFirebasePush = 0;
unsigned long lastHeartbeat = 0;

WiFiClientSecure client;
HTTPClient http;

void sendToFirebase(int fill, int dist, String lid, String status) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(F("[Wi-Fi] Not connected! Reconnecting..."));
    WiFi.disconnect();
    WiFi.reconnect();
    return;
  }

  String endpoint = String(FIREBASE_HOST) + String(FIREBASE_PATH);

  http.begin(client, endpoint);
  http.setReuse(true); // Keep HTTPS connection open
  http.addHeader("Content-Type", "application/json");

  // Construct JSON payload
  String jsonPayload = "{";
  jsonPayload += "\"fill\":" + String(fill) + ",";
  jsonPayload += "\"dist\":" + String(dist) + ",";
  jsonPayload += "\"lid\":\"" + lid + "\",";
  jsonPayload += "\"status\":\"" + status + "\"";
  jsonPayload += "}";

  int httpResponseCode = http.PATCH(jsonPayload);

  if (httpResponseCode > 0) {
    Serial.printf("[Firebase BIN-002] 🟢 Sent! Code: %d -> %s\n", httpResponseCode, jsonPayload.c_str());
  } else {
    Serial.printf("[Firebase BIN-002] 🔴 Error: %d\n", httpResponseCode);
    http.end();
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  // Serial2 from Arduino Uno Pin 10
  Serial2.begin(9600, SERIAL_8N1, RXD2, TXD2);
  Serial2.setTimeout(20);

  client.setInsecure(); // Fast SSL handshake

  Serial.println();
  Serial.println(F("=========================================="));
  Serial.println(F("  ESP32 Cloud Streamer - DUSTBIN 2 (BIN-002)"));
  Serial.println(F("=========================================="));
  Serial.printf("Connecting to Wi-Fi: '%s' ...\n", WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 35) {
    delay(400);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println(F("[Wi-Fi] 🟢 CONNECTED SUCCESSFULLY!"));
    Serial.print(F("[Wi-Fi] IP Address: "));
    Serial.println(WiFi.localIP());

    // Push initial status to /bins/BIN-002.json
    sendToFirebase(fillPercent, trashDistance, lidStatus, binStatus);
  } else {
    Serial.println();
    Serial.println(F("[Wi-Fi] 🔴 CONNECTION FAILED! Check Hotspot 2.4 GHz setting."));
  }
}

void loop() {
  bool stateChanged = false;

  // Read packet from Arduino Uno: "DATA,fill,dist,lid,status"
  if (Serial2.available()) {
    String line = Serial2.readStringUntil('\n');
    line.trim();

    if (line.length() > 0) {
      Serial.printf("[Arduino Serial2 In] %s\n", line.c_str());
    }

    if (line.startsWith("DATA,")) {
      int c1 = line.indexOf(',');
      int c2 = line.indexOf(',', c1 + 1);
      int c3 = line.indexOf(',', c2 + 1);
      int c4 = line.indexOf(',', c3 + 1);

      if (c1 > 0 && c2 > 0 && c3 > 0 && c4 > 0) {
        int newFill      = line.substring(c1 + 1, c2).toInt();
        int newDist      = line.substring(c2 + 1, c3).toInt();
        String newLid    = line.substring(c3 + 1, c4);
        String newStatus = line.substring(c4 + 1);

        if (newFill != fillPercent || abs(newDist - trashDistance) >= 2) {
          stateChanged = true;
          Serial.printf("[BIN-002 Change] Fill: %d%% -> %d%% | Dist: %dcm -> %dcm\n",
                        fillPercent, newFill, trashDistance, newDist);
        }

        fillPercent   = newFill;
        trashDistance = newDist;
        lidStatus     = newLid;
        binStatus     = newStatus;
      }
    }
  }

  unsigned long now = millis();

  // Send immediately on change, or every 3 seconds as heartbeat
  if (stateChanged || (now - lastFirebasePush >= 3000)) {
    lastFirebasePush = now;
    sendToFirebase(fillPercent, trashDistance, lidStatus, binStatus);
  }

  // Periodic heartbeat in Serial Monitor
  if (now - lastHeartbeat >= 5000) {
    lastHeartbeat = now;
    if (WiFi.status() == WL_CONNECTED) {
      Serial.printf("[BIN-002 Heartbeat] Wi-Fi: OK | Fill=%d%%, Dist=%dcm\n", fillPercent, trashDistance);
    } else {
      Serial.println(F("[BIN-002 Heartbeat] Wi-Fi: Disconnected (reconnecting...)"));
      WiFi.reconnect();
    }
  }
}
