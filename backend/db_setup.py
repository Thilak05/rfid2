import sqlite3

def setup_database(db_path='rfid_log.db'):
    conn = sqlite3.connect(db_path)
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
    print(f"Database initialized at {db_path}")

if __name__ == '__main__':
    setup_database()
