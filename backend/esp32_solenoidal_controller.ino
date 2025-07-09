/*
 * ESP32 Solenoidal Door Lock Controller
 * MAC Address: FC:B4:67:F0:44:18
 * 
 * This ESP32 controls the solenoidal door lock for a 3-ESP32 RFID system:
 * - ESP1: Entry RFID Scanner + OLED
 * - ESP2: Door Controller (this device) - controls solenoidal lock
 * - ESP3: Exit RFID Scanner + OLED
 * 
 * Door Logic:
 * - GPIO LOW = Door OPEN (relay activated, solenoid unlocked)
 * - GPIO HIGH = Door CLOSED (relay deactivated, solenoid locked)
 * - Auto-close after 5 seconds
 * 
 * HTTP Endpoints:
 * - POST /unlock_entry - Opens door for entry (5s timeout)
 * - POST /unlock_exit - Opens door for exit (5s timeout)
 * - POST /lock - Closes door immediately
 * - GET /status - Returns door status
 * - GET / - Web interface
 * 
 * Pin Connections:
 * - GPIO23: Relay control (LOW=Open, HIGH=Closed)
 * - GPIO2: Status LED (LOW=Closed, HIGH=Open)
 */

#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>

// WiFi Configuration
const char* ssid = "R&D";
const char* password = "9686940950";

// Hardware Configuration
#define RELAY_PIN 23              // GPIO23 controls the relay
#define STATUS_LED_PIN 2          // Built-in LED for status
#define DOOR_OPEN_TIME 5000       // 5 seconds door open time

// Door States
bool doorOpen = false;            // true = door open, false = door closed
unsigned long doorOpenStartTime = 0;
String lastOperation = "";        // "entry", "exit", or "manual"

// Statistics
unsigned long entryCount = 0;
unsigned long exitCount = 0;
unsigned long manualOperations = 0;
unsigned long totalOperations = 0;
unsigned long systemStartTime = 0;

// Web Server
WebServer server(80);

// Function declarations
void setupHardware();
void connectWiFi();
void setupWebServer();
void registerWithServer();  // New function to register with Flask server
void openDoor(String operation);
void closeDoor();
void updateDoorStatus();
void handleUnlockEntry();
void handleUnlockExit();
void handleLock();
void handleStatus();
void handleRoot();
String getDoorStatusJSON();
String getUptimeString();

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println();
  Serial.println("=== ESP32 Door Lock Controller ===");
  Serial.println("Device: Solenoidal Lock Controller");
  Serial.println("Expected MAC: FC:B4:67:F0:44:18");
  Serial.println("Actual MAC: " + WiFi.macAddress());
  Serial.println("Initializing...");
  
  systemStartTime = millis();
  
  setupHardware();
  connectWiFi();
  setupWebServer();
  registerWithServer();  // Register with Flask server on startup
  
  // Startup indication - flash LED
  for (int i = 0; i < 3; i++) {
    digitalWrite(STATUS_LED_PIN, HIGH);
    delay(200);
    digitalWrite(STATUS_LED_PIN, LOW);
    delay(200);
  }
  
  Serial.println();
  Serial.println("Door Controller Ready!");
  Serial.println("IP Address: " + WiFi.localIP().toString());
  Serial.println("Web Interface: http://" + WiFi.localIP().toString());
  Serial.println();
  Serial.println("API Endpoints:");
  Serial.println("  POST /unlock_entry - Open door for entry");
  Serial.println("  POST /unlock_exit - Open door for exit");
  Serial.println("  POST /lock - Close door immediately");
  Serial.println("  GET /status - Get door status");
  Serial.println("  GET / - Web interface");
  Serial.println();
  Serial.println("Door Logic: GPIO LOW = OPEN, GPIO HIGH = CLOSED");
  Serial.println("Auto-close timer: 5 seconds");
  Serial.println();
}

void loop() {
  server.handleClient();
  updateDoorStatus();
  delay(50);
}

void setupHardware() {
  // Initialize pins
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(STATUS_LED_PIN, OUTPUT);
  
  // Start with door closed (GPIO HIGH)
  closeDoor();
  
  Serial.println("Hardware initialized:");
  Serial.println("  Relay Pin: GPIO" + String(RELAY_PIN) + " (LOW=Open, HIGH=Closed)");
  Serial.println("  Status LED: GPIO" + String(STATUS_LED_PIN));
  Serial.println("  Door initially: CLOSED");
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  Serial.print("Connecting to WiFi: " + String(ssid));
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(1000);
    Serial.print(".");
    attempts++;
    
    // Blink LED while connecting
    digitalWrite(STATUS_LED_PIN, attempts % 2);
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println("WiFi connected successfully!");
    Serial.println("IP: " + WiFi.localIP().toString());
    Serial.println("MAC: " + WiFi.macAddress());
    Serial.println("Signal: " + String(WiFi.RSSI()) + " dBm");
    
    // Flash LED to indicate success
    for (int i = 0; i < 3; i++) {
      digitalWrite(STATUS_LED_PIN, HIGH);
      delay(200);
      digitalWrite(STATUS_LED_PIN, LOW);
      delay(200);
    }
  } else {
    Serial.println();
    Serial.println("WiFi connection FAILED!");
    Serial.println("Check SSID/password and restart device");
    
    // Keep LED on to indicate error
    digitalWrite(STATUS_LED_PIN, HIGH);
  }
}

void setupWebServer() {
  // Door control endpoints
  server.on("/unlock_entry", HTTP_POST, handleUnlockEntry);
  server.on("/unlock_exit", HTTP_POST, handleUnlockExit);
  server.on("/lock", HTTP_POST, handleLock);
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/", HTTP_GET, handleRoot);
  
  // Enable CORS for cross-origin requests
  server.enableCORS(true);
  
  server.begin();
  Serial.println("Web server started on port 80");
}

void registerWithServer() {
  // Register this ESP32 door controller with the Flask server
  Serial.println("Registering with Flask server...");
  
  // Try to find the Flask server on the network
  // We'll try common Pi IP addresses or broadcast
  String serverIPs[] = {
    "192.168.1.100",  // Common Pi IP
    "192.168.1.101", 
    "192.168.1.102",
    "192.168.1.103",
    "192.168.1.104",
    "192.168.1.105"
  };
  
  for (int i = 0; i < 6; i++) {
    String serverIP = serverIPs[i];
    Serial.println("Trying server at: " + serverIP);
    
    WiFiClient client;
    if (client.connect(serverIP.c_str(), 5000)) {
      Serial.println("✅ Flask server found at: " + serverIP);
      Serial.println("Door controller connection established!");
      client.stop();
      return;
    }
    
    delay(500);  // Brief delay between attempts
  }
  
  Serial.println("⚠ Could not find Flask server. Manual registration may be required.");
  Serial.println("Make sure Flask server is running and accessible.");
}

void openDoor(String operation) {
  String upperOperation = operation;
  upperOperation.toUpperCase();
  Serial.println("OPENING DOOR for " + upperOperation);
  
  // Set relay LOW to open door
  digitalWrite(RELAY_PIN, LOW);
  digitalWrite(STATUS_LED_PIN, HIGH); // LED on when door open
  
  doorOpen = true;
  doorOpenStartTime = millis();
  lastOperation = operation;
  
  // Update statistics
  totalOperations++;
  if (operation == "entry") {
    entryCount++;
  } else if (operation == "exit") {
    exitCount++;
  } else {
    manualOperations++;
  }
  
  Serial.println("Door OPENED - auto-close in 5 seconds");
  Serial.println("Stats: Entry=" + String(entryCount) + ", Exit=" + String(exitCount) + ", Manual=" + String(manualOperations));
}

void closeDoor() {
  Serial.println("CLOSING DOOR");
  
  // Set relay HIGH to close door
  digitalWrite(RELAY_PIN, HIGH);
  digitalWrite(STATUS_LED_PIN, LOW); // LED off when door closed
  
  doorOpen = false;
  
  Serial.println("Door CLOSED and secured");
}

void updateDoorStatus() {
  // Auto-close door after 5 seconds
  if (doorOpen) {
    unsigned long currentTime = millis();
    if (currentTime - doorOpenStartTime >= DOOR_OPEN_TIME) {
      closeDoor();
    }
  }
}

void handleUnlockEntry() {
  Serial.println("Received ENTRY unlock request");
  
  openDoor("entry");
  
  // Send response
  String response = getDoorStatusJSON();
  server.send(200, "application/json", response);
  
  Serial.println("ENTRY unlock processed");
}

void handleUnlockExit() {
  Serial.println("Received EXIT unlock request");
  
  openDoor("exit");
  
  // Send response
  String response = getDoorStatusJSON();
  server.send(200, "application/json", response);
  
  Serial.println("EXIT unlock processed");
}

void handleLock() {
  Serial.println("Received manual lock request");
  
  closeDoor();
  
  // Send response
  String response = getDoorStatusJSON();
  server.send(200, "application/json", response);
  
  Serial.println("Manual lock processed");
}

void handleStatus() {
  String response = getDoorStatusJSON();
  server.send(200, "application/json", response);
}

void handleRoot() {
  String html = "<!DOCTYPE html><html><head>";
  html += "<title>ESP32 Door Controller</title>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
  html += "<style>";
  html += "body { font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }";
  html += ".container { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }";
  html += ".status { padding: 15px; margin: 10px 0; border-radius: 5px; font-weight: bold; text-align: center; }";
  html += ".closed { background: #ffebee; color: #c62828; }";
  html += ".open { background: #e8f5e8; color: #2e7d32; }";
  html += "button { background: #2196F3; color: white; border: none; padding: 10px 20px; margin: 5px; border-radius: 5px; cursor: pointer; }";
  html += "button:hover { background: #1976D2; }";
  html += ".danger { background: #f44336 !important; }";
  html += ".stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin: 20px 0; }";
  html += ".stat { background: #e3f2fd; padding: 15px; border-radius: 5px; text-align: center; }";
  html += ".stat-value { font-size: 24px; font-weight: bold; color: #1976d2; }";
  html += ".stat-label { font-size: 12px; color: #666; }";
  html += "</style>";
  html += "</head><body>";
  
  html += "<div class='container'>";
  html += "<h1>ESP32 Door Lock Controller</h1>";
  html += "<p><strong>Device MAC:</strong> " + WiFi.macAddress() + "</p>";
  html += "<p><strong>IP Address:</strong> " + WiFi.localIP().toString() + "</p>";
  html += "<p><strong>Uptime:</strong> " + getUptimeString() + "</p>";
  
  // Door Status
  String statusClass = doorOpen ? "open" : "closed";
  String statusText = doorOpen ? "DOOR OPEN" : "DOOR CLOSED";
  html += "<div class='status " + statusClass + "'>" + statusText;
  
  if (doorOpen) {
    unsigned long timeLeft = DOOR_OPEN_TIME - (millis() - doorOpenStartTime);
    html += "<br>Auto-close in: " + String(timeLeft/1000) + " seconds";
    String upperOperation = lastOperation;
    upperOperation.toUpperCase();
    html += "<br>Last operation: " + upperOperation;
  }
  html += "</div>";
  
  // Statistics
  html += "<div class='stats'>";
  html += "<div class='stat'><div class='stat-value'>" + String(entryCount) + "</div><div class='stat-label'>ENTRIES</div></div>";
  html += "<div class='stat'><div class='stat-value'>" + String(exitCount) + "</div><div class='stat-label'>EXITS</div></div>";
  html += "<div class='stat'><div class='stat-value'>" + String(manualOperations) + "</div><div class='stat-label'>MANUAL</div></div>";
  html += "<div class='stat'><div class='stat-value'>" + String(totalOperations) + "</div><div class='stat-label'>TOTAL</div></div>";
  html += "</div>";
  
  // Manual Controls
  html += "<h2>Manual Control</h2>";
  html += "<button onclick=\"unlockDoor('entry')\">Entry Unlock</button>";
  html += "<button onclick=\"unlockDoor('exit')\">Exit Unlock</button>";
  html += "<button onclick=\"lockDoor()\" class='danger'>Close Door</button>";
  html += "<button onclick=\"getStatus()\">Refresh</button>";
  
  // Hardware Status
  html += "<hr><h2>Hardware Status</h2>";
  html += "<p><strong>Relay Pin (GPIO23):</strong> " + String(digitalRead(RELAY_PIN) == LOW ? "LOW (Door Open)" : "HIGH (Door Closed)") + "</p>";
  html += "<p><strong>Status LED (GPIO2):</strong> " + String(digitalRead(STATUS_LED_PIN) == HIGH ? "ON" : "OFF") + "</p>";
  html += "<p><strong>Door Logic:</strong> GPIO LOW = Open, GPIO HIGH = Closed</p>";
  html += "<p><strong>Auto-close Timer:</strong> 5 seconds</p>";
  
  // API Documentation
  html += "<hr><h2>API Documentation</h2>";
  html += "<h3>Endpoints:</h3>";
  html += "<ul>";
  html += "<li><strong>POST /unlock_entry</strong> - Open door for entry (5s auto-close)</li>";
  html += "<li><strong>POST /unlock_exit</strong> - Open door for exit (5s auto-close)</li>";
  html += "<li><strong>POST /lock</strong> - Close door immediately</li>";
  html += "<li><strong>GET /status</strong> - Get current door status</li>";
  html += "</ul>";
  
  html += "<h3>Usage Examples:</h3>";
  html += "<pre style='background: #f5f5f5; padding: 10px; border-radius: 5px;'>";
  html += "# Open door for entry\n";
  html += "curl -X POST http://" + WiFi.localIP().toString() + "/unlock_entry\n\n";
  html += "# Open door for exit\n";
  html += "curl -X POST http://" + WiFi.localIP().toString() + "/unlock_exit\n\n";
  html += "# Close door immediately\n";
  html += "curl -X POST http://" + WiFi.localIP().toString() + "/lock\n\n";
  html += "# Get door status\n";
  html += "curl http://" + WiFi.localIP().toString() + "/status\n";
  html += "</pre>";
  
  html += "</div>";
  
  // JavaScript for interactive controls
  html += "<script>";
  html += "function unlockDoor(type) {";
  html += "  const endpoint = type === 'entry' ? '/unlock_entry' : '/unlock_exit';";
  html += "  fetch(endpoint, {method: 'POST'})";
  html += "    .then(() => setTimeout(() => location.reload(), 500));";
  html += "}";
  html += "function lockDoor() {";
  html += "  fetch('/lock', {method: 'POST'})";
  html += "    .then(() => setTimeout(() => location.reload(), 500));";
  html += "}";
  html += "function getStatus() { location.reload(); }";
  html += "setInterval(() => { if (!document.hidden) location.reload(); }, 2000);"; // Auto-refresh every 2s
  html += "</script>";
  
  html += "</body></html>";
  
  server.send(200, "text/html", html);
}

String getDoorStatusJSON() {
  DynamicJsonDocument doc(400);
  
  doc["device_type"] = "door_controller";
  doc["mac_address"] = WiFi.macAddress();
  doc["ip_address"] = WiFi.localIP().toString();
  doc["door_open"] = doorOpen;
  doc["door_closed"] = !doorOpen;
  doc["last_operation"] = lastOperation;
  doc["timestamp"] = millis();
  doc["uptime_ms"] = millis() - systemStartTime;
  
  if (doorOpen) {
    unsigned long timeLeft = DOOR_OPEN_TIME - (millis() - doorOpenStartTime);
    doc["time_until_close_ms"] = timeLeft;
    doc["auto_close_timer_ms"] = DOOR_OPEN_TIME;
  }
  
  // Hardware status
  doc["relay_pin_state"] = digitalRead(RELAY_PIN);
  doc["status_led_state"] = digitalRead(STATUS_LED_PIN);
  
  // Statistics
  JsonObject stats = doc.createNestedObject("statistics");
  stats["entry_count"] = entryCount;
  stats["exit_count"] = exitCount;
  stats["manual_operations"] = manualOperations;
  stats["total_operations"] = totalOperations;
  
  String response;
  serializeJson(doc, response);
  return response;
}

String getUptimeString() {
  unsigned long uptime = millis() - systemStartTime;
  unsigned long seconds = uptime / 1000;
  unsigned long minutes = seconds / 60;
  unsigned long hours = minutes / 60;
  unsigned long days = hours / 24;
  
  String result = "";
  if (days > 0) result += String(days) + "d ";
  if (hours % 24 > 0) result += String(hours % 24) + "h ";
  if (minutes % 60 > 0) result += String(minutes % 60) + "m ";
  result += String(seconds % 60) + "s";
  
  return result;
}
