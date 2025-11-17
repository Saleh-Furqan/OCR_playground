#!/usr/bin/env python3
"""
Run benchmark on the 50 clearest SRD images only
Quick test to validate our fixes work
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from paddleocr import PaddleOCR
import time
import json

# Just test first 10 images from srd directory
srd_dir = Path("data/srd")
images = sorted(srd_dir.glob("*.jpg"))[:10]  # Just first 10 for quick test

print("=" * 80)
print(f"PADDLEOCR TEST ON SRD CLEAR IMAGES")
print(f"Testing {len(images)} images")
print("=" * 80)

# Initialize PaddleOCR once
print("\n🔧 Initializing PaddleOCR...")
ocr = PaddleOCR(use_textline_orientation=True, lang='en')
print("✅ Initialized!\n")

results = []

for idx, img_path in enumerate(images, 1):
    print(f"\n[{idx}/{len(images)}] Processing: {img_path.name}")

    try:
        start = time.time()
        ocr_results = ocr.predict(str(img_path), use_textline_orientation=True)
        elapsed = time.time() - start

        if ocr_results and len(ocr_results) > 0:
            result = ocr_results[0]
            texts = result.get('rec_texts', [])
            scores = result.get('rec_scores', [])

            # Calculate stats
            avg_conf = sum(scores) / len(scores) if scores else 0
            full_text = '\n'.join(texts)

            print(f"   ✅ Extracted {len(texts)} lines in {elapsed:.2f}s (confidence: {avg_conf:.2f})")

            results.append({
                "image": img_path.name,
                "num_lines": len(texts),
                "avg_confidence": avg_conf,
                "time_seconds": elapsed,
                "text_preview": full_text[:200] + "..." if len(full_text) > 200 else full_text
            })
        else:
            print(f"   ❌ No results returned")
            results.append({
                "image": img_path.name,
                "error": "No results"
            })

    except Exception as e:
        print(f"   ❌ Error: {e}")
        results.append({
            "image": img_path.name,
            "error": str(e)
        })

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

successful = [r for r in results if "error" not in r]
failed = [r for r in results if "error" in r]

print(f"\n✅ Successful: {len(successful)}/{len(results)}")
print(f"❌ Failed: {len(failed)}/{len(results)}")

if successful:
    avg_time = sum(r["time_seconds"] for r in successful) / len(successful)
    avg_lines = sum(r["num_lines"] for r in successful) / len(successful)
    avg_conf = sum(r["avg_confidence"] for r in successful) / len(successful)

    print(f"\n📊 Average Statistics:")
    print(f"   Time per image: {avg_time:.2f}s")
    print(f"   Lines per image: {avg_lines:.1f}")
    print(f"   Confidence: {avg_conf:.2f}")

# Save results
output_file = Path("results/srd_quick_test.json")
output_file.parent.mkdir(exist_ok=True)
with open(output_file, 'w') as f:
    json.dump({
        "summary": {
            "total": len(results),
            "successful": len(successful),
            "failed": len(failed)
        },
        "results": results
    }, f, indent=2)

print(f"\n💾 Results saved to: {output_file}")
print("=" * 80)
