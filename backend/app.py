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

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

DB_PATH = 'rfid_log.db'

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
    data = request.json
    unique_id = data.get('unique_id')
    action = data.get('action')

    if not unique_id or action not in ['entry', 'exit']:
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Validate user exists and is active
    c.execute('SELECT name FROM users WHERE unique_id=? AND status="active"', (unique_id,))
    user = c.fetchone()

    if not user:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Access Denied: User not registered'}), 403

    if action == 'entry':
        c.execute('''SELECT id FROM logs WHERE unique_id=? AND entry_time IS NOT NULL
                     AND (exit_time IS NULL OR exit_time < entry_time)
                     ORDER BY id DESC LIMIT 1''', (unique_id,))
        existing_entry = c.fetchone()

        if existing_entry:
            conn.close()
            return jsonify({'status': 'error', 'message': 'User already inside'}), 400

        c.execute('INSERT INTO logs (name, unique_id, entry_time, status) VALUES (?, ?, ?, ?)',
                  (user[0], unique_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'inside'))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Entry logged', 'user_name': user[0]})

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
            return jsonify({'status': 'success', 'message': 'Exit logged', 'user_name': user[0]})
        else:
            conn.close()
            return jsonify({'status': 'error', 'message': 'No entry found for exit'}), 404

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
except Exception as e:
    print(f"Warning: Could not start RFID processes: {e}")
    reader_proc = None
    sender_proc = None

def cleanup():
    print("Terminating RFID subprocesses...")
    for proc in [reader_proc, sender_proc]:
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
