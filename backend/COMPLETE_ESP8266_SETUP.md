# Complete ESP8266 RFID Entry System Setup

## Overview

This single ESP8266 module now handles **everything** for the entry point:
- ✅ **RFID Scanning** (MFRC522)
- ✅ **OLED Display** (SSD1306) 
- ✅ **WiFi Communication** with Raspberry Pi
- ✅ **Automatic Pi Discovery** by MAC address
- ✅ **Complete Entry Processing**

## Hardware Setup

### ESP8266 Module
- **Recommended**: NodeMCU or Wemos D1 Mini
- **Power**: 3.3V (can use USB for development)
- **WiFi**: 2.4GHz network required

### Complete Wiring Diagram

```
ESP8266 Connections:

MFRC522 RFID Scanner (SPI):
┌─────────────┬──────────────┐
│ MFRC522 Pin │ ESP8266 Pin  │
├─────────────┼──────────────┤
│ VCC         │ 3.3V         │
│ RST         │ D3 (GPIO 0)  │
│ GND         │ GND          │
│ MISO        │ D6 (GPIO 12) │
│ MOSI        │ D7 (GPIO 13) │
│ SCK         │ D5 (GPIO 14) │
│ SDA         │ D4 (GPIO 2)  │
└─────────────┴──────────────┘

SSD1306 OLED Display (I2C):
┌─────────────┬──────────────┐
│ OLED Pin    │ ESP8266 Pin  │
├─────────────┼──────────────┤
│ VCC         │ 3.3V         │
│ GND         │ GND          │
│ SCL         │ D1 (GPIO 5)  │
│ SDA         │ D2 (GPIO 4)  │
└─────────────┴──────────────┘

Power Supply:
- VCC/3.3V: Connect all VCC pins together
- GND: Connect all GND pins together
- Use ESP8266 built-in 3.3V regulator
```

## Software Configuration

### 1. Arduino IDE Setup

Install required libraries:
```
Tools > Manage Libraries > Install:
1. ESP8266WiFi (built-in with ESP8266 board package)
2. ESP8266WebServer (built-in)
3. MFRC522 by GithubCommunity
4. Adafruit SSD1306
5. Adafruit GFX Library
6. SPI (built-in)
7. Wire (built-in)
```

### 2. Update Configuration

Edit these lines in `esp8266_entry_oled.ino`:

```cpp
// WiFi Settings
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Raspberry Pi MAC Address (no need to change if correct)
const char* raspberryPiMAC = "D8:3A:DD:78:01:07";
```

### 3. Flash ESP8266

1. Connect ESP8266 to computer via USB
2. Select correct board: **Tools > Board > ESP8266 Boards > NodeMCU 1.0**
3. Select correct port: **Tools > Port > COM[X]** (Windows) or **/dev/ttyUSB[X]** (Linux)
4. Upload code: **Sketch > Upload**

## System Operation

### Startup Sequence

1. **Initialization**
   ```
   OLED: "ESP8266 RFID Entry\nInitializing..."
   ```

2. **WiFi Connection**
   ```
   OLED: "Connecting WiFi..."
   Serial: "WiFi connected! IP address: 192.168.1.150"
   ```

3. **Pi Discovery**
   ```
   OLED: "Discovering Pi...\nD8:3A:DD:78:01:07"
   Serial: "🔍 Discovering Raspberry Pi by MAC address..."
   Serial: "Scanning network: 192.168.1.1-254"
   ```

4. **Ready State**
   ```
   OLED: "ENTRY SCANNER\nPi: 192.168.1.100\nReady for scan..."
   Serial: "✓ Connected to Raspberry Pi at: 192.168.1.100"
   ```

### RFID Scan Process

1. **User scans RFID card**
   ```
   Serial: "RFID scanned: A1B2C3D4"
   OLED: "Sending to Pi...\nIP: 192.168.1.100\nA1B2C3D4"
   ```

2. **Data sent to Raspberry Pi**
   ```
   Serial: "Connected to Raspberry Pi: 192.168.1.100"
   Serial: "Pi response: OK"
   OLED: "Sent to Pi!\nIP: 192.168.1.100\nA1B2C3D4"
   ```

3. **Access result received from Pi**
   ```
   OLED: "Access Granted\nDoor Opened\nWelcome John"
   ```

4. **Return to ready**
   ```
   OLED: "ENTRY SCANNER\nPi: 192.168.1.100\nReady for scan..."
   ```

## Web Interface

The ESP8266 provides a web interface for testing and monitoring:

### Access Web Interface
- **URL**: `http://[ESP8266_IP]` (e.g., `http://192.168.1.150`)
- **Features**:
  - System status display
  - Pi connection status
  - OLED message testing
  - System information

### Test OLED Messages
Send test messages via web interface:
```
Access Granted\nDoor Opened\nWelcome John
Access Denied\nDoor Closed\nNot Registered
ENTRY SCANNER\nReady for scan...
```

## Communication Protocol

### ESP8266 → Raspberry Pi (Port 8080)
```
Connection: TCP to Pi IP:8080
Data Format: Plain text RFID UID
Example: "A1B2C3D4"
Response: "OK"
```

### Raspberry Pi → ESP8266 (Port 80)
```
Connection: HTTP POST to ESP8266_IP:80/message
Data Format: Plain text message
Example: "Access Granted\nDoor Opened\nWelcome John"
Response: "Message displayed on OLED"
```

## Troubleshooting

### ESP8266 Not Connecting to WiFi
- ✅ Check SSID and password
- ✅ Ensure 2.4GHz network (ESP8266 doesn't support 5GHz)
- ✅ Check signal strength

### Pi Discovery Failing
- ✅ Verify Pi MAC address: `ip link show`
- ✅ Ensure Pi and ESP8266 on same network
- ✅ Check Python server is running: `python3 rfid_sender.py`
- ✅ Verify port 8080 is open on Pi

### RFID Not Reading
- ✅ Check wiring connections (especially SPI pins)
- ✅ Verify 3.3V power supply
- ✅ Test with known RFID cards
- ✅ Check for interference from other devices

### OLED Not Displaying
- ✅ Check I2C wiring (SDA/SCL)
- ✅ Verify OLED address (usually 0x3C)
- ✅ Test with simple text
- ✅ Check power supply

### Python Communication Issues
- ✅ Check Pi firewall settings
- ✅ Verify Python server listening on port 8080
- ✅ Test network connectivity between devices
- ✅ Check for IP address changes (DHCP)

## System Benefits

### All-in-One Design
- ✅ **Single ESP8266** handles everything
- ✅ **No serial cables** required
- ✅ **Wireless communication** only
- ✅ **Automatic discovery** and reconnection

### Robust Operation
- ✅ **Auto-reconnects** if Pi restarts
- ✅ **Visual feedback** on OLED for all states
- ✅ **Web interface** for testing and monitoring
- ✅ **Duplicate scan prevention**

### Easy Deployment
- ✅ **Compact hardware** setup
- ✅ **WiFi-based** - works anywhere with network
- ✅ **MAC address discovery** - no IP configuration
- ✅ **Plug and play** operation

This complete ESP8266 solution provides a professional, robust RFID entry system with integrated display and intelligent network communication!
