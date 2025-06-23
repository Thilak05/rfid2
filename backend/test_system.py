#!/usr/bin/env python3
"""
ESP32 RFID System Test Script
Tests all components of the ESP32 WROOM RFID entry system
"""

import requests
import json
import time
import subprocess
import sys

# Configuration
FLASK_URL = 'http://127.0.0.1:5000'
ESP32_MAC = "E4:65:B8:27:73:08"
PI_MAC = "D8:3A:DD:78:01:07"

def test_flask_server():
    """Test if Flask server is running and responding"""
    print("🧪 Testing Flask Server...")
    
    try:
        # Test root endpoint
        response = requests.get(f"{FLASK_URL}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Flask server is running: {data.get('service', 'Unknown')}")
            return True
        else:
            print(f"❌ Flask server returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Flask server not accessible: {e}")
        return False

def test_device_info():
    """Test device info endpoint (MAC address verification)"""
    print("🧪 Testing Device Info Endpoint...")
    
    try:
        response = requests.get(f"{FLASK_URL}/api/device/info", timeout=5)
        if response.status_code == 200:
            data = response.json()
            mac = data.get('mac_address', 'Unknown')
            device_type = data.get('device_type', 'Unknown')
            print(f"✅ Device Info: {device_type}, MAC: {mac}")
            
            if mac.upper() == PI_MAC.upper():
                print("✅ MAC address matches expected Pi MAC")
            else:
                print(f"⚠️  MAC address differs from expected: {PI_MAC}")
            return True
        else:
            print(f"❌ Device info endpoint returned: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Device info endpoint failed: {e}")
        return False

def test_user_registration():
    """Test user registration and validation"""
    print("🧪 Testing User Registration...")
    
    test_user = {
        "name": "Test User",
        "unique_id": "TEST123456",
        "email": "test@example.com",
        "phone": "555-0123"
    }
    
    try:
        # Register test user
        response = requests.post(f"{FLASK_URL}/api/users", json=test_user, timeout=5)
        if response.status_code == 200:
            print("✅ Test user registered successfully")
        else:
            print(f"ℹ️  User registration response: {response.status_code} (may already exist)")
        
        # Validate test user
        validation_data = {"unique_id": test_user["unique_id"]}
        response = requests.post(f"{FLASK_URL}/api/validate_user", json=validation_data, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('access_granted'):
                print(f"✅ User validation successful: {data.get('name')}")
                return True
            else:
                print(f"❌ User validation failed: {data.get('message')}")
                return False
        else:
            print(f"❌ User validation endpoint error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ User registration/validation failed: {e}")
        return False

def test_rfid_scan():
    """Test RFID scan endpoint"""
    print("🧪 Testing RFID Scan Endpoint...")
    
    scan_data = {
        "unique_id": "TEST123456",
        "action": "entry",
        "device_mac": ESP32_MAC
    }
    
    try:
        response = requests.post(f"{FLASK_URL}/scan", json=scan_data, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ RFID scan successful: {data.get('message')}")
            return True
        else:
            data = response.json()
            print(f"❌ RFID scan failed ({response.status_code}): {data.get('message')}")
            return False
    except Exception as e:
        print(f"❌ RFID scan endpoint failed: {e}")
        return False

def test_system_endpoints():
    """Test various system endpoints"""
    print("🧪 Testing System Endpoints...")
    
    endpoints = [
        ('/api/users', 'GET', 'Users list'),
        ('/api/logs', 'GET', 'Access logs'),
        ('/api/stats', 'GET', 'System statistics'),
        ('/api/rfid/status', 'GET', 'RFID status')
    ]
    
    success_count = 0
    for endpoint, method, description in endpoints:
        try:
            if method == 'GET':
                response = requests.get(f"{FLASK_URL}{endpoint}", timeout=5)
            else:
                response = requests.post(f"{FLASK_URL}{endpoint}", timeout=5)
            
            if response.status_code == 200:
                print(f"✅ {description}: OK")
                success_count += 1
            else:
                print(f"❌ {description}: {response.status_code}")
        except Exception as e:
            print(f"❌ {description}: {e}")
    
    return success_count == len(endpoints)

def check_dependencies():
    """Check if required Python packages are installed"""
    print("🧪 Checking Python Dependencies...")
    
    required_packages = [
        'flask',
        'flask_cors',
        'requests'
    ]
    
    optional_packages = [
        'netifaces',
        'serial'
    ]
    
    all_good = True
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}: Available")
        except ImportError:
            print(f"❌ {package}: Missing (required)")
            all_good = False
    
    for package in optional_packages:
        try:
            if package == 'serial':
                import serial
            else:
                __import__(package)
            print(f"✅ {package}: Available")
        except ImportError:
            print(f"⚠️  {package}: Missing (optional, fallbacks available)")
    
    return all_good

def display_network_info():
    """Display network information for debugging"""
    print("🌐 Network Information:")
    
    try:
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"   Hostname: {hostname}")
        print(f"   Local IP: {local_ip}")
    except:
        print("   Could not determine network info")
    
    print(f"   Flask URL: {FLASK_URL}")
    print(f"   ESP32 MAC: {ESP32_MAC}")
    print(f"   Pi MAC: {PI_MAC}")

def main():
    """Main test function"""
    print("=" * 60)
    print("🔬 ESP32 RFID System Test Suite")
    print("=" * 60)
    
    # Display system info
    display_network_info()
    print()
    
    # Run tests
    tests = [
        ("Dependencies", check_dependencies),
        ("Flask Server", test_flask_server),
        ("Device Info", test_device_info),
        ("User Registration", test_user_registration),
        ("RFID Scan", test_rfid_scan),
        ("System Endpoints", test_system_endpoints)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"💥 {test_name} CRASHED: {e}")
        print()
    
    # Results
    print("=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready.")
    elif passed >= total - 2:
        print("⚠️  Most tests passed. Minor issues may exist.")
    else:
        print("❌ Multiple failures. Check Flask server and dependencies.")
    
    print("\n📋 Next Steps:")
    if passed < total:
        print("   1. Ensure Flask server is running: python app.py")
        print("   2. Install missing dependencies: pip install -r requirements.txt")
        print("   3. Check network connectivity")
    
    print("   4. Upload ESP32 firmware: esp8266_entry_oled.ino")
    print("   5. Configure WiFi credentials in ESP32 code")
    print("   6. Verify hardware connections (RFID, OLED)")
    print("   7. Monitor ESP32 serial output for connection status")
    
    print("=" * 60)
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
