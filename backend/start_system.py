#!/usr/bin/env python3
"""
ESP32 RFID System Startup Script
Starts the Flask server and optionally runs system tests
"""

import sys
import subprocess
import time
import os
import argparse

def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def check_flask_app():
    """Check if Flask app exists"""
    if not os.path.exists('app.py'):
        print("❌ app.py not found in current directory")
        return False
    return True

def run_tests():
    """Run system tests"""
    print("🧪 Running system tests...")
    try:
        result = subprocess.run([sys.executable, 'test_system.py'], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("Warnings/Errors:", result.stderr)
        return result.returncode == 0
    except FileNotFoundError:
        print("⚠️  test_system.py not found, skipping tests")
        return True

def start_flask_server(debug=True):
    """Start the Flask server"""
    print("🚀 Starting Flask server...")
    print("   - Server will run on http://0.0.0.0:5000")
    print("   - Press Ctrl+C to stop")
    print("   - ESP32 should auto-discover this server")
    print("")
    
    try:
        # Import and run the Flask app
        import app
        app.app.run(debug=debug, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Flask server failed: {e}")
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description='ESP32 RFID System Startup')
    parser.add_argument('--install-deps', action='store_true', help='Install dependencies first')
    parser.add_argument('--test', action='store_true', help='Run tests before starting server')
    parser.add_argument('--no-debug', action='store_true', help='Run Flask in production mode')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔐 ESP32 RFID Entry System Startup")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not check_flask_app():
        print("Please run this script from the backend directory")
        return False
    
    # Install dependencies if requested
    if args.install_deps:
        if not install_dependencies():
            return False
    
    # Run tests if requested
    if args.test:
        print("Waiting 2 seconds for any previous server to stop...")
        time.sleep(2)
        if not run_tests():
            print("⚠️  Some tests failed, but continuing anyway...")
    
    # Start Flask server
    debug_mode = not args.no_debug
    return start_flask_server(debug=debug_mode)

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
