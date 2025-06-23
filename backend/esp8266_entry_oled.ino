/*
 * ESP8266 Simple RFID Entry Scanner with OLED Display
 * 
 * This ESP8266 simply:
 * 1. Scans RFID cards and sends UID to Python server
 * 2. Displays messages received from Python server on OLED
 * 3. Python server handles all logic (user verification, database, etc.)
 */

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>
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

// RFID Configuration
#define RST_PIN D3
#define SS_PIN D4
MFRC522 mfrc522(SS_PIN, RST_PIN);

// OLED Configuration
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Web Server for receiving OLED messages from Python
ESP8266WebServer server(80);

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

String discoverPiByMAC() {
  Serial.println("Discovering Raspberry Pi by MAC: " + String(raspberryPiMAC));
  displayMessage("Discovering Pi...\n" + String(raspberryPiMAC));
  
  IPAddress localIP = WiFi.localIP();
  String networkBase = String(localIP[0]) + "." + String(localIP[1]) + "." + String(localIP[2]) + ".";
  
  for (int i = 1; i <= 254; i++) {
    String testIP = networkBase + String(i);
    if (testIP == WiFi.localIP().toString()) continue;
    
    if (testPythonServer(testIP)) {
      Serial.println("Found Raspberry Pi at: " + testIP);
      return testIP;
    }
    
    if (i % 25 == 0) {
      displayMessage("Scanning...\n" + testIP + "\nLooking for Pi...");
      yield();
    }
  }
  
  Serial.println("Raspberry Pi not found");
  return "";
}

bool testPythonServer(String ip) {
  WiFiClient client;
  client.setTimeout(1000);
  
  if (client.connect(ip.c_str(), pythonServerPort)) {
    client.stop();
    return true;
  }
  return false;

void setup() {
  Serial.begin(9600);
  
  // Initialize OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("SSD1306 allocation failed");
    while (1);
  }
  
  displayMessage("ESP8266 RFID\nInitializing...");
  
  // Initialize SPI and RFID
  SPI.begin();
  mfrc522.PCD_Init();
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  displayMessage("Connecting WiFi...");
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  
  Serial.println();
  Serial.println("WiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
    // Setup web server for OLED messages
  server.on("/message", HTTP_POST, handleOLEDMessage);
  server.on("/", HTTP_GET, handleRoot);
  server.begin();
  
  // Discover Raspberry Pi by MAC address
  pythonServerIP = discoverPiByMAC();
  if (pythonServerIP.length() > 0) {
    piFound = true;
    displayMessage("ENTRY SCANNER\nPi Found: " + pythonServerIP + "\nMAC: " + WiFi.macAddress());
  } else {
    displayMessage("ENTRY SCANNER\nPi Not Found\nMAC: " + WiFi.macAddress());
  }
  
  Serial.println("ESP8266 RFID Entry System ready!");
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
        displayMessage("ENTRY SCANNER\nPi Found: " + pythonServerIP + "\nMAC: " + WiFi.macAddress());
      }
    }
  }
  
  // Check for RFID cards
  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    
    // Prevent duplicate scans
    unsigned long currentTime = millis();
    if (currentTime - lastScanTime < SCAN_DELAY) {
      mfrc522.PICC_HaltA();
      return;
    }
    
    // Read RFID UID
    String rfidUID = "";
    for (byte i = 0; i < mfrc522.uid.size; i++) {
      rfidUID += String(mfrc522.uid.uidByte[i], HEX);
    }
    rfidUID.toUpperCase();
    
    // Prevent duplicate of same card
    if (rfidUID == lastRFID && (currentTime - lastScanTime) < 5000) {
      mfrc522.PICC_HaltA();
      return;
    }
    
    lastRFID = rfidUID;
    lastScanTime = currentTime;
    
    Serial.println("RFID scanned: " + rfidUID);
    
    // Send to Python server and let it handle everything
    sendRFIDToPython(rfidUID);
    
    // Halt PICC
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
  }
  
  delay(100);
}

void sendRFIDToPython(String rfidUID) {
  if (!piFound || pythonServerIP.length() == 0) {
    displayMessage("Pi Not Found\nCannot send:\n" + rfidUID);
    Serial.println("Cannot send RFID - Pi not discovered");
    return;
  }
  
  displayMessage("Sending...\n" + rfidUID);
  
  WiFiClient client;
  HTTPClient http;
  
  // Send RFID to Python Flask server
  http.begin(client, "http://" + pythonServerIP + ":" + String(pythonServerPort) + "/scan");
  http.addHeader("Content-Type", "application/json");
  
  // Create JSON payload with MAC address for device identification
  String deviceMAC = WiFi.macAddress();
  String jsonPayload = "{\"unique_id\":\"" + rfidUID + "\",\"action\":\"entry\",\"device_mac\":\"" + deviceMAC + "\"}";
  
  int httpResponseCode = http.POST(jsonPayload);
  
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println("HTTP Response: " + String(httpResponseCode));
    Serial.println("Response: " + response);
    
    if (httpResponseCode == 200) {
      displayMessage("Sent Successfully\n" + rfidUID);
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
    displayMessage("ENTRY SCANNER\nPi: " + pythonServerIP + "\nMAC: " + WiFi.macAddress());
  } else {
    displayMessage("ENTRY SCANNER\nPi Not Found\nMAC: " + WiFi.macAddress());
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
  html += "<h1>ESP8266 RFID Entry Scanner</h1>";  html += "<p><strong>MAC:</strong> " + WiFi.macAddress() + "</p>";
  html += "<p><strong>IP:</strong> " + WiFi.localIP().toString() + "</p>";
  html += "<p><strong>Target Pi MAC:</strong> " + String(raspberryPiMAC) + "</p>";
  html += "<p><strong>Pi Status:</strong> " + (piFound ? ("Found - " + pythonServerIP) : "Not Found") + "</p>";
  html += "<p><strong>Function:</strong> Simple RFID scanner + OLED display</p>";
  html += "<hr>";
  html += "<h2>Test OLED Display</h2>";
  html += "<form method='post' action='/message'>";
  html += "<textarea name='plain' rows='4' cols='40' placeholder='Access Granted\\nDoor Opened\\nWelcome User'></textarea><br><br>";
  html += "<input type='submit' value='Send to OLED'>";
  html += "</form>";
  html += "<hr>";
  html += "<h3>Example Messages:</h3>";
  html += "<ul>";
  html += "<li><strong>Success:</strong> Access Granted\\nDoor Opened\\nWelcome John</li>";
  html += "<li><strong>Denied:</strong> Access Denied\\nDoor Closed\\nNot Registered</li>";
  html += "<li><strong>Ready:</strong> ENTRY SCANNER\\nReady for scan...</li>";
  html += "</ul>";
  html += "</body></html>";
  server.send(200, "text/html", html);
}

void displayMessage(String message) {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  
  // Replace \n with actual newlines
  message.replace("\\n", "\n");
  
  // Split message by newlines and display
  int startPos = 0;
  int line = 0;
  int maxLines = 8; // 64 pixels / 8 pixels per line
  
  while (startPos < message.length() && line < maxLines) {
    int endPos = message.indexOf('\n', startPos);
    if (endPos == -1) endPos = message.length();
    
    String lineText = message.substring(startPos, endPos);
    
    // Make certain lines larger for better visibility
    if (line == 0 && (lineText.indexOf("Access") != -1 || lineText.indexOf("ENTRY") != -1)) {
      display.setTextSize(2);
      display.setCursor(0, line * 16);
      display.println(lineText);
      line += 2; // Takes 2 line spaces
      display.setTextSize(1);
    } else {
      display.setCursor(0, line * 8);
      display.println(lineText);
      line++;
    }
    
    startPos = endPos + 1;
  }
  
  display.display();
}
