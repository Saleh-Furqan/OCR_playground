#!/usr/bin/env python3

import sys
import os
import json
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.ocr_processor import OCRProcessor
from llm.grok_enhancer import GrokEnhancer

def main():
    if len(sys.argv) != 2:
        print("Usage: python run.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    if not os.path.exists(image_path):
        print(f"Error: Image file '{image_path}' not found")
        sys.exit(1)
    
    print(f"🔍 Processing receipt: {image_path}")
    
    # Initialize processors
    ocr_processor = OCRProcessor()
    grok_enhancer = GrokEnhancer()
    
    try:
        # Step 1: Extract text with OCR
        print("📖 Extracting text with OCR...")
        text, metadata = ocr_processor.extract_text(image_path)
        print(f"✅ OCR extracted {len(text)} characters")
        
        # Step 2: Structure with Grok
        if grok_enhancer.is_available():
            print("🤖 Structuring receipt with Grok...")
            structured_receipt = grok_enhancer.structure_receipt(text)
            
            if "error" in structured_receipt:
                print(f"❌ Grok error: {structured_receipt['error']}")
                print("📝 Raw OCR Text:")
                print(text)
            else:
                print("✅ Receipt structured successfully!")
                print("\n" + "="*50)
                print("📄 STANDARDIZED DIGITAL RECEIPT")
                print("="*50)
                print(json.dumps(structured_receipt, indent=2, default=str))
        else:
            print("⚠️  Grok not configured. Add XAI_API_KEY to use receipt structuring.")
            print("📝 Raw OCR Text:")
            print(text)
        
    except Exception as e:
        print(f"❌ Error processing receipt: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()