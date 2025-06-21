#!/usr/bin/env python3
"""
Script to add test users to the RFID access control database.
Run this script to populate the database with test users for the RFID system.
"""

import sqlite3
from datetime import datetime

DB_PATH = 'rfid_log.db'

# Test users data (same as the old USER_MAP)
TEST_USERS = [
    {
        'name': 'Arun',
        'unique_id': '0009334653',
        'email': 'arun@company.com',
        'phone': '+1234567890'
    },
    {
        'name': 'Thilak',
        'unique_id': '080058DBB1',
        'email': 'thilak@company.com',
        'phone': '+1234567891'
    },
    {
        'name': 'Hari',
        'unique_id': '080058DD98',
        'email': 'hari@company.com',
        'phone': '+1234567892'
    }
]

def setup_test_users():
    """Add test users to the database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("Setting up test users...")
    
    for user in TEST_USERS:
        try:
            c.execute('''INSERT INTO users (name, unique_id, email, phone, status) 
                         VALUES (?, ?, ?, ?, ?)''',
                      (user['name'], user['unique_id'], user['email'], user['phone'], 'active'))
            print(f"✓ Added user: {user['name']} (RFID: {user['unique_id']})")
        except sqlite3.IntegrityError:
            print(f"ℹ User {user['name']} (RFID: {user['unique_id']}) already exists")
    
    conn.commit()
    
    # Display all users
    print("\nCurrent users in database:")
    c.execute('SELECT name, unique_id, email, status FROM users ORDER BY name')
    users = c.fetchall()
    
    for user in users:
        status_icon = "✓" if user[3] == 'active' else "✗"
        print(f"{status_icon} {user[0]} - RFID: {user[1]} - Email: {user[2]} - Status: {user[3]}")
    
    conn.close()
    print(f"\nTotal users: {len(users)}")

if __name__ == '__main__':
    setup_test_users()
