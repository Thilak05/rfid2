# RFID Access Control System - OLED Display Integration

## Overview
This system integrates OLED displays to provide visual feedback for RFID access control:
- **Entry Point**: ESP8266 OLED (WiFi-based)
- **Exit Point**: Serial OLED (Serial port-based)

## Hardware Requirements

### Entry Point - ESP8266 OLED
- ESP8266 module (NodeMCU, Wemos D1 Mini, etc.)
- 128x64 I2C OLED Display
- WiFi connection

**Wiring:**
```
ESP8266    OLED Display
3.3V   →   VCC
GND    →   GND
D1     →   SCL (GPIO5)
D2     →   SDA (GPIO4)
```

### Exit Point - Serial OLED
- Serial OLED display compatible with UART communication
- Serial port connection (/dev/ttyUSB2 by default)

## Software Configuration

### 1. ESP8266 Setup (Entry Point)

1. Install Arduino IDE with ESP8266 board support
2. Install required libraries:
   - ESP8266WiFi
   - ESP8266WebServer
   - Adafruit_GFX
   - Adafruit_SSD1306

3. Configure `esp8266_entry_oled.ino`:
   ```cpp
   const char* ssid = "YOUR_WIFI_SSID";
   const char* password = "YOUR_WIFI_PASSWORD";
   IPAddress local_IP(192, 168, 0, 10);  // Must match Python scripts
   ```

4. Upload the code to ESP8266

### 2. Python Scripts Configuration

**Entry Point (rfid_sender.py):**
```python
ESP_IP = "192.168.0.10"  # Must match ESP8266 IP
```

**Exit Point (rfid_reader.py):**
```python
OLED_SERIAL_PORT = '/dev/ttyUSB2'  # Update for your system
```

## Display Messages

### Entry Point Messages (ESP8266 OLED)

**Access Granted:**
```
Access Granted
Door Opened
Welcome [User Name]
```

**Access Denied - Not Registered:**
```
Access Denied
Door Closed
Not Registered
```

**Access Denied - Already Inside:**
```
Access Denied
Door Closed
Already Inside
```

**Ready State:**
```
ENTRY SCANNER
Ready for scan...
```

### Exit Point Messages (Serial OLED)

**Access Granted:**
```
Access Granted
Door Opened
Goodbye [User Name]
```

**Access Denied - Entry Not Found:**
```
Entry Not Found
Access Denied
Door Closed
```

**Access Denied - Not Registered:**
```
Access Denied
Door Closed
Not Registered
```

**Ready State:**
```
EXIT SCANNER
Ready for scan...
```

## API Communication

### ESP8266 HTTP Endpoint
```
POST http://192.168.0.10/message
Content-Type: application/x-www-form-urlencoded
Body: [message content]
```

Example using Python:
```python
import requests
ESP_IP = "192.168.0.10"
message = "Access Granted\nDoor Opened\nWelcome John"
response = requests.post(f"http://{ESP_IP}/message", data=message)
```

### Serial OLED Communication
```python
import serial
OLED_SERIAL_PORT = '/dev/ttyUSB2'
BAUD_RATE = 9600

with serial.Serial(OLED_SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
    ser.write(b'\x0C')  # Clear screen
    time.sleep(0.1)
    ser.write(message.encode('utf-8'))
```

## Testing

### Test Individual Displays
```bash
# Test connectivity
python oled_test.py connectivity

# Test entry scenarios (ESP8266)
python oled_test.py entry

# Test exit scenarios (Serial)
python oled_test.py exit

# Test ready screens
python oled_test.py ready

# Interactive mode
python oled_test.py interactive
```

### Test Full System
```bash
# Run all tests
python oled_test.py
```

## Setup Instructions

### 1. Hardware Setup
1. Connect ESP8266 OLED as per wiring diagram
2. Connect Serial OLED to USB port
3. Power on both displays

### 2. Software Setup
1. Upload Arduino code to ESP8266
2. Update WiFi credentials and verify IP address
3. Update serial port in Python scripts if needed
4. Test displays using `oled_test.py`

### 3. System Integration
1. Start Flask app: `python app.py`
2. Start entry scanner: `python rfid_sender.py`
3. Start exit scanner: `python rfid_reader.py`
4. Test with RFID cards

## Troubleshooting

### ESP8266 OLED Issues
- **Not connecting to WiFi**: Check credentials and network
- **IP not accessible**: Verify static IP configuration
- **Display not working**: Check I2C wiring and OLED address (0x3C)

### Serial OLED Issues
- **Port not found**: Check with `ls /dev/ttyUSB*`
- **Permission denied**: Run `sudo chmod 666 /dev/ttyUSB2`
- **No response**: Verify baud rate and serial protocol

### Network Issues
- **Timeout errors**: Increase timeout in Python scripts
- **Connection refused**: Check ESP8266 is powered and connected
- **Wrong IP**: Verify ESP8266 IP matches Python configuration

## Features

### Visual Feedback
- Immediate feedback on access attempts
- Clear success/failure indication
- User-friendly messages

### Error Handling
- Graceful degradation if displays are unavailable
- Timeout protection for network requests
- Serial port error recovery

### Customization
- Easy message customization
- Configurable display timing
- Adjustable font sizes and layouts

## Benefits

1. **Enhanced User Experience**: Visual feedback for all access attempts
2. **Security**: Clear indication of access status
3. **Debugging**: Visual confirmation of system operation
4. **Flexibility**: Different display types for different points
5. **Reliability**: Redundant display methods (WiFi + Serial)
