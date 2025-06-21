/*
 * ESP8266 OLED Display Server for RFID Entry Point
 * This code runs on ESP8266 with an OLED display connected.
 * It receives HTTP POST requests with messages to display on the OLED.
 * 
 * Hardware Required:
 * - ESP8266 (NodeMCU, Wemos D1 Mini, etc.)
 * - OLED Display (128x64, I2C interface)
 * 
 * Wiring:
 * OLED VCC -> 3.3V
 * OLED GND -> GND
 * OLED SCL -> D1 (GPIO5)
 * OLED SDA -> D2 (GPIO4)
 */

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// OLED Display configuration
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// WiFi credentials - Update these with your network details
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Static IP configuration (must match Python script)
IPAddress local_IP(192, 168, 0, 10);
IPAddress gateway(192, 168, 0, 1);
IPAddress subnet(255, 255, 255, 0);

ESP8266WebServer server(80);

void setup() {
  Serial.begin(115200);
  
  // Initialize OLED display
  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("SSD1306 allocation failed"));
    for(;;);
  }
  
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println("ESP8266 Starting...");
  display.display();
  
  // Configure static IP
  if (!WiFi.config(local_IP, gateway, subnet)) {
    Serial.println("STA Failed to configure");
  }
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("Connecting WiFi...");
  display.display();
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println();
  Serial.print("Connected! IP address: ");
  Serial.println(WiFi.localIP());
  
  // Display connection info on OLED
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("WiFi Connected!");
  display.print("IP: ");
  display.println(WiFi.localIP());
  display.println("Entry Point OLED");
  display.println("Ready...");
  display.display();
  
  // Setup web server routes
  server.on("/message", HTTP_POST, handleMessage);
  server.on("/", HTTP_GET, handleRoot);
  
  server.begin();
  Serial.println("HTTP server started");
  
  delay(2000);  // Show connection info for 2 seconds
  showReadyScreen();
}

void loop() {
  server.handleClient();
}

void handleMessage() {
  if (server.hasArg("plain")) {
    String message = server.arg("plain");
    Serial.println("Received message: " + message);
    displayMessage(message);
    server.send(200, "text/plain", "Message displayed on Entry OLED");
  } else {
    server.send(400, "text/plain", "No message data");
  }
}

void handleRoot() {
  String html = "<html><body>";
  html += "<h1>RFID Entry Point OLED Display</h1>";
  html += "<p>IP: " + WiFi.localIP().toString() + "</p>";
  html += "<p>Status: Ready for Entry Scans</p>";
  html += "<form method='post' action='/message'>";
  html += "<textarea name='plain' rows='4' cols='30' placeholder='Access Granted\\nDoor Opened\\nWelcome User'></textarea><br>";
  html += "<input type='submit' value='Send Message'>";
  html += "</form>";
  html += "<p>Example messages:</p>";
  html += "<ul>";
  html += "<li>Access Granted\\nDoor Opened\\nWelcome John</li>";
  html += "<li>Access Denied\\nDoor Closed\\nNot Registered</li>";
  html += "<li>ENTRY SCANNER\\nReady for scan...</li>";
  html += "</ul>";
  html += "</body></html>";
  server.send(200, "text/html", html);
}

void displayMessage(String message) {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  
  // Split message by newlines and display
  int startIndex = 0;
  int line = 0;
  int maxLines = 8; // 64 pixels / 8 pixels per line
  
  while (startIndex < message.length() && line < maxLines) {
    int endIndex = message.indexOf('\n', startIndex);
    if (endIndex == -1) {
      endIndex = message.length();
    }
    
    String lineText = message.substring(startIndex, endIndex);
    
    // Make certain lines larger for better visibility
    if (line == 0 && (lineText.indexOf("Access") != -1)) {
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
    
    startIndex = endIndex + 1;
  }
  
  display.display();
}

void showReadyScreen() {
  display.clearDisplay();
  display.setTextSize(2);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println("ENTRY");
  display.println("SCANNER");
  display.setTextSize(1);
  display.setCursor(0, 40);
  display.println("Ready for scan...");
  display.print("IP: ");
  display.println(WiFi.localIP());
  display.display();
}
