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
unsigned long lastHeartbeat = 0;

// Persistent HTTP client for sub-100ms updates
WiFiClientSecure client;
HTTPClient http;

void sendToFirebase(int fill, int dist, String lid, String status) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(F("[Wi-Fi] Not connected! Trying to reconnect..."));
    WiFi.disconnect();
    WiFi.reconnect();
    return;
  }

  String endpoint = String(FIREBASE_HOST) + "/bins/BIN-001.json";

  http.begin(client, endpoint);
  http.setReuse(true); // Keeps SSL session open for instant low-latency pushes
  http.addHeader("Content-Type", "application/json");

  // Construct JSON payload
  String jsonPayload = "{";
  jsonPayload += "\"fill\":" + String(fill) + ",";
  jsonPayload += "\"dist\":" + String(dist) + ",";
  jsonPayload += "\"lid\":\"" + lid + "\",";
  jsonPayload += "\"status\":\"" + status + "\"";
  jsonPayload += "}";

  // Send PATCH
  int httpResponseCode = http.PATCH(jsonPayload);

  if (httpResponseCode > 0) {
    Serial.printf("[Firebase] 🟢 Sent! Code: %d -> %s\n", httpResponseCode, jsonPayload.c_str());
  } else {
    Serial.printf("[Firebase] 🔴 Error: %d (resetting connection)\n", httpResponseCode);
    http.end(); // Reset on error
  }
}

void setup() {
  // Start PC Serial Monitor
  Serial.begin(115200);
  delay(1000); // Give Serial Monitor 1 second to connect

  // Serial2 from Arduino Uno at 9600 baud with ultra-short 15ms timeout
  Serial2.begin(9600, SERIAL_8N1, RXD2, TXD2);
  Serial2.setTimeout(20);

  client.setInsecure(); // Fast HTTPS handshake

  Serial.println();
  Serial.println(F("=========================================="));
  Serial.println(F("  ESP32 Smart Dustbin Streamer Started!"));
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

    // Send initial boot state
    sendToFirebase(fillPercent, trashDistance, lidStatus, binStatus);
  } else {
    Serial.println();
    Serial.println(F("[Wi-Fi] 🔴 CONNECTION FAILED!"));
    Serial.println(F("Tip: On your Nothing Phone hotspot settings:"));
    Serial.println(F("     Turn ON 'Extend compatibility' (enables 2.4 GHz)"));
  }
}

void loop() {
  bool stateChanged = false;

  // Read incoming packet from Arduino UNO: "DATA,fill,dist,lidState,status"
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

        // INSTANT TRIGGER: If lid opened/closed or fill changed, push immediately!
        if (newLid != lidStatus || newFill != fillPercent || abs(newDist - trashDistance) >= 2) {
          stateChanged = true;
          Serial.printf("[State Change] Lid: %s -> %s | Fill: %d%% -> %d%%\n",
                        lidStatus.c_str(), newLid.c_str(), fillPercent, newFill);
        }

        fillPercent   = newFill;
        trashDistance = newDist;
        lidStatus     = newLid;
        binStatus     = newStatus;
      }
    }
  }

  unsigned long now = millis();

  // Push instantly on state change, or every 3 seconds as a heartbeat
  if (stateChanged || (now - lastFirebasePush >= 3000)) {
    lastFirebasePush = now;
    sendToFirebase(fillPercent, trashDistance, lidStatus, binStatus);
  }

  // Periodic status heartbeat on USB monitor so user knows ESP32 is running
  if (now - lastHeartbeat >= 5000) {
    lastHeartbeat = now;
    if (WiFi.status() == WL_CONNECTED) {
      Serial.printf("[ESP32 Heartbeat] Wi-Fi: OK | Current: Fill=%d%%, Lid=%s, Dist=%dcm\n",
                    fillPercent, lidStatus.c_str(), trashDistance);
    } else {
      Serial.println(F("[ESP32 Heartbeat] Wi-Fi: Disconnected (reconnecting...)"));
      WiFi.reconnect();
    }
  }
}
