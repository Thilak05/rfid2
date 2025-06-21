#!/usr/bin/env python3
"""
OLED Display Test Script
Test both ESP8266 OLED (entry) and Serial OLED (exit) displays with various messages.
"""

import serial
import requests
import time
import sys

# Configuration
ESP_IP = "192.168.0.10"
OLED_SERIAL_PORT = '/dev/ttyUSB2'  # Adjust as needed for your system
BAUD_RATE = 9600

def send_to_esp8266_oled(message):
    """Send message to ESP8266 OLED display (Entry Point)"""
    try:
        response = requests.post(f"http://{ESP_IP}/message", data=message, timeout=5)
        print(f"✓ ESP8266 Entry OLED: {response.status_code} - {response.text}")
        return True
    except Exception as e:
        print(f"✗ ESP8266 Entry OLED Error: {e}")
        return False

def send_to_serial_oled(message):
    """Send message to Serial OLED display (Exit Point)"""
    try:
        with serial.Serial(OLED_SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
            # Clear screen and send message
            ser.write(b'\x0C')  # Clear screen command
            time.sleep(0.1)
            ser.write(message.encode('utf-8'))
            print(f"✓ Serial Exit OLED: Message sent")
            return True
    except Exception as e:
        print(f"✗ Serial Exit OLED Error: {e}")
        return False

def test_entry_scenarios():
    """Test different entry scenarios on ESP8266 OLED"""
    print("\n=== Testing Entry Scenarios (ESP8266 OLED) ===")
    
    scenarios = [
        {
            "name": "Access Granted - Registered User",
            "message": "Access Granted\nDoor Opened\nWelcome Arun"
        },
        {
            "name": "Access Denied - Unregistered User", 
            "message": "Access Denied\nDoor Closed\nNot Registered"
        },
        {
            "name": "Access Denied - Already Inside",
            "message": "Access Denied\nDoor Closed\nAlready Inside"
        },
        {
            "name": "Server Error",
            "message": "Access Denied\nDoor Closed\nServer Error"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. Testing: {scenario['name']}")
        send_to_esp8266_oled(scenario['message'])
        time.sleep(4)  # Display for 4 seconds

def test_exit_scenarios():
    """Test different exit scenarios on Serial OLED"""
    print("\n=== Testing Exit Scenarios (Serial OLED) ===")
    
    scenarios = [
        {
            "name": "Exit Granted - Valid User",
            "message": "Access Granted\nDoor Opened\nGoodbye Thilak"
        },
        {
            "name": "Exit Denied - Entry Not Found",
            "message": "Entry Not Found\nAccess Denied\nDoor Closed"
        },
        {
            "name": "Exit Denied - Unregistered User",
            "message": "Access Denied\nDoor Closed\nNot Registered"
        },
        {
            "name": "Server Error",
            "message": "Access Denied\nDoor Closed\nServer Error"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. Testing: {scenario['name']}")
        send_to_serial_oled(scenario['message'])
        time.sleep(4)  # Display for 4 seconds

def test_ready_screens():
    """Test ready/idle screens"""
    print("\n=== Testing Ready Screens ===")
    
    # Entry scanner ready (ESP8266)
    print("\n1. Entry Scanner Ready (ESP8266)")
    send_to_esp8266_oled("ENTRY SCANNER\nReady for scan...")
    time.sleep(3)
    
    # Exit scanner ready (Serial)
    print("\n2. Exit Scanner Ready (Serial)")
    send_to_serial_oled("EXIT SCANNER\nReady for scan...")
    time.sleep(3)

def test_connectivity():
    """Test connectivity to both displays"""
    print("\n=== Testing Connectivity ===")
    
    print("1. Testing ESP8266 OLED connection...")
    esp_success = send_to_esp8266_oled("Connection Test\nESP8266 OLED\nEntry Point")
    
    print("2. Testing Serial OLED connection...")
    serial_success = send_to_serial_oled("Connection Test\nSerial OLED\nExit Point")
    
    if esp_success and serial_success:
        print("✓ Both displays are working!")
    elif esp_success:
        print("⚠ Only ESP8266 OLED is working")
    elif serial_success:
        print("⚠ Only Serial OLED is working")
    else:
        print("✗ Both displays failed")
    
    time.sleep(3)

def interactive_test():
    """Interactive test mode"""
    print("\n=== Interactive Test Mode ===")
    print("Choose display:")
    print("1. ESP8266 OLED (Entry)")
    print("2. Serial OLED (Exit)")
    print("3. Both")
    
    while True:
        choice = input("\nEnter choice (1-3) or 'quit': ")
        if choice.lower() == 'quit':
            break
            
        message = input("Enter message to display: ")
        
        if choice == '1':
            send_to_esp8266_oled(message)
        elif choice == '2':
            send_to_serial_oled(message)
        elif choice == '3':
            send_to_esp8266_oled(message)
            send_to_serial_oled(message)
        else:
            print("Invalid choice!")
        
        time.sleep(2)

def main():
    print("RFID OLED Display Test Script")
    print("============================")
    print("Entry Point: ESP8266 OLED (WiFi)")
    print("Exit Point: Serial OLED")
    print("============================")
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        if test_type == "connectivity":
            test_connectivity()
        elif test_type == "entry":
            test_entry_scenarios()
        elif test_type == "exit":
            test_exit_scenarios()
        elif test_type == "ready":
            test_ready_screens()
        elif test_type == "interactive":
            interactive_test()
        else:
            print("Usage: python oled_test.py [connectivity|entry|exit|ready|interactive]")
    else:
        # Run all tests
        test_connectivity()
        test_ready_screens()
        test_entry_scenarios()
        test_exit_scenarios()
        
        # End with ready screens
        print("\n=== Returning to Ready State ===")
        send_to_esp8266_oled("ENTRY SCANNER\nReady for scan...")
        send_to_serial_oled("EXIT SCANNER\nReady for scan...")

if __name__ == '__main__':
    main()
