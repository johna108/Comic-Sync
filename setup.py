#!/usr/bin/env python3
"""
Setup script for Virtual Browser Sync
"""

import subprocess
import sys
import os

def install_requirements():
    """Install Python requirements"""
    print("📦 Installing Python requirements...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    print("✅ Requirements installed!")

def test_browser():
    """Test if browser setup works"""
    print("🧪 Testing browser setup...")
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get("https://www.google.com")
        print("✅ Browser test successful!")
        driver.quit()
        
    except Exception as e:
        print(f"❌ Browser test failed: {e}")
        print("💡 The app will try to install Chrome automatically when you run it")

def main():
    try:
        install_requirements()
        test_browser()
        
        print("\n🚀 Setup complete!")
        print("Run the app with: python app.py")
        print("📝 Note: Chrome will be downloaded automatically on first run if needed")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during setup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
