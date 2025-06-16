import serial
import serial.tools.list_ports
import requests
import time

# Update the serial port to match Raspberry Pi environment
SERIAL_PORT = '/dev/ttyS0'  # Use /dev/ttyAMA0 if needed
BAUD_RATE = 9600
FLASK_URL = 'http://127.0.0.1:5000/scan'

USER_MAP = {
    '0009334653': 'Arun',
    '080058DBB1': 'Thilak',
    '080058DD98': 'Hari',
}

def list_available_ports():
    """List all available serial ports"""
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

def send_scan(unique_id):
    name = USER_MAP.get(unique_id, 'Unknown')
    data = {'name': name, 'unique_id': unique_id, 'action': 'entry'}
    try:
        response = requests.post(FLASK_URL, json=data)
        print(f"Sent to Flask: {data} → Response: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending data to Flask server: {e}")

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
        print(f"Connected to {SERIAL_PORT}")
    except serial.SerialException as e:
        print(f"Connection failed: {e}")
        return

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
                        send_scan(rfid_data)
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