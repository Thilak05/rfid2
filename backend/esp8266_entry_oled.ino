/*
 * ESP8266 Complete RFID Entry System with OLED Display
 * 
 * This ESP8266 handles:
 * 1. RFID scanning (MFRC522)
 * 2. OLED display (SSD1306)
 * 3. WiFi communication with Raspberry Pi
 * 4. Automatic Pi discovery by MAC address
 */

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// WiFi Configuration
const char* ssid = "R&D";
const char* password = "9686940950";

// Raspberry Pi Configuration (using MAC address for discovery)
const char* raspberryPiMAC = "D8:3A:DD:78:01:07";
String raspberryPiIP = "";
const int pythonServerPort = 8080;

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
const unsigned long SCAN_DELAY = 2000;
bool raspberryPiFound = false;
unsigned long lastDiscoveryAttempt = 0;
const unsigned long DISCOVERY_INTERVAL = 30000;

// Function declarations
String discoverRaspberryPiIP();
bool pingIP(String ip);
bool testPythonServer(String ip);
void discoverAndConnectToPi();
void sendRFIDToPython(String rfidUID);
void handleOLEDMessage();
void handleRoot();
void displayMessage(String message);

String discoverRaspberryPiIP() {
  Serial.println("🔍 Discovering Raspberry Pi by MAC address...");
  displayMessage("Discovering Pi...\n" + String(raspberryPiMAC));
  
  IPAddress localIP = WiFi.localIP();
  String networkBase = String(localIP[0]) + "." + String(localIP[1]) + "." + String(localIP[2]) + ".";
  
  Serial.println("Scanning network: " + networkBase + "1-254");
  
  for (int i = 1; i <= 254; i++) {
    String testIP = networkBase + String(i);
    if (testIP == WiFi.localIP().toString()) continue;
    
    if (pingIP(testIP) && testPythonServer(testIP)) {
      Serial.println("✓ Found Raspberry Pi at: " + testIP);
      return testIP;
    }
    
    if (i % 50 == 0) {
      Serial.println("Scanned up to: " + testIP);
      displayMessage("Scanning...\n" + testIP + "\nLooking for Pi...");
      yield();
    }
  }
  
  Serial.println("✗ Raspberry Pi not found on network");
  return "";
}

bool pingIP(String ip) {
  WiFiClient client;
  client.setTimeout(1000);
  
  if (client.connect(ip.c_str(), pythonServerPort)) {
    client.stop();
    return true;
  }
  
  return false;
}

bool testPythonServer(String ip) {
  WiFiClient client;
  client.setTimeout(2000);
  
  if (client.connect(ip.c_str(), pythonServerPort)) {
    client.print("TEST_CONNECTION");
    
    unsigned long timeout = millis() + 2000;
    while (client.available() == 0 && millis() < timeout) {
      delay(10);
    }
    
    if (client.available()) {
      String response = client.readString();
      client.stop();
      
      if (response.indexOf("OK") >= 0) {
        return true;
      }
    }
    
    client.stop();
  }
  
  return false;
}

void discoverAndConnectToPi() {
  unsigned long currentTime = millis();
  
  // FIXED: Added missing || operator
  if (!raspberryPiFound || (currentTime - lastDiscoveryAttempt > DISCOVERY_INTERVAL)) {
    lastDiscoveryAttempt = currentTime;
    
    raspberryPiIP = discoverRaspberryPiIP();
    
    if (raspberryPiIP.length() > 0) {
      raspberryPiFound = true;
      displayMessage("Pi Found!\nIP: " + raspberryPiIP + "\nReady for scan...");
      Serial.println("✓ Connected to Raspberry Pi at: " + raspberryPiIP);
    } else {
      raspberryPiFound = false;
      displayMessage("Pi Not Found\nMAC: " + String(raspberryPiMAC) + "\nRetrying...");
      Serial.println("✗ Raspberry Pi discovery failed");
    }
  }
}

void setup() {
  Serial.begin(9600);
  
  // Initialize OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("SSD1306 allocation failed");
    while (1);
  }
  
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println("ESP8266 RFID Entry");
  display.println("Initializing...");
  display.display();
  
  // Initialize SPI and RFID
  SPI.begin();
  mfrc522.PCD_Init();
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("Connecting WiFi...");
  display.display();
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  
  Serial.println();
  Serial.println("WiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
  Serial.print("MAC address: ");
  Serial.println(WiFi.macAddress());
  
  // Setup web server for OLED messages
  server.on("/message", HTTP_POST, handleOLEDMessage);
  server.on("/", HTTP_GET, handleRoot);
  server.begin();
  
  // Discover Raspberry Pi by MAC address
  Serial.println("🔍 Starting Raspberry Pi discovery...");
  Serial.println("Target MAC: " + String(raspberryPiMAC));
  
  discoverAndConnectToPi();
  
  // Display initial status
  if (raspberryPiFound) {
    displayMessage("ENTRY SCANNER\nPi: " + raspberryPiIP + "\nReady for scan...");
  } else {
    displayMessage("ENTRY SCANNER\nSearching for Pi...\nMAC: " + String(raspberryPiMAC));
  }
  
  Serial.println("ESP8266 RFID Entry System ready!");
}

void loop() {
  // Handle web server requests (for OLED messages)
  server.handleClient();
  
  // Periodically attempt to discover Raspberry Pi if not found
  if (!raspberryPiFound) {
    discoverAndConnectToPi();
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
    
    // Send to Python server
    sendRFIDToPython(rfidUID);
    
    // Halt PICC
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
  }
  
  delay(100);
}

void loop() {
  // Handle web server requests (for OLED messages)
  server.handleClient();
  
  // Periodically attempt to discover Raspberry Pi if not found
  if (!raspberryPiFound) {
    discoverAndConnectToPi();
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
    
    // Send to Python server
    sendRFIDToPython(rfidUID);
    
    // Halt PICC
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
  }
  
  delay(100);
}

void sendRFIDToPython(String rfidUID) {
  // FIXED: Added missing || operator
  if (!raspberryPiFound || raspberryPiIP.length() == 0) {
    displayMessage("Pi Not Found\nCannot send:\n" + rfidUID);
    Serial.println("✗ Cannot send RFID - Raspberry Pi not discovered");
    
    // Attempt to rediscover
    discoverAndConnectToPi();
    return;
  }
  
  displayMessage("Sending to Pi...\nIP: " + raspberryPiIP + "\n" + rfidUID);
  
  WiFiClient client;
  
  if (client.connect(raspberryPiIP.c_str(), pythonServerPort)) {
    Serial.println("Connected to Raspberry Pi: " + raspberryPiIP);
    
    // Send RFID data
    client.print(rfidUID);
    
    // Wait for response
    unsigned long timeout = millis() + 5000; // 5 second timeout
    while (client.available() == 0 && millis() < timeout) {
      delay(10);
    }
    
    if (client.available()) {
      String response = client.readString();
      Serial.println("Pi response: " + response);
      
      if (response.indexOf("OK") >= 0) {
        displayMessage("Sent to Pi!\nIP: " + raspberryPiIP + "\n" + rfidUID);
      } else {
        displayMessage("Pi Error\nResponse: " + response);
      }
    } else {
      Serial.println("Pi timeout");
      displayMessage("Pi Timeout\nIP: " + raspberryPiIP + "\n" + rfidUID);
      
      // Mark Pi as lost and try to rediscover
      raspberryPiFound = false;
    }
    
    client.stop();
  } else {
    Serial.println("Connection to Pi failed: " + raspberryPiIP);
    displayMessage("Pi Unreachable\nIP: " + raspberryPiIP + "\n" + rfidUID);
    
    // Mark Pi as lost and try to rediscover
    raspberryPiFound = false;
  }
  
  // Return to ready state after 2 seconds
  delay(2000);
  
  if (raspberryPiFound) {
    displayMessage("ENTRY SCANNER\nPi: " + raspberryPiIP + "\nReady for scan...");
  } else {
    displayMessage("ENTRY SCANNER\nSearching for Pi...\nMAC: " + String(raspberryPiMAC));
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
  html += "<h1>ESP8266 RFID Entry System</h1>";
  html += "<p><strong>IP:</strong> " + WiFi.localIP().toString() + "</p>";
  html += "<p><strong>MAC:</strong> " + WiFi.macAddress() + "</p>";
  html += "<p><strong>Target Pi MAC:</strong> " + String(raspberryPiMAC) + "</p>";
  html += "<p><strong>Pi Status:</strong> " + (raspberryPiFound ? ("Connected - " + raspberryPiIP) : "Not Found") + "</p>";
  html += "<p><strong>System:</strong> RFID + OLED Complete Entry System</p>";
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
  html += "<li><strong>Already Inside:</strong> Already Inside\\nAccess Denied\\nDoor Closed</li>";
  html += "</ul>";
  html += "<hr>";
  html += "<h3>System Information:</h3>";
  html += "<ul>";
  html += "<li>RFID Scanner: MFRC522 on SPI</li>";
  html += "<li>OLED Display: SSD1306 on I2C</li>";
  html += "<li>Communication: WiFi to Raspberry Pi</li>";
  html += "<li>Discovery: By Pi MAC address</li>";
  html += "<li>Listen Port: " + String(pythonServerPort) + "</li>";
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
