#!/usr/bin/env python3
"""
Local setup script for OBS Docker Web Manager
Handles Python version compatibility issues
"""

import sys
import subprocess
import os

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("ERROR: Python 3.8+ is required")
        return False
    
    if version.major == 3 and version.minor >= 12:
        print("WARNING: Python 3.12+ detected. Installing compatibility packages...")
        return True
    
    return True

def install_dependencies():
    """Install required dependencies with compatibility fixes"""
    try:
        # Upgrade pip and setuptools first
        print("Upgrading pip and setuptools...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "setuptools>=65.0.0"])
        
        # Install requirements
        print("Installing requirements...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        
        print("✅ Dependencies installed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 OBS Docker Web Manager - Local Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Change to web directory
    web_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(web_dir)
    print(f"Working directory: {web_dir}")
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    print("\n✅ Setup completed successfully!")
    print("\nTo start the web manager:")
    print("  python app.py")
    print("\nOr use the Docker method:")
    print("  ./start-web-manager.sh start")

if __name__ == "__main__":
    main()
