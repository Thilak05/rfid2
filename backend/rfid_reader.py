import requests
import time
import socket
import threading
import json
from datetime import datetime

# Configuration
FLASK_URL = 'http://127.0.0.1:5000'
ESP32_EXIT_MAC = "E0:5A:1B:A2:A5:B4"  # ESP32 EXIT scanner MAC address (for identification)
RASPBERRY_PI_MAC = "D8:3A:DD:78:01:07"  # Raspberry Pi MAC address
ESP32_LISTEN_PORT = 8081  # Port to listen for ESP32 EXIT data (different from entry port)
ESP32_OLED_PORT = 80      # Port for sending OLED messages to ESP32 EXIT

# Global variables
esp32_exit_ip = None  # Will be discovered when ESP32 EXIT connects
running = True

def discover_esp32_exit_ip():
    """Discover ESP32 EXIT IP address by MAC address"""
    try:
        # Use ARP table to find IP by MAC address
        import subprocess
        import re
        
        # Get ARP table
        result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        for line in lines:
            if ESP32_EXIT_MAC.lower() in line.lower():
                # Extract IP address from ARP entry
                ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                if ip_match:
                    return ip_match.group(1)
        
        print(f"ESP32 EXIT with MAC {ESP32_EXIT_MAC} not found in ARP table")
        return None
        
    except Exception as e:
        print(f"Error discovering ESP32 EXIT IP: {e}")
        return None

def ping_esp32_exit(ip):
    """Ping ESP32 EXIT to verify it's reachable"""
    try:
        import subprocess
        result = subprocess.run(['ping', '-c', '1', ip], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False

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
    """Send exit scan data to Flask server after validation"""
    # First validate the user
    access_granted, name, message = validate_user(unique_id)
    
    if not access_granted:
        print(f"Access Denied for RFID {unique_id}: {message}")
        display_exit_result(False, "Unknown", "Not Registered")
        return False
    
    print(f"Access Granted for {name} (RFID: {unique_id})")
    
    # Send the exit scan with ESP32 MAC address
    data = {
        'unique_id': unique_id, 
        'action': 'exit',
        'device_mac': ESP32_EXIT_MAC
    }
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
                display_exit_result(False, name, "No Entry Found")
            else:
                display_exit_result(False, name, "Exit Failed")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error sending scan to Flask server: {e}")
        display_exit_result(False, name, "Server Error")
        return False

def send_to_esp32_exit_oled(message):
    """Send message to ESP32 EXIT OLED display"""
    global esp32_exit_ip
    
    if not esp32_exit_ip:
        print("ESP32 EXIT IP not available - cannot send OLED message")
        return False
        
    try:
        response = requests.post(f"http://{esp32_exit_ip}:{ESP32_OLED_PORT}/message", 
                               data=message, timeout=5)
        print(f"✓ Sent to ESP32 EXIT OLED: {response.status_code} - {response.text}")
        return True
    except Exception as e:
        print(f"✗ Error sending to ESP32 EXIT OLED: {e}")
        return False

def display_exit_result(access_granted, user_name="Unknown", error_reason=""):
    """Display exit result on ESP32 EXIT OLED"""
    if access_granted:
        # Access Granted - Exit successful
        message = f"Exit Granted\nDoor Opened\nGoodbye {user_name}"
        print(f"✅ EXIT: Access granted for {user_name}")
    else:
        # Access Denied - Exit failed
        if "no entry found" in error_reason.lower():
            message = f"No Entry Found\nAccess Denied\n{user_name}"
        else:
            message = f"Access Denied\nDoor Closed\n{error_reason}"
        print(f"❌ EXIT: Access denied - {error_reason}")
    
    # Send to ESP32 EXIT OLED
    send_to_esp32_exit_oled(message)
    
    # Keep message displayed for 3 seconds
    time.sleep(3)
    
    # Return to ready state
    send_to_esp32_exit_oled("EXIT SCANNER\nReady for scan...")

def handle_rfid_data(rfid_data, client_ip):
    """Process RFID data received from ESP32 EXIT"""
    
    # Handle test connection
    if rfid_data == "TEST_CONNECTION":
        print(f"🔗 Test connection from ESP32 EXIT at {client_ip}")
        return True
    
    print(f"📡 Received RFID data from ESP32 EXIT ({client_ip}): {rfid_data}")
    
    # Verify this is our ESP32 EXIT by checking if IP matches discovered IP
    global esp32_exit_ip
    if esp32_exit_ip and client_ip != esp32_exit_ip:
        print(f"⚠️  Warning: Data from unexpected IP {client_ip}, expected {esp32_exit_ip}")
    
    # Process the RFID scan for EXIT
    success = send_scan(rfid_data)
    if success:
        print("✓ Exit processed successfully")
    else:
        print("✗ Exit processing failed")
    
    return success

def rfid_exit_server():
    """Server to receive RFID data from ESP32 EXIT"""
    global running, esp32_exit_ip
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind(('', ESP32_LISTEN_PORT))
        server_socket.listen(1)
        server_socket.settimeout(1.0)  # Non-blocking with timeout
        
        print(f"🌐 RFID EXIT Server listening on port {ESP32_LISTEN_PORT}")
        print(f"   Waiting for ESP32 EXIT ({ESP32_EXIT_MAC}) to send RFID data...")
        
        while running:
            try:
                client_socket, client_address = server_socket.accept()
                client_ip = client_address[0]
                
                # Update ESP32 EXIT IP if not set
                if not esp32_exit_ip:
                    esp32_exit_ip = client_ip
                    print(f"📍 ESP32 EXIT connected from: {esp32_exit_ip}")
                
                # Receive data
                data = client_socket.recv(1024).decode('utf-8').strip()
                if data:
                    # Handle the RFID data
                    handle_rfid_data(data, client_ip)
                    
                    # Send acknowledgment
                    client_socket.send(b"OK")
                
                client_socket.close()
                
            except socket.timeout:
                # Timeout is normal - allows checking running flag
                continue
            except Exception as e:
                if running:  # Only print errors if we're still supposed to be running
                    print(f"Server error: {e}")
                
    except Exception as e:
        print(f"Failed to start RFID EXIT server: {e}")
    finally:
        server_socket.close()

def initialize_esp32_exit():
    """Initialize ESP32 EXIT connection and OLED display"""
    global esp32_exit_ip
    
    print("🔍 Discovering ESP32 EXIT...")
    
    # Try to discover ESP32 EXIT IP
    esp32_exit_ip = discover_esp32_exit_ip()
    
    if esp32_exit_ip:
        print(f"✓ Found ESP32 EXIT at IP: {esp32_exit_ip}")
        
        # Test connectivity
        if ping_esp32_exit(esp32_exit_ip):
            print("✓ ESP32 EXIT is reachable")
            
            # Initialize OLED display
            print("📺 Initializing ESP32 EXIT OLED display...")
            if send_to_esp32_exit_oled("EXIT SCANNER\nReady for scan..."):
                print("✓ ESP32 EXIT OLED initialized successfully")
                return True
            else:
                print("⚠️  ESP32 EXIT OLED initialization failed")
                return False
        else:
            print("✗ ESP32 EXIT is not reachable")
            esp32_exit_ip = None
            return False
    else:
        print(f"✗ ESP32 EXIT with MAC {ESP32_EXIT_MAC} not found")
        print("   The ESP32 EXIT will be discovered when it connects")
        return False

def main():
    """Main function - network-based RFID exit system"""
    global running
    print("=" * 60)
    print("🚪 RFID Exit System (Network-based)")
    print(f"   ESP32 EXIT MAC: {ESP32_EXIT_MAC}")
    print(f"   Raspberry Pi MAC: {RASPBERRY_PI_MAC}")
    print(f"   Listen Port: {ESP32_LISTEN_PORT}")
    print(f"   OLED Port: {ESP32_OLED_PORT}")
    print("=" * 60)
    
    # Try to initialize ESP32 EXIT connection
    initialize_esp32_exit()
    
    # Start the RFID EXIT server in a separate thread
    server_thread = threading.Thread(target=rfid_exit_server, daemon=True)
    server_thread.start()
    
    print("\n🚀 Exit system started!")
    print("   - ESP32 EXIT should send RFID data to this system")
    print("   - OLED messages will be sent back to ESP32 EXIT")
    print("   - Press Ctrl+C to stop")
    
    try:
        # Keep main thread alive and handle user input
        while True:
            time.sleep(1)
            
            # Optionally, you can add periodic health checks here
            # if esp32_exit_ip and time.time() % 30 == 0:  # Every 30 seconds
            #     ping_esp32_exit(esp32_exit_ip)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping RFID Exit System...")
        running = False
        
        # Wait for server thread to finish
        server_thread.join(timeout=2)
        
        print("✓ RFID Exit System stopped")

if __name__ == '__main__':
    main()