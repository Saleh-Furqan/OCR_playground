#!/usr/bin/env python3
"""Quick test of single receipt - PaddleOCR only"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from paddleocr import PaddleOCR
import time

# Test image
img_path = "data/sroie/train/img/X51005255805.jpg"
gt_path = "data/sroie/train/entities/X51005255805.txt"

print("=" * 80)
print("QUICK PADDLEOCR TEST")
print("=" * 80)

# Load ground truth
import json
with open(gt_path) as f:
    gt = json.load(f)

print(f"\n📋 Ground Truth:")
print(f"   Merchant: {gt['company']}")
print(f"   Date: {gt['date']}")
print(f"   Total: {gt['total']}")

# Initialize PaddleOCR
print(f"\n🔧 Initializing PaddleOCR...")
ocr = PaddleOCR(use_textline_orientation=True, lang='en')
print(f"✅ Initialized!")

# Run OCR
print(f"\n📷 Processing: {img_path}")
start = time.time()
results = ocr.predict(img_path, use_textline_orientation=True)
elapsed = time.time() - start

print(f"⏱️  Time: {elapsed:.2f}s")

# Parse results - PaddleX 3.x returns dict-like OCRResult
if results and len(results) > 0:
    result = results[0]  # First image result

    # Extract text and scores from new API
    texts = result.get('rec_texts', [])
    scores = result.get('rec_scores', [])

    if texts:
        print(f"\n📝 Extracted Text:")
        print("=" * 80)
        for text, score in zip(texts, scores):
            print(f"{text:<50} (conf: {score:.2f})")
        print("=" * 80)

        # Extract all text
        all_text = '\n'.join(texts)
        print(f"\n📊 Total lines extracted: {len(texts)}")
        print(f"📊 Total characters: {len(all_text)}")

    # Check if key fields are present
    print(f"\n🔍 Field Detection:")
    merchant_found = gt['company'].upper() in all_text.upper() or any(word.upper() in all_text.upper() for word in gt['company'].split()[:2])
    date_found = gt['date'] in all_text or gt['date'].replace('/', '-') in all_text
    total_found = gt['total'] in all_text

    print(f"   Merchant text present: {'✅' if merchant_found else '❌'}")
    print(f"   Date present: {'✅' if date_found else '❌'}")
    print(f"   Total amount present: {'✅' if total_found else '❌'}")

print("\n" + "=" * 80)
print("✅ Test complete!")
print("=" * 80)
