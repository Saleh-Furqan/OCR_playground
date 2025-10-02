#!/usr/bin/env python3
"""Configuration management for OCR Receipt Processor"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
load_dotenv(CONFIG_DIR / ".env")


class Config:
    """Application configuration"""
    
    # Flask Configuration
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'ocr-receipt-processor-secret-key-2025')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', 5000))
    
    # Upload Configuration
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16777216))  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
    
    # OCR Configuration
    TESSERACT_CMD = os.getenv('TESSERACT_CMD', '/usr/bin/tesseract')
    
    # LLM Configuration
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'groq').lower()
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')
    HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
    HUGGINGFACE_MODEL = os.getenv('HUGGINGFACE_MODEL', 'microsoft/DialoGPT-medium')
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
    OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.1:8b')
    
    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist"""
        cls.UPLOAD_FOLDER.mkdir(exist_ok=True)


# Create default config instance
config = Config()