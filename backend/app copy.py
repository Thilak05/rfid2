import sqlite3
from flask import Flask, request, render_template, jsonify
from datetime import datetime

app = Flask(__name__)
DB_PATH = 'rfid_log.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        unique_id TEXT NOT NULL,
        entry_time TEXT,
        exit_time TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name, entry_time, exit_time FROM logs')
    rows = c.fetchall()
    conn.close()
    return render_template('index.html', rows=rows)

@app.route('/scan', methods=['POST'])
def scan():
    data = request.json
    name = data.get('name')
    unique_id = data.get('unique_id')
    action = data.get('action')  # 'entry' or 'exit'
    if not name or not unique_id or action not in ['entry', 'exit']:
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if action == 'entry':
        # Authenticate and log entry
        c.execute('INSERT INTO logs (name, unique_id, entry_time) VALUES (?, ?, ?)',
                  (name, unique_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Entry logged'})
    elif action == 'exit':
        # Authenticate and log exit
        c.execute('SELECT id FROM logs WHERE unique_id=? AND exit_time IS NULL ORDER BY id DESC LIMIT 1', (unique_id,))
        row = c.fetchone()
        if row:
            c.execute('UPDATE logs SET exit_time=? WHERE id=?',
                      (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), row[0]))
            conn.commit()
            conn.close()
            return jsonify({'status': 'success', 'message': 'Exit logged'})
        else:
            conn.close()
            return jsonify({'status': 'error', 'message': 'No entry found for exit'}), 404

if __name__ == '__main__':
    app.run(debug=True)
