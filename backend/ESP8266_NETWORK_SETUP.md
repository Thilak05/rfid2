# ESP8266 Network-based RFID Entry System Setup

## Overview

This system uses ESP8266 to handle RFID scanning and OLED display for the entry point, communicating with the Python server over WiFi using the ESP8266's MAC address for identification.

## System Architecture

```
RFID Scanner → ESP8266 → WiFi → Python Server → Flask App
     ↓             ↓
   MFRC522      OLED Display
```

## Hardware Requirements

### ESP8266 Module
- ESP8266 development board (NodeMCU, Wemos D1 Mini, etc.)
- **MAC Address**: `C4:5B:BE:74:FC:39` (update if different)

### RFID Scanner (MFRC522)
- **VCC** → 3.3V
- **RST** → D3 (GPIO 0)
- **GND** → GND
- **MISO** → D6 (GPIO 12)
- **MOSI** → D7 (GPIO 13)
- **SCK** → D5 (GPIO 14)
- **SDA** → D4 (GPIO 2)

### OLED Display (SSD1306)
- **VCC** → 3.3V
- **GND** → GND
- **SDA** → D2 (GPIO 4)
- **SCL** → D1 (GPIO 5)

## Software Setup

### 1. Arduino IDE Configuration

Install required libraries:
```
1. ESP8266WiFi (built-in)
2. ESP8266WebServer (built-in)
3. MFRC522 by GithubCommunity
4. Adafruit SSD1306
5. Adafruit GFX Library
```

### 2. ESP8266 Code Configuration

Edit `esp8266_rfid_entry.ino`:

```cpp
// Update WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Update Python server IP (your Raspberry Pi IP)
const char* pythonServerIP = "192.168.1.100";
```

### 3. Python Server Configuration

The Python server (`rfid_sender.py`) is configured to:
- **Listen on port**: 8080 (for RFID data from ESP8266)
- **Send OLED messages to ESP8266 on port**: 80
- **ESP8266 MAC address**: `C4:5B:BE:74:FC:39`

## Network Communication Protocol

### RFID Data (ESP8266 → Python)
```
ESP8266 connects to: Python_Server_IP:8080
Sends: RFID_UID (e.g., "A1B2C3D4")
Receives: "OK" (acknowledgment)
```

### OLED Messages (Python → ESP8266)
```
Python connects to: ESP8266_IP:80/message
Sends: POST request with message body
ESP8266 displays message on OLED
```

## Setup Steps

### 1. Flash ESP8266
1. Connect ESP8266 to computer via USB
2. Open `esp8266_rfid_entry.ino` in Arduino IDE
3. Update WiFi credentials and server IP
4. Select correct board and port
5. Upload code

### 2. Start Python Server
```bash
cd /path/to/project/backend
python3 rfid_sender.py
```

### 3. Verify Communication
1. ESP8266 should connect to WiFi and display IP
2. Python should discover ESP8266 by MAC address
3. OLED should show "ENTRY SCANNER Ready for scan..."

## Expected Output

### Python Server Startup
```
============================================================
🔐 RFID Entry System (Network-based)
   ESP8266 MAC: C4:5B:BE:74:FC:39
   Listen Port: 8080
   OLED Port: 80
============================================================
🔍 Discovering ESP8266...
✓ Found ESP8266 at IP: 192.168.1.150
✓ ESP8266 is reachable
📺 Initializing ESP8266 OLED display...
✓ ESP8266 OLED initialized successfully
🌐 RFID Server listening on port 8080
   Waiting for ESP8266 (C4:5B:BE:74:FC:39) to send RFID data...

🚀 Entry system started!
   - ESP8266 should send RFID data to this system
   - OLED messages will be sent back to ESP8266
   - Press Ctrl+C to stop
```

### RFID Scan Process
```
📡 Received RFID data from ESP8266 (192.168.1.150): A1B2C3D4
Access Granted for John Doe (RFID: A1B2C3D4)
Entry logged successfully: Entry recorded for John Doe
✅ ENTRY: Access granted for John Doe
✓ Sent to ESP8266 OLED: 200 - Message displayed on OLED
✓ Entry processed successfully
```

## Troubleshooting

### ESP8266 Not Found
1. **Check MAC address**: Verify ESP8266 MAC matches `C4:5B:BE:74:FC:39`
2. **Check network**: Ensure ESP8266 and Python server are on same network
3. **Check ARP table**: Run `arp -a` to see if ESP8266 is visible

### Connection Issues
1. **WiFi credentials**: Double-check SSID and password
2. **IP address**: Update Python server IP in ESP8266 code
3. **Firewall**: Ensure ports 8080 and 80 are open

### OLED Display Issues
1. **Wiring**: Check I2C connections (SDA/SCL)
2. **Address**: Verify OLED I2C address (usually 0x3C)
3. **Power**: Ensure 3.3V power supply

### RFID Reading Issues
1. **Wiring**: Check SPI connections
2. **Power**: Ensure 3.3V power supply
3. **Card compatibility**: Use MIFARE Classic cards

## Testing Commands

### Test ESP8266 Discovery
```bash
# Check if ESP8266 is in ARP table
arp -a | grep -i "c4:5b:be:74:fc:39"

# Ping ESP8266 (if IP is known)
ping 192.168.1.150
```

### Test OLED Communication
```bash
# Send test message to ESP8266 OLED
curl -X POST -d "Test Message\nFrom Python" http://ESP8266_IP/message
```

## File Structure
```
backend/
├── rfid_sender.py              # Main Python server (network-based)
├── esp8266_rfid_entry.ino      # ESP8266 Arduino code
├── rfid_reader.py              # Exit system (unchanged)
└── app.py                      # Flask web server (unchanged)
```

This setup eliminates the need for direct serial connections and allows the ESP8266 to operate independently while communicating over WiFi.
