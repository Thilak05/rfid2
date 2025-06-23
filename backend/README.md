# ESP32 WROOM RFID Entry System

A complete RFID-based entry system using ESP32 WROOM with OLED display and Python Flask backend.

## System Overview

### Hardware Components
- **ESP32 WROOM Development Board** (MAC: `E4:65:B8:27:73:08`)
- **RFID Reader** (Serial output)
- **SSD1306 OLED Display** (128x64, I2C)
- **Raspberry Pi** (MAC: `D8:3A:DD:78:01:07`)

### Architecture
- **ESP32**: Scans RFID cards, sends UID to Pi, displays messages from Pi
- **Raspberry Pi**: Runs Flask server, handles all business logic, user verification, database operations
- **Network Discovery**: ESP32 discovers Pi by scanning subnet and verifying MAC address via `/api/device/info`

## Pin Connections

### ESP32 WROOM Pin Layout
```
RFID Reader (Serial):
  GND -> GND
  VCC -> 3.3V
  TXD -> GPIO16 (RX2) - RFID data output

OLED SSD1306 (I2C):
  GND -> GND
  VCC -> 3.3V
  SDA -> GPIO21 (SDA)
  SCL -> GPIO22 (SCL)
```

## Installation

### 1. Python Backend Setup (Raspberry Pi)
```bash
cd backend/
pip install -r requirements.txt
```

### 2. Database Initialization
```bash
python db_setup.py
```

### 3. Arduino IDE Setup for ESP32
1. Install ESP32 board support in Arduino IDE
2. Install required libraries:
   - `Adafruit GFX Library`
   - `Adafruit SSD1306`
3. Configure WiFi credentials in `esp8266_entry_oled.ino`:
   ```cpp
   const char* ssid = "YOUR_WIFI_SSID";
   const char* password = "YOUR_WIFI_PASSWORD";
   ```

### 4. Hardware Verification
Update MAC addresses in code if needed:
- **ESP32 MAC**: Update in `rfid_sender.py` if different from `E4:65:B8:27:73:08`
- **Pi MAC**: Update in both `esp8266_entry_oled.ino` and `rfid_sender.py` if different from `D8:3A:DD:78:01:07`

## Usage

### 1. Start Flask Server (Pi)
```bash
python app.py
```
Server starts on: `http://0.0.0.0:5000`

### 2. Upload ESP32 Code
Upload `esp8266_entry_oled.ino` to ESP32 WROOM board.

### 3. Monitor ESP32 (Optional)
Open Serial Monitor (115200 baud) to see ESP32 logs:
- WiFi connection status
- Pi discovery process
- RFID scan results
- OLED message confirmations

### 4. Web Frontend (Optional)
Access React frontend at: `http://[PI_IP]:5173`

## System Flow

### ESP32 Startup Sequence
1. **WiFi Connection**: Connects to configured WiFi network
2. **Pi Discovery**: Scans subnet for Flask servers (port 5000)
3. **MAC Verification**: Fetches `/api/device/info` from each server and verifies MAC address
4. **OLED Ready**: Displays "ENTRY SCANNER" when Pi is found and verified

### RFID Scan Process
1. **Card Detection**: ESP32 reads RFID UID from serial
2. **Data Transmission**: Sends JSON to Pi: `{"unique_id": "RFID_UID", "action": "entry", "device_mac": "ESP32_MAC"}`
3. **Pi Processing**: Pi validates user, logs entry/exit, determines response
4. **OLED Response**: Pi sends message back to ESP32 OLED display

### Network Discovery Details
- ESP32 scans network range: `192.168.x.1-254`
- Tests each IP for Flask server on port 5000
- Fetches device info: `GET /api/device/info`
- Verifies MAC address matches target Pi MAC: `D8:3A:DD:78:01:07`
- Only connects to Pi with matching MAC address

## API Endpoints

### Device Discovery
- `GET /` - Root endpoint for basic server identification
- `GET /api/device/info` - Returns device type, MAC address, server info

### User Management
- `GET /api/users` - List all users
- `POST /api/users` - Register new user
- `PUT /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user
- `POST /api/validate_user` - Validate user by RFID

### Access Control
- `POST /scan` - Process RFID scan (entry/exit)
- `POST /message` - Send OLED message to ESP device

### Monitoring
- `GET /api/logs` - Recent access logs
- `GET /api/stats` - System statistics
- `GET /api/rfid/status` - Current RFID scan status

## Files Description

### Core Files
- `app.py` - Main Flask server with all endpoints and logic
- `esp8266_entry_oled.ino` - ESP32 firmware for RFID scanning and OLED display
- `requirements.txt` - Python dependencies

### Supporting Files
- `rfid_sender.py` - Alternative entry point system (network-based)
- `rfid_reader.py` - Alternative exit point system (serial-based)
- `db_setup.py` - Database initialization utility

## Configuration

### WiFi Settings (ESP32)
```cpp
const char* ssid = "R&D";              // Your WiFi SSID
const char* password = "9686940950";   // Your WiFi password
```

### Device MAC Addresses
```cpp
// In esp8266_entry_oled.ino
const char* raspberryPiMAC = "D8:3A:DD:78:01:07";
```

```python
# In rfid_sender.py
ESP32_MAC = "E4:65:B8:27:73:08"
RASPBERRY_PI_MAC = "D8:3A:DD:78:01:07"
```

## Troubleshooting

### ESP32 Not Finding Pi
1. Verify both devices on same network
2. Check Pi MAC address: `ip link show` or `ifconfig`
3. Ensure Flask server is running and accessible
4. Check firewall settings on Pi

### OLED Display Issues
1. Verify I2C connections (SDA=21, SCL=22)
2. Check OLED I2C address (default: 0x3C)
3. Ensure adequate power supply

### RFID Reading Issues
1. Verify RFID reader serial output
2. Check baud rate (default: 9600)
3. Ensure proper wiring to GPIO16 (RX2)

### Network Connectivity
1. Verify WiFi credentials
2. Ensure 2.4GHz network (ESP32 doesn't support 5GHz)
3. Check signal strength and range

## Security Notes

- System uses MAC address verification for device identification
- All communication is over HTTP (consider HTTPS for production)
- RFID UIDs are transmitted in plain text
- Database contains user information and access logs

## Development

### Adding New Users
Use the web frontend or direct API calls:
```bash
curl -X POST http://[PI_IP]:5000/api/users \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "unique_id": "RFID_UID_HERE", "email": "john@example.com"}'
```

### Testing OLED Messages
```bash
curl -X POST http://[ESP32_IP]/message \
  -d "Test Message\nLine 2\nLine 3"
```

### Viewing Logs
```bash
curl http://[PI_IP]:5000/api/logs
```

This system provides a robust, network-based RFID entry solution with proper device identification and real-time OLED feedback.
