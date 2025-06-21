/*
 * ESP8266 RFID Entry System with OLED Display
 * 
 * This ESP8266 code:
 * 1. Reads RFID data from MFRC522 scanner
 * 2. Sends RFID data to Python server over WiFi
 * 3. Displays access results on SSD1306 OLED
 * 4. Uses MAC address for identification: C4:5B:BE:74:FC:39
 */

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// WiFi Configuration
const char* ssid = "YOUR_WIFI_SSID";      // Replace with your WiFi SSID
const char* password = "YOUR_WIFI_PASSWORD"; // Replace with your WiFi password

// Raspberry Pi Configuration (using MAC address for discovery)
const char* raspberryPiMAC = "D8:3A:DD:78:01:07"; // Raspberry Pi MAC address
String raspberryPiIP = "";                         // Will be discovered
const int pythonServerPort = 8080;                 // Port where Python listens

// RFID Configuration
#define RST_PIN    D3     // Reset pin
#define SS_PIN     D4     // Slave select pin
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
bool raspberryPiFound = false;
unsigned long lastDiscoveryAttempt = 0;
const unsigned long DISCOVERY_INTERVAL = 30000; // Re-discover every 30 seconds

// Function declarations
String discoverRaspberryPiIP();
bool pingIP(String ip);
void discoverAndConnectToPi();

void setup() {
  Serial.begin(9600);
  
  // Initialize OLED
  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("SSD1306 allocation failed");
    while(1);
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
  
  Serial.println();  Serial.println("WiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
  Serial.print("MAC address: ");
  Serial.println(WiFi.macAddress());
  
  // Setup web server for OLED messages
  server.on("/message", HTTP_POST, handleOLEDMessage);
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

void sendRFIDToPython(String rfidUID) {
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

void displayMessage(String message) {
  display.clearDisplay();
  display.setCursor(0, 0);
  
  // Replace \n with actual newlines
  message.replace("\\n", "\n");
  
  // Split message by newlines and display
  int startPos = 0;
  int line = 0;
  
  while (startPos < message.length() && line < 8) { // Max 8 lines
    int endPos = message.indexOf('\n', startPos);
    if (endPos == -1) endPos = message.length();
    
    String lineText = message.substring(startPos, endPos);
    display.setCursor(0, line * 8);
    display.println(lineText);
    
    startPos = endPos + 1;
    line++;
  }
  
  display.display();
}

void displayConnectionInfo() {
  display.clearDisplay();
  display.setCursor(0, 0);
  display.setTextSize(1);
  display.println("ESP8266 RFID Entry");
  display.println("IP: " + WiFi.localIP().toString());
  display.println("MAC: " + WiFi.macAddress());
  display.println("Ready for scan...");
  display.display();
}

String discoverRaspberryPiIP() {
  /*
   * Discover Raspberry Pi IP address by scanning network for MAC address
   * This function attempts to find the Pi by pinging common IP ranges
   * and checking ARP responses (limited on ESP8266, so we use ping method)
   */
  
  Serial.println("🔍 Discovering Raspberry Pi by MAC address...");
  displayMessage("Discovering Pi...\n" + String(raspberryPiMAC));
  
  // Get our own IP to determine network range
  IPAddress localIP = WiFi.localIP();
  String networkBase = String(localIP[0]) + "." + String(localIP[1]) + "." + String(localIP[2]) + ".";
  
  Serial.println("Scanning network: " + networkBase + "1-254");
  
  // Scan common IP ranges (this is a simplified approach)
  // In a real implementation, you might need a more sophisticated method
  for (int i = 1; i <= 254; i++) {
    String testIP = networkBase + String(i);
    
    // Skip our own IP
    if (testIP == WiFi.localIP().toString()) continue;
    
    // Test connectivity with a quick ping-like check
    if (pingIP(testIP)) {
      Serial.println("✓ Found responsive device at: " + testIP);
      
      // For ESP8266, we can't easily check ARP table
      // So we'll try to connect and see if it responds as expected
      if (testPythonServer(testIP)) {
        Serial.println("✓ Found Raspberry Pi at: " + testIP);
        return testIP;
      }
    }
    
    // Show progress
    if (i % 50 == 0) {
      Serial.println("Scanned up to: " + testIP);
      yield(); // Prevent watchdog timeout
    }
  }
  
  Serial.println("✗ Raspberry Pi not found on network");
  return "";
}

bool pingIP(String ip) {
  /*
   * Simple connectivity test to an IP address
   * Uses HTTP request as a "ping" since ESP8266 doesn't have native ping
   */
  
  WiFiClient client;
  
  // Try to connect with short timeout
  client.setTimeout(1000); // 1 second timeout
  
  if (client.connect(ip.c_str(), pythonServerPort)) {
    client.stop();
    return true;
  }
  
  return false;
}

bool testPythonServer(String ip) {
  /*
   * Test if the IP address is running our Python server
   * by attempting to connect to the RFID listener port
   */
  
  WiFiClient client;
  client.setTimeout(2000); // 2 second timeout
  
  if (client.connect(ip.c_str(), pythonServerPort)) {
    // Send a test message to see if it responds correctly
    client.print("TEST_CONNECTION");
    
    // Wait for response
    unsigned long timeout = millis() + 2000;
    while (client.available() == 0 && millis() < timeout) {
      delay(10);
    }
    
    if (client.available()) {
      String response = client.readString();
      client.stop();
      
      // If we get "OK" response, this is likely our Python server
      if (response.indexOf("OK") >= 0) {
        return true;
      }
    }
    
    client.stop();
  }
  
  return false;
}

void discoverAndConnectToPi() {
  /*
   * Main function to discover and connect to Raspberry Pi
   */
  
  unsigned long currentTime = millis();
  
  // Only attempt discovery if not found or if it's time to re-discover
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
