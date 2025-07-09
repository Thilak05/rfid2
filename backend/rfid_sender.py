import requests
import time
import socket
import threading
import json
from datetime import datetime

# Configuration
FLASK_URL = 'http://127.0.0.1:5000'
ESP32_MAC = "E4:65:B8:27:73:08"  # ESP32 WROOM MAC address (for identification)
RASPBERRY_PI_MAC = "D8:3A:DD:78:01:07"  # Raspberry Pi MAC address
ESP32_LISTEN_PORT = 8080  # Port to listen for ESP32 data
ESP32_OLED_PORT = 80      # Port for sending OLED messages to ESP32

# Global variables
esp32_ip = None  # Will be discovered when ESP32 connects
running = True

def discover_esp32_ip():
    """Discover ESP32 IP address by MAC address"""
    try:
        # Use ARP table to find IP by MAC address
        import subprocess
        import re
        
        # Get ARP table
        result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        for line in lines:
            if ESP32_MAC.lower() in line.lower():
                # Extract IP address from ARP entry
                ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                if ip_match:
                    return ip_match.group(1)
        
        print(f"ESP32 with MAC {ESP32_MAC} not found in ARP table")
        return None
        
    except Exception as e:
        print(f"Error discovering ESP32 IP: {e}")
        return None

def ping_esp32(ip):
    """Ping ESP32 to verify it's reachable"""
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
    """Send scan data to Flask server after validation"""
    # First validate the user
    access_granted, name, message = validate_user(unique_id)
    
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
        display_entry_result(False, name, "Server Error")
        return False

def send_to_esp32_oled(message):
    """Send message to ESP32 OLED display for entry point"""
    global esp32_ip
    
    if not esp32_ip:
        print("ESP32 IP not available - cannot send OLED message")
        return False
        
    try:
        response = requests.post(f"http://{esp32_ip}:{ESP32_OLED_PORT}/message", 
                               data=message, timeout=5)
        print(f"✓ Sent to ESP32 OLED: {response.status_code} - {response.text}")
        return True
    except Exception as e:
        print(f"✗ Error sending to ESP32 OLED: {e}")
        return False

def display_entry_result(access_granted, user_name="Unknown", error_reason=""):
    """Display entry result on ESP32 OLED"""
    if access_granted:
        # Access Granted - Entry successful
        message = f"Access Granted\nWelcome {user_name}"
        print(f"✅ ENTRY: Access granted for {user_name}")
    else:
        # Access Denied - Entry failed
        message = f"Access Denied\n{error_reason}"
        print(f"❌ ENTRY: Access denied - {error_reason}")
    
    # Send to ESP32 OLED
    send_to_esp32_oled(message)
    
    # Keep message displayed for 3 seconds
    time.sleep(3)
    
    # Return to ready state
    send_to_esp32_oled("ENTRY SCANNER\nReady for scan...")

def handle_rfid_data(rfid_data, client_ip):
    """Process RFID data received from ESP32"""
    
    # Handle test connection
    if rfid_data == "TEST_CONNECTION":
        print(f"🔗 Test connection from ESP32 at {client_ip}")
        return True
    
    print(f"📡 Received RFID data from ESP32 ({client_ip}): {rfid_data}")
    
    # Verify this is our ESP32 by checking if IP matches discovered IP
    global esp32_ip
    if esp32_ip and client_ip != esp32_ip:
        print(f"⚠️  Warning: Data from unexpected IP {client_ip}, expected {esp32_ip}")
    
    # Process the RFID scan
    success = send_scan(rfid_data)
    if success:
        print("✓ Entry processed successfully")
    else:
        print("✗ Entry processing failed")
    
    return success

def rfid_server():
    """Server to receive RFID data from ESP32"""
    global running, esp32_ip
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind(('', ESP32_LISTEN_PORT))
        server_socket.listen(1)
        server_socket.settimeout(1.0)  # Non-blocking with timeout
        
        print(f"🌐 RFID Server listening on port {ESP32_LISTEN_PORT}")
        print(f"   Waiting for ESP32 ({ESP32_MAC}) to send RFID data...")
        
        while running:
            try:
                client_socket, client_address = server_socket.accept()
                client_ip = client_address[0]
                
                # Update ESP32 IP if not set
                if not esp32_ip:
                    esp32_ip = client_ip
                    print(f"📍 ESP32 connected from: {esp32_ip}")
                
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
        print(f"Failed to start RFID server: {e}")
    finally:
        server_socket.close()

def initialize_esp32():
    """Initialize ESP32 connection and OLED display"""
    global esp32_ip
    
    print("🔍 Discovering ESP32...")
    
    # Try to discover ESP32 IP
    esp32_ip = discover_esp32_ip()
    
    if esp32_ip:
        print(f"✓ Found ESP32 at IP: {esp32_ip}")
        
        # Test connectivity
        if ping_esp32(esp32_ip):
            print("✓ ESP32 is reachable")
            
            # Initialize OLED display
            print("📺 Initializing ESP32 OLED display...")
            if send_to_esp32_oled("ENTRY SCANNER\nReady for scan..."):
                print("✓ ESP32 OLED initialized successfully")
                return True
            else:
                print("⚠️  ESP32 OLED initialization failed")
                return False
        else:
            print("✗ ESP32 is not reachable")
            esp32_ip = None
            return False
    else:
        print(f"✗ ESP32 with MAC {ESP32_MAC} not found")
        print("   The ESP32 will be discovered when it connects")
        return False

def main():
    """Main function - network-based RFID entry system"""
    global running
    print("=" * 60)
    print("🔐 RFID Entry System (Network-based)")
    print(f"   ESP32 MAC: {ESP32_MAC}")
    print(f"   Raspberry Pi MAC: {RASPBERRY_PI_MAC}")
    print(f"   Listen Port: {ESP32_LISTEN_PORT}")
    print(f"   OLED Port: {ESP32_OLED_PORT}")
    print("=" * 60)
    
    # Try to initialize ESP32 connection
    initialize_esp32()
    
    # Start the RFID server in a separate thread
    server_thread = threading.Thread(target=rfid_server, daemon=True)
    server_thread.start()
    
    print("\n🚀 Entry system started!")
    print("   - ESP32 should send RFID data to this system")
    print("   - OLED messages will be sent back to ESP32")
    print("   - Press Ctrl+C to stop")
    
    try:
        # Keep main thread alive and handle user input
        while True:
            time.sleep(1)
            
            # Optionally, you can add periodic health checks here
            # if esp32_ip and time.time() % 30 == 0:  # Every 30 seconds
            #     ping_esp32(esp32_ip)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping RFID Entry System...")
        running = False
        
        # Wait for server thread to finish
        server_thread.join(timeout=2)
        
        print("✓ RFID Entry System stopped")

if __name__ == '__main__':
    main()