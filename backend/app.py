import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import socket
import threading
import time
import subprocess
import signal
import sys
import atexit
import requests

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

DB_PATH = 'rfid_log.db'

# ESP32/ESP8266 Configuration
ESP_DEVICES = {}  # Store MAC -> IP mapping for multiple devices

def send_oled_message(message, device_mac=None):
    """Send a message to ESP device OLED display"""
    if device_mac and device_mac in ESP_DEVICES:
        esp_ip = ESP_DEVICES[device_mac]
    elif ESP_DEVICES:
        esp_ip = list(ESP_DEVICES.values())[0]  # Use first available device
    else:
        print("No ESP devices registered yet")
        return False
    
    try:
        response = requests.post(
            f"http://{esp_ip}/message", 
            data=message,
            timeout=3
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending OLED message to {device_mac}: {e}")
        return False

def get_network_ip():
    """Get the network IP address of the machine"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create logs table
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        unique_id TEXT NOT NULL,
        entry_time TEXT,
        exit_time TEXT,
        status TEXT DEFAULT 'inside'
    )''')

    # Create users table for registration
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        unique_id TEXT UNIQUE NOT NULL,
        email TEXT,
        phone TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'active'
    )''')

    conn.commit()
    conn.close()

init_db()

latest_rfid_scan = {'rfid_id': None, 'timestamp': None, 'status': 'idle'}

@app.route('/')
def root():
    """Root endpoint for ESP device discovery and identification"""
    return jsonify({
        'service': 'RFID Entry System',
        'type': 'Flask Server',
        'version': '1.0',
        'description': 'Raspberry Pi RFID Entry System Backend',
        'endpoints': ['/scan', '/api/users', '/api/logs', '/api/stats']
    })

@app.route('/api/device/info')
def device_info():
    """Device information endpoint for identification"""
    try:
        import netifaces
        
        # Get MAC address of the default interface
        gateways = netifaces.gateways()
        default_interface = gateways['default'][netifaces.AF_INET][1]
        mac_address = netifaces.ifaddresses(default_interface)[netifaces.AF_LINK][0]['addr']
        
        return jsonify({
            'device_type': 'Raspberry Pi',
            'service': 'RFID Entry System',
            'mac_address': mac_address.upper(),
            'interface': default_interface,
            'server_ip': get_network_ip(),
            'registered_devices': len(ESP_DEVICES)
        })
    except ImportError:
        # netifaces not available, try alternative methods
        try:
            import uuid
            import subprocess
            import re
            
            # Try to get MAC address using system commands
            try:
                # Linux/Pi method
                result = subprocess.run(['cat', '/sys/class/net/eth0/address'], 
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    mac_address = result.stdout.strip().upper()
                else:
                    # Try wlan0 if eth0 not available
                    result = subprocess.run(['cat', '/sys/class/net/wlan0/address'], 
                                          capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        mac_address = result.stdout.strip().upper()
                    else:
                        # Fall back to a known Pi MAC if system is configured for testing
                        mac_address = "D8:3A:DD:78:01:07"  # Default Pi MAC for testing
            except:
                # Ultimate fallback
                mac_address = "D8:3A:DD:78:01:07"  # Default Pi MAC for testing
            
            return jsonify({
                'device_type': 'Raspberry Pi',
                'service': 'RFID Entry System',
                'mac_address': mac_address,
                'server_ip': get_network_ip(),
                'registered_devices': len(ESP_DEVICES),
                'method': 'fallback'
            })
        except Exception as e:
            # Final fallback with known MAC
            return jsonify({
                'device_type': 'Raspberry Pi',
                'service': 'RFID Entry System',
                'mac_address': 'D8:3A:DD:78:01:07',  # Default Pi MAC for testing
                'server_ip': get_network_ip(),
                'registered_devices': len(ESP_DEVICES),
                'error': str(e),
                'method': 'hardcoded'
            })
    except Exception as e:
        # Fallback if netifaces fails for other reasons
        return jsonify({
            'device_type': 'Raspberry Pi',
            'service': 'RFID Entry System',
            'mac_address': 'D8:3A:DD:78:01:07',  # Default Pi MAC for testing
            'server_ip': get_network_ip(),
            'registered_devices': len(ESP_DEVICES),
            'error': str(e),
            'method': 'error_fallback'
        })

@app.route('/api/users', methods=['GET'])
def get_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM users ORDER BY created_at DESC')
    users = []
    for row in c.fetchall():
        users.append({
            'id': row[0],
            'name': row[1],
            'unique_id': row[2],
            'email': row[3],
            'phone': row[4],
            'created_at': row[5],
            'status': row[6]
        })
    conn.close()
    return jsonify(users)

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.json
    name = data.get('name')
    unique_id = data.get('unique_id')
    email = data.get('email', '')
    phone = data.get('phone', '')

    if not name or not unique_id:
        return jsonify({'status': 'error', 'message': 'Name and RFID ID are required'}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    try:
        c.execute('INSERT INTO users (name, unique_id, email, phone) VALUES (?, ?, ?, ?)',
                  (name, unique_id, email, phone))
        conn.commit()
        user_id = c.lastrowid
        conn.close()
        return jsonify({
            'status': 'success',
            'message': 'User registered successfully',
            'user_id': user_id
        })
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'status': 'error', 'message': 'RFID ID already exists'}), 400

@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('UPDATE users SET name=?, email=?, phone=?, status=? WHERE id=?',
              (data.get('name'), data.get('email'), data.get('phone'),
               data.get('status'), user_id))
    conn.commit()
    conn.close()

    return jsonify({'status': 'success', 'message': 'User updated successfully'})

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE id=?', (user_id,))
    conn.commit()
    conn.close()

    return jsonify({'status': 'success', 'message': 'User deleted successfully'})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT l.*, u.name as user_name, u.email as user_email
                 FROM logs l
                 LEFT JOIN users u ON l.unique_id = u.unique_id
                 ORDER BY l.id DESC LIMIT 100''')
    logs = []
    for row in c.fetchall():
        logs.append({
            'id': row[0],
            'name': row[1],
            'unique_id': row[2],
            'entry_time': row[3],
            'exit_time': row[4],
            'status': row[5],
            'user_name': row[6] or row[1],
            'user_email': row[7] if len(row) > 7 else None
        })
    conn.close()
    return jsonify(logs)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('SELECT COUNT(*) FROM users WHERE status="active"')
    total_users = c.fetchone()[0]

    c.execute('''SELECT COUNT(DISTINCT unique_id) FROM logs
                 WHERE unique_id IN (
                     SELECT unique_id FROM logs
                     WHERE entry_time IS NOT NULL
                     AND unique_id NOT IN (
                         SELECT unique_id FROM logs
                         WHERE exit_time IS NOT NULL
                         AND exit_time > entry_time
                     )
                 )''')
    inside_count = c.fetchone()[0]

    today = datetime.now().strftime('%Y-%m-%d')
    c.execute('SELECT COUNT(*) FROM logs WHERE entry_time LIKE ?', (f'{today}%',))
    today_entries = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM logs WHERE exit_time LIKE ?', (f'{today}%',))
    today_exits = c.fetchone()[0]

    conn.close()

    return jsonify({
        'total_users': total_users,
        'inside_count': inside_count,
        'outside_count': max(0, total_users - inside_count),
        'today_entries': today_entries,
        'today_exits': today_exits
    })

@app.route('/api/validate_user', methods=['POST'])
def validate_user():
    """Validate if a user exists and is active"""
    data = request.json
    unique_id = data.get('unique_id')
    
    if not unique_id:
        return jsonify({'status': 'error', 'message': 'RFID ID is required'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, name, status FROM users WHERE unique_id=?', (unique_id,))
    user = c.fetchone()
    conn.close()
    
    if not user:
        return jsonify({'status': 'error', 'message': 'Access Denied: User not registered', 'access_granted': False}), 403
    
    if user[2] != 'active':
        return jsonify({'status': 'error', 'message': 'Access Denied: User account is inactive', 'access_granted': False}), 403
    
    return jsonify({
        'status': 'success', 
        'message': 'Access Granted', 
        'user_id': user[0],
        'name': user[1],
        'access_granted': True
    })

@app.route('/scan', methods=['POST'])
def scan():
    global ESP_DEVICES
    
    data = request.json
    unique_id = data.get('unique_id')
    action = data.get('action')
    device_mac = data.get('device_mac')
    
    # Register ESP device by MAC address
    if device_mac:
        ESP_DEVICES[device_mac] = request.remote_addr
        print(f"ESP device registered: MAC {device_mac} -> IP {request.remote_addr}")

    if not unique_id or action not in ['entry', 'exit']:
        send_oled_message("ERROR\nInvalid data", device_mac)
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Validate user exists and is active
    c.execute('SELECT name FROM users WHERE unique_id=? AND status="active"', (unique_id,))
    user = c.fetchone()

    if not user:
        conn.close()
        send_oled_message("Access Denied\nNot Registered\n" + unique_id, device_mac)
        return jsonify({'status': 'error', 'message': 'Access Denied: User not registered'}), 403

    user_name = user[0]

    if action == 'entry':
        c.execute('''SELECT id FROM logs WHERE unique_id=? AND entry_time IS NOT NULL
                     AND (exit_time IS NULL OR exit_time < entry_time)
                     ORDER BY id DESC LIMIT 1''', (unique_id,))
        existing_entry = c.fetchone()

        if existing_entry:
            conn.close()
            send_oled_message("Already Inside\n" + user_name, device_mac)
            return jsonify({'status': 'error', 'message': 'User already inside'}), 400

        c.execute('INSERT INTO logs (name, unique_id, entry_time, status) VALUES (?, ?, ?, ?)',
                  (user_name, unique_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'inside'))
        conn.commit()
        conn.close()
        
        send_oled_message("Access Granted\nWelcome\n" + user_name, device_mac)
        
        return jsonify({
            'status': 'success', 
            'message': 'Entry logged', 
            'user_name': user_name
        })

    elif action == 'exit':
        c.execute('''SELECT id FROM logs WHERE unique_id=? AND entry_time IS NOT NULL
                     AND (exit_time IS NULL OR exit_time < entry_time)
                     ORDER BY id DESC LIMIT 1''', (unique_id,))
        row = c.fetchone()

        if row:
            c.execute('UPDATE logs SET exit_time=?, status=? WHERE id=?',
                      (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'outside', row[0]))
            conn.commit()
            conn.close()
            
            send_oled_message("Exit Logged\nGoodbye\n" + user_name, device_mac)
            
            return jsonify({
                'status': 'success', 
                'message': 'Exit logged', 
                'user_name': user_name
            })
        else:
            conn.close()
            send_oled_message("No Entry Found\n" + user_name, device_mac)
            return jsonify({'status': 'error', 'message': 'No entry found for exit'}), 404

@app.route('/message', methods=['POST'])
def send_message():
    """Endpoint to manually send messages to ESP8266 OLED"""
    data = request.get_data(as_text=True)
    device_mac = request.args.get('mac')  # Optional MAC parameter
    
    if send_oled_message(data, device_mac):
        return jsonify({'status': 'success', 'message': 'Message sent to OLED'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to send message to OLED'}), 500

@app.route('/api/rfid/read', methods=['POST'])
def read_rfid():
    global latest_rfid_scan

    try:
        import serial
        import serial.tools.list_ports

        latest_rfid_scan = {'rfid_id': None, 'timestamp': time.time(), 'status': 'scanning'}

        possible_ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyS0', '/dev/ttyAMA0']
        ser = None

        for port in possible_ports:
            try:
                ser = serial.Serial(port, 9600, timeout=1)
                print(f"Connected to RFID reader on {port}")
                break
            except serial.SerialException:
                continue

        if not ser:
            latest_rfid_scan['status'] = 'error'
            return jsonify({'status': 'error', 'message': 'RFID reader not found on any port'}), 500

        print("Waiting for RFID scan...")
        start_time = time.time()
        rfid_data = None

        while time.time() - start_time < 15:
            try:
                if ser.in_waiting > 0:
                    raw_data = ser.readline()
                    if raw_data:
                        try:
                            rfid_data = raw_data.decode('utf-8', errors='ignore').strip()
                        except:
                            rfid_data = raw_data.decode('ascii', errors='ignore').strip()

                        rfid_data = ''.join(c for c in rfid_data if c.isalnum())

                        if rfid_data and len(rfid_data) >= 8:
                            latest_rfid_scan = {
                                'rfid_id': rfid_data,
                                'timestamp': time.time(),
                                'status': 'success'
                            }
                            ser.close()
                            print(f"RFID scanned successfully: {rfid_data}")
                            return jsonify({
                                'status': 'success',
                                'rfid_id': rfid_data,
                                'message': 'RFID scanned successfully'
                            })
            except Exception as e:
                print(f"Error reading from serial: {e}")
                continue

            time.sleep(0.1)

        ser.close()
        latest_rfid_scan['status'] = 'timeout'
        return jsonify({
            'status': 'timeout',
            'message': 'No RFID detected within 15 seconds. Please try again.'
        }), 408

    except ImportError:
        latest_rfid_scan['status'] = 'error'
        return jsonify({
            'status': 'error',
            'message': 'Serial library not available. Install pyserial: pip install pyserial'
        }), 500
    except Exception as e:
        latest_rfid_scan['status'] = 'error'
        return jsonify({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }), 500

@app.route('/api/rfid/status', methods=['GET'])
def get_rfid_status():
    global latest_rfid_scan
    return jsonify(latest_rfid_scan)

try:
    reader_proc = subprocess.Popen([sys.executable, 'rfid_reader.py'])
    sender_proc = subprocess.Popen([sys.executable, 'rfid_sender.py'])
    registration_proc = subprocess.Popen([sys.executable, 'rfid_registration.py'])
    print("✅ Started RFID processes:")
    print("   - Entry system (rfid_sender.py)")
    print("   - Exit system (rfid_reader.py)") 
    print("   - Registration system (rfid_registration.py)")
except Exception as e:
    print(f"Warning: Could not start RFID processes: {e}")
    reader_proc = None
    sender_proc = None
    registration_proc = None

def cleanup():
    print("Terminating RFID subprocesses...")
    for proc in [reader_proc, sender_proc, registration_proc]:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

atexit.register(cleanup)

if __name__ == '__main__':
    network_ip = get_network_ip()
    print(f"Starting RFID Access Control System...")
    print(f"Network IP: {network_ip}")
    print(f"Frontend URL: http://{network_ip}:5173")
    print(f"Backend API: http://{network_ip}:5000")
    print(f"Database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name, unique_id FROM users')
    users = c.fetchall()
    print(f"Registered users: {users}")
    conn.close()

    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        pass
