import serial
import serial.tools.list_ports
import requests
import time

# Update the serial port to match Raspberry Pi environment
SERIAL_PORT = '/dev/ttyUSB0'  # Use /dev/ttyAMA0 if needed
BAUD_RATE = 9600
FLASK_URL = 'http://127.0.0.1:5000'

# Serial OLED Configuration for Exit Point
OLED_SERIAL_PORT = '/dev/ttyUSB2'  # Serial port for OLED display

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
    # First validate the user
    access_granted, name, message = validate_user(unique_id)
    
    if not access_granted:
        print(f"Access Denied for RFID {unique_id}: {message}")
        display_exit_result(False, "Unknown", "Not Registered")
        return False
    
    print(f"Access Granted for {name} (RFID: {unique_id})")
    
    # Send the exit scan
    data = {'unique_id': unique_id, 'action': 'exit'}
    try:
        response = requests.post(f'{FLASK_URL}/scan', json=data)
        if response.status_code == 200:
            result = response.json()
            print(f"Exit logged successfully: {result.get('message', '')}")
            display_exit_result(True, name)
            return True
        else:
            result = response.json()
            error_msg = result.get('message', 'Exit failed')
            print(f"Exit failed: {error_msg}")
            
            # Handle specific error cases for exit
            if "no entry found" in error_msg.lower():
                display_exit_result(False, name, "Entry Not Found")
            else:
                display_exit_result(False, name, "Exit Failed")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error sending scan to Flask server: {e}")
        display_exit_result(False, name, "Server Error")
        return False

def send_to_serial_oled(message):
    """Send message to Serial OLED display for exit point"""
    try:
        with serial.Serial(OLED_SERIAL_PORT, BAUD_RATE, timeout=1) as oled_ser:
            # Clear display and send message
            oled_ser.write(b'\x0C')  # Clear screen command (may vary by OLED model)
            time.sleep(0.1)
            oled_ser.write(message.encode('utf-8'))
            print(f"Sent to Serial OLED: {message}")
            return True
    except Exception as e:
        print(f"Error sending to Serial OLED: {e}")
        return False

def display_exit_result(access_granted, user_name="Unknown", error_reason=""):
    """Display exit result on Serial OLED"""
    if access_granted:
        # Access Granted - Exit successful
        message = f"Access Granted\nDoor Opened\nGoodbye {user_name}"
        print(f"✅ EXIT: Access granted for {user_name}")
    else:
        # Access Denied - Exit failed
        if "entry not found" in error_reason.lower():
            message = f"Entry Not Found\nAccess Denied\nDoor Closed"
        else:
            message = f"Access Denied\nDoor Closed\n{error_reason}"
        print(f"❌ EXIT: Access denied - {error_reason}")
    
    # Send to Serial OLED
    send_to_serial_oled(message)
    
    # Keep message displayed for 3 seconds
    time.sleep(3)
    
    # Return to ready state
    send_to_serial_oled("EXIT SCANNER\nReady for scan...")

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

    # Initialize Serial OLED display
    print("Initializing Serial OLED display...")
    send_to_serial_oled("EXIT SCANNER\nReady for scan...")
    
    print("Listening for RFID scans... (action='exit')")
    try:
        while True:
            if ser.in_waiting:
                rfid_data = ser.readline().decode('utf-8').strip()
                if rfid_data:
                    print(f"Scanned RFID: {rfid_data}")
                    success = send_scan(rfid_data)
                    if success:
                        print("✓ Exit processed successfully")
                    else:
                        print("✗ Exit processing failed")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        if ser.is_open:
            ser.close()
            print("Serial port closed.")

if __name__ == '__main__':
    main()