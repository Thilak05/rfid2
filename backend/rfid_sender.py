import requests
import time
import socket
import threading
import json
from datetime import datetime

# Configuration
FLASK_URL = 'http://127.0.0.1:5000'
ESP8266_MAC = "C4:5B:BE:74:FC:39"  # ESP8266 MAC address (for identification)
RASPBERRY_PI_MAC = "D8:3A:DD:78:01:07"  # Raspberry Pi MAC address
ESP8266_LISTEN_PORT = 8080  # Port to listen for ESP8266 data
ESP8266_OLED_PORT = 80      # Port for sending OLED messages to ESP8266

# Global variables
esp8266_ip = None  # Will be discovered when ESP8266 connects
running = True

def discover_esp8266_ip():
    """Discover ESP8266 IP address by MAC address"""
    try:
        # Use ARP table to find IP by MAC address
        import subprocess
        import re
        
        # Get ARP table
        result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        for line in lines:
            if ESP8266_MAC.lower() in line.lower():
                # Extract IP address from ARP entry
                ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                if ip_match:
                    return ip_match.group(1)
        
        print(f"ESP8266 with MAC {ESP8266_MAC} not found in ARP table")
        return None
        
    except Exception as e:
        print(f"Error discovering ESP8266 IP: {e}")
        return None

def ping_esp8266(ip):
    """Ping ESP8266 to verify it's reachable"""
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

def send_to_esp8266_oled(message):
    """Send message to ESP8266 OLED display for entry point"""
    global esp8266_ip
    
    if not esp8266_ip:
        print("ESP8266 IP not available - cannot send OLED message")
        return False
        
    try:
        response = requests.post(f"http://{esp8266_ip}:{ESP8266_OLED_PORT}/message", 
                               data=message, timeout=5)
        print(f"✓ Sent to ESP8266 OLED: {response.status_code} - {response.text}")
        return True
    except Exception as e:
        print(f"✗ Error sending to ESP8266 OLED: {e}")
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

def handle_rfid_data(rfid_data, client_ip):
    """Process RFID data received from ESP8266"""
    
    # Handle test connection
    if rfid_data == "TEST_CONNECTION":
        print(f"🔗 Test connection from ESP8266 at {client_ip}")
        return True
    
    print(f"📡 Received RFID data from ESP8266 ({client_ip}): {rfid_data}")
    
    # Verify this is our ESP8266 by checking if IP matches discovered IP
    global esp8266_ip
    if esp8266_ip and client_ip != esp8266_ip:
        print(f"⚠️  Warning: Data from unexpected IP {client_ip}, expected {esp8266_ip}")
    
    # Process the RFID scan
    success = send_scan(rfid_data)
    if success:
        print("✓ Entry processed successfully")
    else:
        print("✗ Entry processing failed")
    
    return success

def rfid_server():
    """Server to receive RFID data from ESP8266"""
    global running, esp8266_ip
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind(('', ESP8266_LISTEN_PORT))
        server_socket.listen(1)
        server_socket.settimeout(1.0)  # Non-blocking with timeout
        
        print(f"🌐 RFID Server listening on port {ESP8266_LISTEN_PORT}")
        print(f"   Waiting for ESP8266 ({ESP8266_MAC}) to send RFID data...")
        
        while running:
            try:
                client_socket, client_address = server_socket.accept()
                client_ip = client_address[0]
                
                # Update ESP8266 IP if not set
                if not esp8266_ip:
                    esp8266_ip = client_ip
                    print(f"📍 ESP8266 connected from: {esp8266_ip}")
                
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

def initialize_esp8266():
    """Initialize ESP8266 connection and OLED display"""
    global esp8266_ip
    
    print("🔍 Discovering ESP8266...")
    
    # Try to discover ESP8266 IP
    esp8266_ip = discover_esp8266_ip()
    
    if esp8266_ip:
        print(f"✓ Found ESP8266 at IP: {esp8266_ip}")
        
        # Test connectivity
        if ping_esp8266(esp8266_ip):
            print("✓ ESP8266 is reachable")
            
            # Initialize OLED display
            print("📺 Initializing ESP8266 OLED display...")
            if send_to_esp8266_oled("ENTRY SCANNER\nReady for scan..."):
                print("✓ ESP8266 OLED initialized successfully")
                return True
            else:
                print("⚠️  ESP8266 OLED initialization failed")
                return False
        else:
            print("✗ ESP8266 is not reachable")
            esp8266_ip = None
            return False
    else:
        print(f"✗ ESP8266 with MAC {ESP8266_MAC} not found")
        print("   The ESP8266 will be discovered when it connects")
        return False

def main():
    """Main function - network-based RFID entry system"""
    global running
    print("=" * 60)
    print("🔐 RFID Entry System (Network-based)")
    print(f"   ESP8266 MAC: {ESP8266_MAC}")
    print(f"   Raspberry Pi MAC: {RASPBERRY_PI_MAC}")
    print(f"   Listen Port: {ESP8266_LISTEN_PORT}")
    print(f"   OLED Port: {ESP8266_OLED_PORT}")
    print("=" * 60)
    
    # Try to initialize ESP8266 connection
    initialize_esp8266()
    
    # Start the RFID server in a separate thread
    server_thread = threading.Thread(target=rfid_server, daemon=True)
    server_thread.start()
    
    print("\n🚀 Entry system started!")
    print("   - ESP8266 should send RFID data to this system")
    print("   - OLED messages will be sent back to ESP8266")
    print("   - Press Ctrl+C to stop")
    
    try:
        # Keep main thread alive and handle user input
        while True:
            time.sleep(1)
            
            # Optionally, you can add periodic health checks here
            # if esp8266_ip and time.time() % 30 == 0:  # Every 30 seconds
            #     ping_esp8266(esp8266_ip)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping RFID Entry System...")
        running = False
        
        # Wait for server thread to finish
        server_thread.join(timeout=2)
        
        print("✓ RFID Entry System stopped")

if __name__ == '__main__':
    main()