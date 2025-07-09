# ESP32 Door Controller Setup Instructions

## Overview
Your ESP32 door controller is already configured to work with your Raspberry Pi RFID system. Here's what you need to know:

## Configuration Details
- **Raspberry Pi MAC**: `D8:3A:DD:78:01:07`
- **ESP32 Door Controller**: Uses the existing complex controller (`esp32_solenoidal_controller.ino`)
- **Relay Pin**: GPIO23 (LOW = door open, HIGH = door closed)
- **Door Open Duration**: 5 seconds (auto-close)
- **Registration**: Only registered users can unlock the door

## How It Works

### 1. User Registration Check
- When a user scans their RFID card on entry/exit scanner
- Flask server checks if user is registered and active in database
- If not registered: Access denied, door stays locked
- If registered: Access granted, door unlock command sent

### 2. Door Control Flow
```
User Scans RFID → Server Validates User → If Valid: Send Unlock Command → ESP32 Opens Door → Auto-close after 5 seconds
```

### 3. Entry Process
1. User scans RFID at entry scanner
2. Server validates user is registered and not already inside
3. If valid: Server sends POST request to `http://ESP32_IP/unlock_entry`
4. ESP32 opens door (GPIO23 LOW) for 5 seconds
5. Door auto-closes (GPIO23 HIGH)
6. Buzzer beeps once for entry

### 4. Exit Process
1. User scans RFID at exit scanner
2. Server validates user is registered and currently inside
3. If valid: Server sends POST request to `http://ESP32_IP/unlock_exit`
4. ESP32 opens door (GPIO23 LOW) for 5 seconds
5. Door auto-closes (GPIO23 HIGH)
6. Buzzer beeps twice for exit

## Setup Steps

### 1. Update ESP32 MAC Address
In `app.py`, update the door controller MAC address to match your ESP32:
```python
DOOR_CONTROLLER_MAC = "YOUR_ESP32_MAC_ADDRESS_HERE"  # Replace with actual MAC
```

### 2. Flash ESP32
Upload the `esp32_solenoidal_controller.ino` to your ESP32

### 3. Check Serial Monitor
The ESP32 will display:
- Its MAC address
- WiFi connection status
- IP address
- Registration attempt with Flask server

### 4. Hardware Connections
- GPIO23 → Relay control pin
- Relay → Solenoid lock
- GPIO25 → Buzzer (optional)
- GPIO2 → Status LED (built-in)

### 5. Test the System
1. Start the Flask server: `python app.py`
2. Register a test user via the web interface
3. Scan the registered RFID card
4. Door should open for 5 seconds, then close

## Troubleshooting

### ESP32 Not Registering
- Check if ESP32 and Raspberry Pi are on same network
- Verify Flask server is running on port 5000
- Check serial monitor for connection messages

### Door Not Opening
- Verify relay connections to GPIO23
- Check if ESP32 received unlock command (serial monitor)
- Test door controller web interface at `http://ESP32_IP`

### Access Denied
- User must be registered in the database
- User status must be "active"
- Check user registration via web interface

## API Endpoints
The ESP32 provides these endpoints:
- `POST /unlock_entry` - Opens door for entry (called by Flask server)
- `POST /unlock_exit` - Opens door for exit (called by Flask server)
- `POST /lock` - Closes door immediately
- `GET /status` - Get door status
- `GET /` - Web interface for manual control

## Security Features
- ✅ Only registered users can unlock door
- ✅ User must have "active" status
- ✅ Entry/exit tracking prevents duplicate entries
- ✅ All access attempts are logged
- ✅ Auto-lock after 5 seconds
- ✅ Buzzer feedback for operations
