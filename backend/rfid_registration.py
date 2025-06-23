#!/usr/bin/env python3
"""
RFID User Registration System
Connects to RFID reader on ttyUSB0 for registering new users
"""

import serial
import serial.tools.list_ports
import requests
import time
import sys

# Configuration
SERIAL_PORT = '/dev/ttyUSB0'  # RFID reader port for registration (Linux)
BAUD_RATE = 9600
FLASK_URL = 'http://127.0.0.1:5000'

def list_available_ports():
    """List all available serial ports"""
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

def register_user(rfid_id):
    """Register a new user with the given RFID ID"""
    print(f"\n📝 Registering new user with RFID: {rfid_id}")
    
    # Get user details
    try:
        name = input("Enter user's full name: ").strip()
        if not name:
            print("❌ Name cannot be empty")
            return False
        
        email = input("Enter user's email (optional): ").strip()
        phone = input("Enter user's phone (optional): ").strip()
        
        # Prepare user data
        user_data = {
            'name': name,
            'unique_id': rfid_id,
            'email': email if email else '',
            'phone': phone if phone else '',
            'status': 'active'
        }
        
        # Send registration request to Flask server
        response = requests.post(f'{FLASK_URL}/api/users', json=user_data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ User registered successfully!")
            print(f"   Name: {name}")
            print(f"   RFID: {rfid_id}")
            print(f"   Email: {email if email else 'Not provided'}")
            print(f"   Phone: {phone if phone else 'Not provided'}")
            print(f"   User ID: {result.get('user_id', 'Unknown')}")
            return True
        else:
            result = response.json()
            error_msg = result.get('message', 'Registration failed')
            print(f"❌ Registration failed: {error_msg}")
            
            if "already exists" in error_msg.lower():
                print(f"   RFID {rfid_id} is already registered to another user")
                print(f"   Use the web interface to update existing users")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error connecting to server: {e}")
        print(f"   Make sure Flask server is running at {FLASK_URL}")
        return False
    except KeyboardInterrupt:
        print(f"\n⚠️  Registration cancelled by user")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def check_existing_user(rfid_id):
    """Check if RFID is already registered"""
    try:
        response = requests.post(f'{FLASK_URL}/api/validate_user', 
                               json={'unique_id': rfid_id}, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('access_granted'):
                print(f"ℹ️  RFID {rfid_id} is already registered to: {result.get('name', 'Unknown')}")
                return True
        return False
        
    except Exception as e:
        print(f"⚠️  Could not check existing user: {e}")
        return False

def test_flask_connection():
    """Test connection to Flask server"""
    try:
        response = requests.get(f'{FLASK_URL}/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Connected to Flask server: {data.get('service', 'RFID System')}")
            return True
        else:
            print(f"❌ Flask server responded with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to Flask server: {e}")
        print(f"   Make sure server is running at {FLASK_URL}")
        return False

def get_user_stats():
    """Get current user statistics"""
    try:
        response = requests.get(f'{FLASK_URL}/api/users', timeout=5)
        if response.status_code == 200:
            users = response.json()
            active_users = [u for u in users if u.get('status') == 'active']
            print(f"📊 Current users: {len(users)} total, {len(active_users)} active")
            return True
        else:
            print(f"⚠️  Could not get user statistics")
            return False
    except Exception as e:
        print(f"⚠️  Error getting user stats: {e}")
        return False

def main():
    """Main registration function"""
    print("=" * 60)
    print("📝 RFID User Registration System")
    print(f"   RFID Reader Port: {SERIAL_PORT}")
    print(f"   Flask Server: {FLASK_URL}")
    print("=" * 60)
    
    # Test Flask connection
    if not test_flask_connection():
        print("\n💡 Start Flask server first: python app.py")
        return False    # Get current stats
    get_user_stats()
    
    # List available ports
    available_ports = list_available_ports()
    print(f"\nAvailable serial ports:")
    for port in available_ports:
        print(f"  📱 {port}")
    
    if SERIAL_PORT not in available_ports:
        print(f"\n❌ {SERIAL_PORT} not found!")
        print("   Common fixes:")
        print("   1. Check RFID reader connection")
        print("   2. Try different USB port")
        print("   3. Check device permissions: sudo chmod 666 /dev/ttyUSB*")
        print("   4. Add user to dialout group: sudo usermod -a -G dialout $USER")
        print("   5. Try /dev/ttyUSB1, /dev/ttyUSB2, etc.")
        return False
    
    # Connect to RFID reader
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"✅ Connected to RFID reader on {SERIAL_PORT}")
    except serial.SerialException as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    print("\n🎯 Ready for RFID registration!")
    print("   1. Scan an RFID card to register a new user")
    print("   2. Press Ctrl+C to exit")
    print("   3. Make sure the card is not already registered")
    print("-" * 60)
    
    try:
        scan_count = 0
        while True:
            if ser.in_waiting > 0:
                try:
                    # Read RFID data
                    raw_data = ser.readline()
                    if raw_data:
                        try:
                            rfid_data = raw_data.decode('utf-8', errors='ignore').strip()
                        except:
                            rfid_data = raw_data.decode('ascii', errors='ignore').strip()
                        
                        # Clean the RFID data
                        rfid_data = ''.join(c for c in rfid_data if c.isalnum())
                        
                        if rfid_data and len(rfid_data) >= 8:
                            scan_count += 1
                            print(f"\n🔍 RFID Scan #{scan_count}: {rfid_data}")
                            
                            # Check if already registered
                            if check_existing_user(rfid_data):
                                print("   Use web interface to update existing users")
                                continue
                            
                            # Register new user
                            if register_user(rfid_data):
                                print(f"\n✅ Registration completed successfully!")
                            else:
                                print(f"\n❌ Registration failed - try again")
                            
                            print("-" * 60)
                            print("🎯 Ready for next RFID scan...")
                        else:
                            print(f"⚠️  Invalid RFID data: {rfid_data}")
                            
                except Exception as e:
                    print(f"Error reading RFID data: {e}")
                    continue
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print(f"\n\n🛑 Registration system stopped by user")
        
    finally:
        if ser.is_open:
            ser.close()
            print("📱 Serial port closed")
    
    print("👋 Thank you for using RFID Registration System!")
    return True

def show_help():
    """Show help information"""
    print("RFID User Registration System")
    print("")
    print("Usage:")
    print("  python rfid_registration.py        - Start registration system")
    print("  python rfid_registration.py --help - Show this help")
    print("")
    print("Requirements:")
    print("  - RFID reader connected to /dev/ttyUSB0")
    print("  - Flask server running at http://127.0.0.1:5000")
    print("  - User with permissions to access serial port")
    print("")
    print("Setup:")
    print("  1. Connect RFID reader to USB port")
    print("  2. Set permissions: sudo chmod 666 /dev/ttyUSB0")
    print("  3. Add user to dialout group: sudo usermod -a -G dialout $USER")
    print("  4. Start Flask server: python app.py")
    print("  5. Run registration: python rfid_registration.py")
    print("  6. Scan RFID cards to register users")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        show_help()
    else:
        try:
            main()
        except Exception as e:
            print(f"💥 System error: {e}")
            sys.exit(1)
