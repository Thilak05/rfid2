# RFID Access Control System - Database Validation Update

## Overview
This update removes hardcoded user mappings from the RFID reader and sender scripts and implements proper database-based user validation with access control.

## Changes Made

### 1. Flask App (app.py)
- **Added new endpoint**: `/api/validate_user` - Validates if a user exists and is active in the database
- **Updated `/scan` endpoint**: Removed auto-registration of unknown users, now requires users to be pre-registered
- **Access Control**: Only registered and active users can gain access

### 2. RFID Sender (rfid_sender.py) - Entry Point
- **Removed**: Hardcoded `USER_MAP` dictionary
- **Added**: `validate_user()` function to check user registration status
- **Updated**: `send_scan()` function now validates users before allowing entry
- **Access Control**: 
  - ✅ **Access Granted**: For registered active users
  - ❌ **Access Denied**: For unregistered or inactive users

### 3. RFID Reader (rfid_reader.py) - Exit Point
- **Removed**: Hardcoded `USER_MAP` dictionary
- **Added**: `validate_user()` function to check user registration status
- **Updated**: `send_scan()` function now validates users before allowing exit
- **Access Control**: Same as entry point

### 4. Test User Setup (setup_test_users.py)
- **New file**: Script to populate database with test users
- **Purpose**: Adds the same users that were previously in USER_MAP to the database
- **Usage**: Run this script to set up initial test users

## Security Improvements

### Before (Insecure)
- Users were hardcoded in files
- Unknown users were auto-registered
- No access control validation

### After (Secure)
- All user data stored in database
- Only pre-registered users can access
- Real-time validation against database
- Clear access granted/denied messages
- Centralized user management through web interface

## API Endpoints

### New: `/api/validate_user` (POST)
```json
Request:
{
  "unique_id": "0009334653"
}

Response (Success):
{
  "status": "success",
  "message": "Access Granted",
  "user_id": 1,
  "name": "Arun",
  "access_granted": true
}

Response (Denied):
{
  "status": "error",
  "message": "Access Denied: User not registered",
  "access_granted": false
}
```

### Updated: `/scan` (POST)
```json
Request:
{
  "unique_id": "0009334653",
  "action": "entry"  // or "exit"
}

Response (Success):
{
  "status": "success",
  "message": "Entry logged",
  "user_name": "Arun"
}

Response (Denied):
{
  "status": "error",
  "message": "Access Denied: User not registered"
}
```

## How It Works

1. **RFID Scan**: When a card is scanned at entry/exit point
2. **Validation**: System checks if user exists and is active in database
3. **Access Control**: 
   - If valid: Shows "Access Granted" and logs entry/exit
   - If invalid: Shows "Access Denied" and blocks action
4. **Logging**: Only successful validations are logged to the database

## Setup Instructions

1. **Install dependencies** (if not already done):
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup test users**:
   ```bash
   python setup_test_users.py
   ```

3. **Start the system**:
   ```bash
   python app.py
   ```

4. **Test RFID scanners** (in separate terminals):
   ```bash
   # For entry point
   python rfid_sender.py
   
   # For exit point  
   python rfid_reader.py
   ```

## Test Users
The following test users are included in `setup_test_users.py`:
- **Arun**: RFID `0009334653`
- **Thilak**: RFID `080058DBB1`
- **Hari**: RFID `080058DD98`

## Benefits

1. **Security**: No unauthorized access
2. **Scalability**: Easy to add/remove users via web interface
3. **Centralized Management**: All user data in one place
4. **Audit Trail**: Clear logging of access attempts
5. **Real-time Validation**: Always up-to-date user status checking
6. **Professional Access Control**: Clear feedback on access decisions
