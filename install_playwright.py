#!/usr/bin/env python3
"""
Script to install Playwright browsers
Run this after installing requirements.txt
"""

import subprocess
import sys

def install_playwright_browsers():
    """Install Playwright browsers"""
    try:
        print("Installing Playwright browsers...")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        print("✅ Playwright browsers installed successfully!")
        
        print("Installing system dependencies...")
        subprocess.run([sys.executable, "-m", "playwright", "install-deps"], check=True)
        print("✅ System dependencies installed successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing Playwright: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    install_playwright_browsers()
