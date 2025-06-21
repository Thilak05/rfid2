import serial
import serial.tools.list_ports
import requests
import time

# Update the serial port to match Raspberry Pi environment
SERIAL_PORT = '/dev/ttyUSB1'  # Use /dev/ttyAMA0 if needed
BAUD_RATE = 9600
FLASK_URL = 'http://127.0.0.1:5000'
ESP_IP = "192.168.0.10"  # ESP8266 OLED IP for entry point

# ESP8266 OLED Configuration for Entry Point
ESP_IP = "192.168.0.10"

def list_available_ports():
    """List all available serial ports"""
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

def validate_user(unique_id):
    """Validate user with the database"""
    data = {'unique_id': unique_id}
    try:
        response = requests.post(f'{FLASK_URL}/api/validate_user', json=data)
        if response.status_code == 200:
            result = response.json()
            return result.get('access_granted', False), result.get('name', 'Unknown'), result.get('message', '')
        else:
            result = response.json()
            return False, 'Unknown', result.get('message', 'Access Denied')
    except requests.exceptions.RequestException as e:
        print(f"Error validating user: {e}")
        return False, 'Unknown', 'Server connection error'

def send_scan(unique_id):
    """Send scan data to Flask server after validation"""
    # First validate the user    access_granted, name, message = validate_user(unique_id)
    
    if not access_granted:
        print(f"Access Denied for RFID {unique_id}: {message}")
        display_entry_result(False, "Unknown", "Not Registered")
        return False
    
    print(f"Access Granted for {name} (RFID: {unique_id})")
    
    # Send the entry scan
    data = {'unique_id': unique_id, 'action': 'entry'}
    try:
        response = requests.post(f'{FLASK_URL}/scan', json=data)
        if response.status_code == 200:
            result = response.json()
            print(f"Entry logged successfully: {result.get('message', '')}")
            display_entry_result(True, name)
            return True
        else:
            result = response.json()
            error_msg = result.get('message', 'Entry failed')
            print(f"Entry failed: {error_msg}")
            
            # Handle specific error cases
            if "already inside" in error_msg.lower():
                display_entry_result(False, name, "Already Inside")
            else:
                display_entry_result(False, name, "Entry Failed")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error sending scan to Flask server: {e}")
        return False

def send_to_esp8266_oled(message):
    """Send message to ESP8266 OLED display for entry point"""
    try:
        response = requests.post(f"http://{ESP_IP}/message", data=message, timeout=5)
        print(f"Sent to ESP8266 OLED: {response.status_code} - {response.text}")
        return True
    except Exception as e:
        print(f"Error sending to ESP8266 OLED: {e}")
        return False

def display_entry_result(access_granted, user_name="Unknown", error_reason=""):
    """Display entry result on ESP8266 OLED"""
    if access_granted:
        # Access Granted - Entry successful
        message = f"Access Granted\nDoor Opened\nWelcome {user_name}"
        print(f"✅ ENTRY: Access granted for {user_name}")
    else:
        # Access Denied - Entry failed
        message = f"Access Denied\nDoor Closed\n{error_reason}"
        print(f"❌ ENTRY: Access denied - {error_reason}")
    
    # Send to ESP8266 OLED
    send_to_esp8266_oled(message)
    
    # Keep message displayed for 3 seconds
    time.sleep(3)
    
    # Return to ready state
    send_to_esp8266_oled("ENTRY SCANNER\nReady for scan...")

def main():
    # List available ports
    available_ports = list_available_ports()
    print("Available serial ports:")
    for port in available_ports:
        print(f"  {port}")

    if SERIAL_PORT not in available_ports:
        print(f"{SERIAL_PORT} not found. Update SERIAL_PORT or check connections.")
        return

    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to RFID scanner on {SERIAL_PORT}")
    except serial.SerialException as e:
        print(f"Connection failed: {e}")
        return

    # Initialize ESP8266 OLED display
    print("Initializing ESP8266 OLED display...")
    send_to_esp8266_oled("ENTRY SCANNER\nReady for scan...")
    
    print("Listening for RFID scans... (action='entry')")
    try:
        while True:
            if ser.in_waiting:
                raw_data = ser.readline()  # Get raw bytes from serial
                try:
                    # Attempt to decode the raw bytes into a UTF-8 string
                    rfid_data = raw_data.decode('utf-8', errors='ignore').strip()
                    if rfid_data:
                        print(f"Scanned RFID: {rfid_data}")
                        success = send_scan(rfid_data)
                        if success:
                            print("✓ Entry processed successfully")
                        else:
                            print("✗ Entry processing failed")
                except UnicodeDecodeError as e:
                    print(f"Unicode decode error: {e}")
                    # Optionally, you can print the raw data here for debugging
                    print(f"Raw bytes received: {raw_data}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        if ser.is_open:
            ser.close()
            print("Serial port closed.")

if __name__ == '__main__':
    main()