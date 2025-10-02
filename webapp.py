#!/usr/bin/env python3

import sys
import os
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.web.app import app
from src.core.config import config

if __name__ == '__main__':
    print("🚀 Starting OCR Receipt Processor...")
    print(f"📱 Access the app at: http://{config.HOST}:{config.PORT}")
    print("⏹️  Press Ctrl+C to stop")
    
    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)