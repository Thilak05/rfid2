# Updated ESP8266 Setup with MAC Address Discovery

## Key Changes

The ESP8266 now discovers the Raspberry Pi by its MAC address instead of using a hardcoded IP address.

## Configuration

### Raspberry Pi MAC Address
- **MAC**: `D8:3A:DD:78:01:07`
- **Discovery**: ESP8266 scans network to find this MAC
- **Communication**: Once found, uses discovered IP for RFID data

### ESP8266 MAC Address  
- **MAC**: `C4:5B:BE:74:FC:39`
- **Purpose**: Python identifies this ESP8266
- **Communication**: Receives OLED messages from Python

## How It Works

1. **ESP8266 startup**: Connects to WiFi
2. **Network scan**: ESP8266 scans network for Raspberry Pi MAC `D8:3A:DD:78:01:07`
3. **Discovery**: Tests each IP to find the Python server
4. **Connection**: Once found, establishes communication
5. **RFID processing**: Sends RFID data to discovered Pi IP
6. **OLED updates**: Receives display messages from Pi

## Arduino Code Changes

```cpp
// NEW: Raspberry Pi identification
const char* raspberryPiMAC = "D8:3A:DD:78:01:07";
String raspberryPiIP = "";  // Discovered automatically

// Functions added:
String discoverRaspberryPiIP();  // Scans network for Pi
bool testPythonServer(String ip); // Verifies Python server
void discoverAndConnectToPi();   // Main discovery function
```

## Expected Behavior

### ESP8266 Startup
```
ESP8266 RFID Entry
Connecting WiFi...
WiFi connected!
IP address: 192.168.1.150
MAC address: C4:5B:BE:74:FC:39

🔍 Starting Raspberry Pi discovery...
Target MAC: D8:3A:DD:78:01:07
🔍 Discovering Raspberry Pi by MAC address...
Scanning network: 192.168.1.1-254
✓ Found responsive device at: 192.168.1.100
✓ Found Raspberry Pi at: 192.168.1.100
✓ Connected to Raspberry Pi at: 192.168.1.100

OLED Display: "ENTRY SCANNER\nPi: 192.168.1.100\nReady for scan..."
```

### RFID Scan Process
```
RFID scanned: A1B2C3D4
Connected to Raspberry Pi: 192.168.1.100
Pi response: OK

OLED Display: "Sent to Pi!\nIP: 192.168.1.100\nA1B2C3D4"
```

## Benefits

1. **No hardcoded IPs**: ESP8266 finds Pi automatically
2. **Network flexibility**: Works on any network configuration
3. **Fault tolerance**: Re-discovers Pi if connection lost
4. **MAC-based identification**: More reliable than IP addresses
5. **Visual feedback**: OLED shows discovery status

## Setup Steps

1. **Update ESP8266 code**: Already done - MAC addresses configured
2. **Flash ESP8266**: Upload `esp8266_rfid_entry.ino`
3. **Update WiFi credentials**: Set your network SSID/password
4. **Start Python server**: Run `python3 rfid_sender.py`
5. **Test**: ESP8266 should automatically find and connect to Pi

## Troubleshooting

### Pi Not Found
- Check Raspberry Pi MAC address: `ip link show`
- Ensure both devices on same network
- Verify Python server is running on port 8080

### Discovery Slow
- Normal behavior - scans 254 IP addresses
- Takes 1-3 minutes on first connection
- Subsequent connections are instant (IP cached)

### Connection Lost
- ESP8266 automatically re-discovers Pi
- OLED shows "Searching for Pi..." during discovery
- No manual intervention required

The system now provides fully automatic network discovery based on MAC addresses!
