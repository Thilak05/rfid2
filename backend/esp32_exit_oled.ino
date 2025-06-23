/*
 * ESP32 WROOM RFID Exit Scanner with OLED Display
 * 
 * This ESP32 handles EXIT operations:
 * 1. Scans RFID cards and sends UID to Python server for EXIT
 * 2. Displays messages received from Python server on OLED
 * 3. Python server handles all logic (user verification, database, etc.)
 * 
 * Pin Connections:
 * RFID Reader (Serial):
 *   GND -> GND
 *   VCC -> 3.3V
 *   TXD -> GPIO16 (RX2) - RFID data output
 * 
 * OLED SSD1306 (I2C):
 *   GND -> GND
 *   VCC -> 3.3V
 *   SDA -> GPIO21 (SDA)
 *   SCL -> GPIO22 (SCL)
 */

#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <HardwareSerial.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// WiFi Configuration
const char* ssid = "R&D";
const char* password = "9686940950";

// Python Server Configuration
const char* raspberryPiMAC = "D8:3A:DD:78:01:07"; // Raspberry Pi MAC address
const int pythonServerPort = 5000;             // Flask server port
String pythonServerIP = "";                   // Will be discovered by MAC address

// RFID Serial Configuration (ESP32 has 3 hardware serial ports)
HardwareSerial rfidSerial(2);  // Use Serial2 (GPIO16=RX, GPIO17=TX)
#define RFID_BAUD_RATE 9600

// OLED Configuration (ESP32 default I2C pins)
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define OLED_SDA 21  // Default SDA pin for ESP32
#define OLED_SCL 22  // Default SCL pin for ESP32
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Web Server for receiving OLED messages from Python
WebServer server(80);

// Global variables
String lastRFID = "";
unsigned long lastScanTime = 0;
const unsigned long SCAN_DELAY = 2000; // 2 seconds between scans
bool piFound = false;
unsigned long lastDiscoveryAttempt = 0;
const unsigned long DISCOVERY_INTERVAL = 30000; // 30 seconds

// Function declarations
String discoverPiByMAC();
bool testPythonServer(String ip);
bool pingDevice(String ip);
String getMACFromARP(String ip);
bool verifyPiIdentity(String ip);
void displayMessage(String message);
String getWiFiStatusText(int status);

String getWiFiStatusText(int status) {
  switch(status) {
    case WL_IDLE_STATUS: return "IDLE_STATUS";
    case WL_NO_SSID_AVAIL: return "NO_SSID_AVAIL";
    case WL_SCAN_COMPLETED: return "SCAN_COMPLETED";
    case WL_CONNECTED: return "CONNECTED";
    case WL_CONNECT_FAILED: return "CONNECT_FAILED";
    case WL_CONNECTION_LOST: return "CONNECTION_LOST";
    case WL_DISCONNECTED: return "DISCONNECTED";
    default: return "UNKNOWN(" + String(status) + ")";
  }
}

String discoverPiByMAC() {
  Serial.println("Discovering Raspberry Pi by MAC: " + String(raspberryPiMAC));
  displayMessage("Discovering Pi...\n" + String(raspberryPiMAC));
  
  IPAddress localIP = WiFi.localIP();
  String networkBase = String(localIP[0]) + "." + String(localIP[1]) + "." + String(localIP[2]) + ".";
  
  // First, do a quick scan for Python servers
  Serial.println("Scanning for Flask servers on port " + String(pythonServerPort) + "...");
  
  for (int i = 1; i <= 254; i++) {
    String testIP = networkBase + String(i);
    if (testIP == WiFi.localIP().toString()) continue;
    
    // Check if Flask server is running
    if (testPythonServer(testIP)) {
      Serial.println("Found Flask server at: " + testIP);
      displayMessage("Found server at:\n" + testIP + "\nVerifying...");
      
      // Try to verify this is our Pi by making a test request
      if (verifyPiIdentity(testIP)) {
        Serial.println("Verified Raspberry Pi at: " + testIP);
        return testIP;
      } else {
        Serial.println("Server at " + testIP + " is not our target Pi");
      }
    }
    
    if (i % 25 == 0) {
      displayMessage("Scanning...\n" + testIP + "\nLooking for Flask...");
      yield();
    }
  }
  
  Serial.println("Target Raspberry Pi not found on network");
  return "";
}

bool pingDevice(String ip) {
  // Simple ping test using HTTP connection attempt
  WiFiClient client;
  client.setTimeout(500); // Short timeout for ping
  
  // Try to connect to any common port to see if device exists
  bool connected = client.connect(ip.c_str(), 80) || 
                   client.connect(ip.c_str(), 22) || 
                   client.connect(ip.c_str(), pythonServerPort);
  
  if (connected) {
    client.stop();
    return true;
  }
  return false;
}

String getMACFromARP(String ip) {
  // ESP32 doesn't have direct ARP table access like ESP8266
  // We'll use a workaround by sending a ping and checking WiFi scan results
  // This is a simplified approach - in production you might want to use more sophisticated methods
  
  // First, try to ping the device to populate ARP cache
  WiFiClient client;
  client.setTimeout(100);
  if (client.connect(ip.c_str(), 80) || client.connect(ip.c_str(), 22) || client.connect(ip.c_str(), pythonServerPort)) {
    client.stop();
    delay(10); // Small delay to let ARP populate
  }
  
  // Unfortunately, ESP32 Arduino doesn't provide direct ARP access
  // For now, we'll use a fallback method: check if it's our known Pi MAC by testing the server
  if (testPythonServer(ip)) {
    // If the Python server responds, we'll assume it's the Pi for now
    // This is not perfect but works for most home network scenarios
    return String(raspberryPiMAC);
  }
  
  return ""; // Unable to determine MAC
}

bool verifyPiIdentity(String ip) {
  // Send a test request to verify this is our target Pi and get its MAC
  HTTPClient http;
  WiFiClient client;
  
  // First try the device info endpoint
  String infoUrl = "http://" + ip + ":" + String(pythonServerPort) + "/api/device/info";
  http.begin(client, infoUrl);
  http.setTimeout(3000);
  
  int httpResponseCode = http.GET();
  
  if (httpResponseCode == 200) {
    String response = http.getString();
    http.end();
    
    Serial.println("Device info response: " + response);
    
    // Parse JSON to check MAC address
    if (response.indexOf("\"device_type\":\"Raspberry Pi\"") != -1) {
      // Extract MAC address from JSON response
      int macStart = response.indexOf("\"mac_address\":\"") + 15;
      if (macStart > 14) {
        int macEnd = response.indexOf("\"", macStart);
        if (macEnd > macStart) {
          String deviceMAC = response.substring(macStart, macEnd);
          deviceMAC.toUpperCase();
          String targetMAC = String(raspberryPiMAC);
          targetMAC.toUpperCase();
          
          Serial.println("Device MAC: " + deviceMAC + ", Target MAC: " + targetMAC);
          
          if (deviceMAC == targetMAC) {
            Serial.println("Pi identity verified - MAC address matches!");
            return true;
          } else {
            Serial.println("Pi MAC address does not match target");
            return false;
          }
        }
      }
    }
  }
  
  http.end();
  
  // Fallback: try root endpoint for basic identification
  String url = "http://" + ip + ":" + String(pythonServerPort) + "/";
  http.begin(client, url);
  http.setTimeout(2000);
  
  httpResponseCode = http.GET();
  
  if (httpResponseCode > 0) {
    String response = http.getString();
    http.end();
    
    // Check if response contains expected Flask server content
    if (response.indexOf("RFID Entry System") != -1 || response.indexOf("Flask Server") != -1) {
      Serial.println("Pi identity verified - Flask server responding correctly (fallback method)");
      return true;
    }
  }
  
  http.end();
  return false;
}

bool testPythonServer(String ip) {
  WiFiClient client;
  client.setTimeout(1000);
  
  if (client.connect(ip.c_str(), pythonServerPort)) {
    client.stop();
    return true;
  }
  return false;
}

void setup() {
  // Initialize Serial for debugging (USB)
  Serial.begin(115200);
  delay(1000); // Give serial time to initialize
  
  Serial.println();
  Serial.println("=== ESP32 RFID EXIT System ===");
  Serial.println("Initializing...");
  
  // Initialize RFID Serial2 (GPIO16=RX, GPIO17=TX)
  rfidSerial.begin(RFID_BAUD_RATE, SERIAL_8N1, 16, 17);
  
  // Initialize I2C with default pins for OLED
  Wire.begin(OLED_SDA, OLED_SCL);
  
  // Initialize OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("SSD1306 allocation failed");
    while (1);
  }
  
  displayMessage("ESP32 EXIT\nInitializing...");
  
  // Print WiFi credentials for debugging
  Serial.println("WiFi Configuration:");
  Serial.println("SSID: " + String(ssid));
  Serial.println("Password length: " + String(strlen(password)));
  
  // Connect to WiFi with timeout and better error handling
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  displayMessage("Connecting WiFi...\n" + String(ssid));
  
  int wifiAttempts = 0;
  const int maxWifiAttempts = 30; // 30 seconds timeout
  while (WiFi.status() != WL_CONNECTED && wifiAttempts < maxWifiAttempts) {
    delay(1000);
    wifiAttempts++;
    Serial.print(".");
    Serial.print(" WiFi Status: ");
    Serial.print(WiFi.status());
    Serial.print(" (");
    Serial.print(getWiFiStatusText(WiFi.status()));
    Serial.println(")");
    
    // Update display every 5 seconds
    if (wifiAttempts % 5 == 0) {
      String statusText = getWiFiStatusText(WiFi.status());
      displayMessage("Connecting WiFi...\nAttempt: " + String(wifiAttempts) + "/" + String(maxWifiAttempts) + "\nStatus: " + statusText);
    }
  }
  
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println();
    Serial.println("WiFi connection failed!");
    Serial.println("Final WiFi Status: " + String(WiFi.status()) + " (" + getWiFiStatusText(WiFi.status()) + ")");
    Serial.println("SSID: " + String(ssid));
    Serial.println("Password length: " + String(strlen(password)));
    Serial.println();
    Serial.println("Common fixes:");
    Serial.println("1. Check SSID and password");
    Serial.println("2. Ensure 2.4GHz WiFi (ESP32 doesn't support 5GHz)");
    Serial.println("3. Check WiFi signal strength");
    Serial.println("4. Restart router if needed");
    
    displayMessage("WiFi FAILED!\nSSID: " + String(ssid) + "\nStatus: " + getWiFiStatusText(WiFi.status()));
    while(1) delay(1000); // Stop here if WiFi fails
  }
  
  Serial.println();
  Serial.println("WiFi connected successfully!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
  Serial.print("MAC address: ");
  Serial.println(WiFi.macAddress());
  Serial.print("Signal strength (RSSI): ");
  Serial.println(WiFi.RSSI());
  Serial.print("Connected to SSID: ");
  Serial.println(WiFi.SSID());
  
  // Setup web server for OLED messages
  server.on("/message", HTTP_POST, handleOLEDMessage);
  server.on("/", HTTP_GET, handleRoot);
  server.begin();
  
  // Discover Raspberry Pi by MAC address
  pythonServerIP = discoverPiByMAC();
  if (pythonServerIP.length() > 0) {
    piFound = true;
    displayMessage("EXIT SCANNER\nPi Found: " + pythonServerIP + "\nMAC: " + WiFi.macAddress());
  } else {
    displayMessage("EXIT SCANNER\nPi Not Found\nMAC: " + WiFi.macAddress());
  }
  
  Serial.println("ESP32 RFID EXIT System ready!");
  Serial.println("MAC Address: " + WiFi.macAddress());
}

void loop() {
  // Handle web server requests (for OLED messages)
  server.handleClient();
  
  // Periodically attempt to discover Pi if not found
  if (!piFound) {
    unsigned long currentTime = millis();
    if (currentTime - lastDiscoveryAttempt > DISCOVERY_INTERVAL) {
      lastDiscoveryAttempt = currentTime;
      pythonServerIP = discoverPiByMAC();
      if (pythonServerIP.length() > 0) {
        piFound = true;
        displayMessage("EXIT SCANNER\nPi Found: " + pythonServerIP + "\nMAC: " + WiFi.macAddress());
      }
    }
  }
  
  // Check for RFID cards from serial
  if (rfidSerial.available()) {
    String rfidUID = rfidSerial.readStringUntil('\n');
    rfidUID.trim();
    
    if (rfidUID.length() > 0) {
      // Prevent duplicate scans
      unsigned long currentTime = millis();
      if (currentTime - lastScanTime < SCAN_DELAY) {
        return;
      }
      
      // Prevent duplicate of same card
      if (rfidUID == lastRFID && (currentTime - lastScanTime) < 5000) {
        return;
      }
      
      lastRFID = rfidUID;
      lastScanTime = currentTime;
      
      Serial.println("RFID scanned for EXIT: " + rfidUID);
      
      // Send to Python server for EXIT processing
      sendRFIDToPython(rfidUID);
    }
  }
  
  delay(100);
}

void sendRFIDToPython(String rfidUID) {
  if (!piFound || pythonServerIP.length() == 0) {
    displayMessage("Pi Not Found\nCannot send:\n" + rfidUID);
    Serial.println("Cannot send RFID - Pi not discovered");
    return;
  }
  
  displayMessage("Sending EXIT...\n" + rfidUID);
  
  WiFiClient client;
  HTTPClient http;
  
  // Send RFID to Python Flask server for EXIT
  http.begin(client, "http://" + pythonServerIP + ":" + String(pythonServerPort) + "/scan");
  http.addHeader("Content-Type", "application/json");
  
  // Create JSON payload with MAC address for device identification (EXIT action)
  String deviceMAC = WiFi.macAddress();
  String jsonPayload = "{\"unique_id\":\"" + rfidUID + "\",\"action\":\"exit\",\"device_mac\":\"" + deviceMAC + "\"}";
  
  int httpResponseCode = http.POST(jsonPayload);
  
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println("HTTP Response: " + String(httpResponseCode));
    Serial.println("Response: " + response);
    
    if (httpResponseCode == 200) {
      displayMessage("EXIT Successful\n" + rfidUID);
    } else {
      displayMessage("Server Error\n" + String(httpResponseCode));
    }
  } else {
    Serial.println("HTTP Error: " + String(httpResponseCode));
    displayMessage("Connection Failed\nCheck server");
    // Mark Pi as lost
    piFound = false;
  }
  
  http.end();
  
  // Return to ready state after 2 seconds
  delay(2000);
  if (piFound) {
    displayMessage("EXIT SCANNER\nPi: " + pythonServerIP + "\nMAC: " + WiFi.macAddress());
  } else {
    displayMessage("EXIT SCANNER\nPi Not Found\nMAC: " + WiFi.macAddress());
  }
}

void handleOLEDMessage() {
  if (server.hasArg("plain")) {
    String message = server.arg("plain");
    Serial.println("Received OLED message: " + message);
    
    displayMessage(message);
    
    server.send(200, "text/plain", "Message displayed on OLED");
  } else {
    server.send(400, "text/plain", "No message provided");
  }
}

void handleRoot() {
  String html = "<html><body>";
  html += "<h1>ESP32 WROOM RFID EXIT Scanner</h1>";
  html += "<p><strong>MAC:</strong> " + WiFi.macAddress() + "</p>";
  html += "<p><strong>IP:</strong> " + WiFi.localIP().toString() + "</p>";
  html += "<p><strong>Target Pi MAC:</strong> " + String(raspberryPiMAC) + "</p>";
  html += "<p><strong>Pi Status:</strong> " + (piFound ? ("Found - " + pythonServerIP) : "Not Found") + "</p>";
  html += "<p><strong>Function:</strong> ESP32 RFID EXIT scanner + OLED display</p>";
  html += "<hr>";
  html += "<h2>Test OLED Display</h2>";
  html += "<form method='post' action='/message'>";
  html += "<textarea name='plain' rows='4' cols='40' placeholder='Exit Granted\\nDoor Opened\\nGoodbye User'></textarea><br><br>";
  html += "<input type='submit' value='Send to OLED'>";
  html += "</form>";
  html += "<hr>";
  html += "<h3>Example Messages:</h3>";
  html += "<ul>";
  html += "<li><strong>Success:</strong> Exit Granted\\nDoor Opened\\nGoodbye John</li>";
  html += "<li><strong>Denied:</strong> Access Denied\\nNo Entry Found\\nUser</li>";
  html += "<li><strong>Ready:</strong> EXIT SCANNER\\nReady for scan...</li>";
  html += "</ul>";
  html += "<p><strong>ESP32 EXIT MAC:</strong> " + WiFi.macAddress() + "</p>";
  html += "</body></html>";
  server.send(200, "text/html", html);
}

void displayMessage(String message) {
  display.clearDisplay();
  display.setTextSize(1);  // Use smaller text size (1 = 6x8 pixels per character)
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  
  // Replace \n with actual newlines
  message.replace("\\n", "\n");
  
  // Split message by newlines and display
  int startPos = 0;
  int line = 0;
  int maxLines = 8; // 64 pixels / 8 pixels per line = 8 lines max
  
  while (startPos < message.length() && line < maxLines) {
    int endPos = message.indexOf('\n', startPos);
    if (endPos == -1) endPos = message.length();
    
    String lineText = message.substring(startPos, endPos);
    
    // Truncate long lines to fit the 128 pixel width (about 21 characters at size 1)
    if (lineText.length() > 21) {
      lineText = lineText.substring(0, 18) + "...";
    }
    
    // Use consistent small text size for all lines
    display.setTextSize(1);
    display.setCursor(0, line * 8);
    display.println(lineText);
    line++;
    
    startPos = endPos + 1;
  }
  
  display.display();
}
