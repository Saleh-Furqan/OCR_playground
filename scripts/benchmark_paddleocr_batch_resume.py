#!/usr/bin/env python3
"""
PaddleOCR benchmark on FULL SROIE dataset - RESUMABLE BATCH VERSION
Automatically resumes from last processed image
Usage: python benchmark_paddleocr_batch_resume.py <batch_number>
"""
import sys
import json
import time
import re
from pathlib import Path
from datetime import datetime
import numpy as np
import cv2
import signal
from contextlib import contextmanager

sys.path.insert(0, str(Path(__file__).parent.parent))
from paddleocr import PaddleOCR

class TimeoutException(Exception):
    pass

@contextmanager
def time_limit(seconds):
    """Context manager to enforce time limit on operations"""
    def signal_handler(signum, frame):
        raise TimeoutException("Operation timed out")
    
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

def load_ground_truth(gt_path: Path):
    """Load ground truth JSON file"""
    with open(gt_path, 'r') as f:
        data = json.load(f)
    return {
        "merchant_name": data.get("company", ""),
        "transaction_date": data.get("date", ""),
        "total_amount": data.get("total", ""),
        "address": data.get("address", "")
    }

def fuzzy_match(pred, truth):
    """Check if prediction matches ground truth (fuzzy)"""
    if not pred or not truth:
        return False
    pred = str(pred).lower().strip()
    truth = str(truth).lower().strip()
    return pred in truth or truth in pred

def preprocess_large_image(img_path: Path, max_dimension: int = 2500, skip_threshold: int = 4500):
    """Check image size and skip if too large to prevent WSL crashes"""
    img = cv2.imread(str(img_path))
    if img is None:
        return None, False
    
    h, w = img.shape[:2]
    max_side = max(h, w)
    
    # Skip images that are too large (causes WSL to crash)
    if max_side > skip_threshold:
        print(f"   ⚠️  Skipping image {w}x{h} - too large (>{skip_threshold}px), causes WSL crash")
        return None, True  # True = intentional skip, not error
    
    if max_side > max_dimension:
        scale = max_dimension / max_side
        new_w = int(w * scale)
        new_h = int(h * scale)
        print(f"   ⚠️  Resizing {w}x{h} → {new_w}x{new_h}")
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # Save resized image temporarily
        temp_path = img_path.parent / f"temp_resized_{img_path.name}"
        cv2.imwrite(str(temp_path), img)
        return temp_path, False
    
    return img_path, False

def load_existing_results(batch_file: Path):
    """Load existing batch results if file exists"""
    if batch_file.exists():
        with open(batch_file, 'r') as f:
            data = json.load(f)
            return data.get('detailed_results', [])
    return []

def save_results_incremental(batch_file: Path, metadata, batch_metrics, results):
    """Save results incrementally"""
    with open(batch_file, 'w') as f:
        json.dump({
            "metadata": metadata,
            "batch_metrics": batch_metrics,
            "detailed_results": results
        }, f, indent=2)

# Parse batch number
if len(sys.argv) < 2:
    print("Usage: python benchmark_paddleocr_batch_resume.py <batch_number>")
    print("  batch_number: 1, 2, or 3")
    sys.exit(1)

try:
    batch_num = int(sys.argv[1])
    if batch_num not in [1, 2, 3]:
        raise ValueError()
except ValueError:
    print("Error: batch_number must be 1, 2, or 3")
    sys.exit(1)

print("=" * 80)
print(f"PADDLEOCR BENCHMARK - BATCH {batch_num}/3 (RESUMABLE)")
print("Raw OCR + Fuzzy Text Matching")
print("=" * 80)

# Find all images with ground truth
dataset_dir = Path("data/sroie")
img_dir = dataset_dir / "train" / "img"
entities_dir = dataset_dir / "train" / "entities"

image_files = sorted(img_dir.glob("*.jpg"))
print(f"Found {len(image_files)} images in {img_dir}")

# Filter to only those with ground truth
all_samples = []
for img_path in image_files:
    gt_path = entities_dir / img_path.with_suffix('.txt').name
    if gt_path.exists():
        all_samples.append((img_path, gt_path))

print(f"Found {len(all_samples)} images with ground truth")

# Split into 3 batches
batch_size = len(all_samples) // 3
remainder = len(all_samples) % 3

# Batch ranges
if batch_num == 1:
    start_idx = 0
    end_idx = batch_size + (1 if remainder > 0 else 0)
elif batch_num == 2:
    start_idx = batch_size + (1 if remainder > 0 else 0)
    end_idx = start_idx + batch_size + (1 if remainder > 1 else 0)
else:  # batch 3
    start_idx = 2 * batch_size + (2 if remainder > 1 else 1 if remainder > 0 else 0)
    end_idx = len(all_samples)

samples = all_samples[start_idx:end_idx]

# Check for existing results
output_dir = Path("results/paddleocr_sroie_full/batches")
output_dir.mkdir(parents=True, exist_ok=True)
batch_file = output_dir / f"batch_{batch_num}_results.json"

existing_results = load_existing_results(batch_file)
processed_images = {r['image'] for r in existing_results}

# Filter out already processed images
remaining_samples = [(img, gt) for img, gt in samples if img.name not in processed_images]

if not remaining_samples:
    print(f"✅ Batch {batch_num} already complete! All {len(samples)} images processed.")
    sys.exit(0)

print(f"\n📊 Resume Status:")
print(f"   Total images in batch: {len(samples)}")
print(f"   Already processed: {len(processed_images)}")
print(f"   Remaining: {len(remaining_samples)}")
print(f"   Starting from image: {len(processed_images) + 1}/{len(samples)}")

print(f"\nEstimated time for remaining: {len(remaining_samples) * 8 / 60:.1f} minutes\n")

# Initialize PaddleOCR once
print("🔧 Initializing PaddleOCR...")
ocr = PaddleOCR(use_textline_orientation=True, lang='en')
print("✅ PaddleOCR ready!")
print()

# Start with existing results
results = existing_results.copy()
start_benchmark = time.time()

for idx, (img_path, gt_path) in enumerate(remaining_samples, 1):
    global_idx = start_idx + len(processed_images) + idx
    overall_batch_idx = len(processed_images) + idx
    
    print(f"[{overall_batch_idx}/{len(samples)}] (Global: {global_idx}/{len(all_samples)}) Processing: {img_path.name}")

    # Load ground truth
    ground_truth = load_ground_truth(gt_path)

    try:
        # Preprocess large images to avoid timeouts
        processed_img_path, skipped = preprocess_large_image(img_path, max_dimension=2500, skip_threshold=4500)
        
        if skipped:
            # Image intentionally skipped due to size
            results.append({
                "image": img_path.name,
                "ground_truth": ground_truth,
                "skipped": "Image too large (>4500px), causes WSL crash"
            })
            print(f"   ⏭️  Skipped")
            continue
        
        if processed_img_path is None:
            raise Exception("Failed to load image")
        
        # Run OCR with timeout (60 seconds per image)
        start_time = time.time()
        try:
            with time_limit(60):
                ocr_results = ocr.predict(str(processed_img_path), use_textline_orientation=True)
        except TimeoutException:
            raise Exception("OCR processing timed out after 60 seconds")
        
        elapsed = time.time() - start_time
        
        # Clean up temp file if created
        if processed_img_path != img_path and processed_img_path.exists():
            processed_img_path.unlink()

        # Extract text and boxes
        if ocr_results and len(ocr_results) > 0:
            result = ocr_results[0]
            texts = result.get('rec_texts', [])
            scores = result.get('rec_scores', [])
            boxes = result.get('dt_polys', [])

            # Combine all text
            all_text = ' '.join(texts)
            avg_confidence = sum(scores) / len(scores) if scores else 0

            # Simple fuzzy text matching
            merchant_found = fuzzy_match(ground_truth['merchant_name'], all_text)
            date_found = (ground_truth['transaction_date'] in all_text or
                         ground_truth['transaction_date'].replace('/', '-') in all_text or
                         ground_truth['transaction_date'].replace('/', '.') in all_text)
            total_found = ground_truth['total_amount'] in all_text

            result_entry = {
                "image": img_path.name,
                "ground_truth": ground_truth,
                "extracted_lines": len(texts),
                "avg_confidence": avg_confidence,
                "time_seconds": elapsed,
                "merchant_match": merchant_found,
                "date_match": date_found,
                "total_match": total_found,
                "extracted_text": all_text
            }

            print(f"   ✅ {len(texts)} lines, conf={avg_confidence:.2f}, time={elapsed:.2f}s")
            print(f"   Merchant: {'✅' if merchant_found else '❌'} | Date: {'✅' if date_found else '❌'} | Total: {'✅' if total_found else '❌'}")

        else:
            result_entry = {
                "image": img_path.name,
                "ground_truth": ground_truth,
                "error": "No OCR results"
            }
            print(f"   ❌ No results")

        results.append(result_entry)
        
        # Save progress every 10 images
        if idx % 10 == 0:
            successful = [r for r in results if "error" not in r]
            batch_metrics = {
                "batch_number": batch_num,
                "progress": f"{len(results)}/{len(samples)}",
                "successful": len(successful),
                "in_progress": True
            }
            save_results_incremental(batch_file, {
                "timestamp": datetime.now().isoformat(),
                "dataset": "sroie_full",
                "batch_number": batch_num,
                "status": "in_progress"
            }, batch_metrics, results)
            print(f"   💾 Progress saved ({len(results)}/{len(samples)})")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        
        # Clean up temp file if it exists
        temp_file = img_path.parent / f"temp_resized_{img_path.name}"
        if temp_file.exists():
            temp_file.unlink()
        
        results.append({
            "image": img_path.name,
            "ground_truth": ground_truth,
            "error": str(e)
        })

    # Progress update every 25 images
    if overall_batch_idx % 25 == 0:
        elapsed_time = time.time() - start_benchmark
        avg_time_per_image = elapsed_time / idx
        remaining_images = len(remaining_samples) - idx
        eta_seconds = remaining_images * avg_time_per_image
        print(f"\n   📊 Progress: {overall_batch_idx}/{len(samples)} ({overall_batch_idx/len(samples)*100:.1f}%)")
        print(f"   ⏱️  Elapsed: {elapsed_time/60:.1f} min | ETA: {eta_seconds/60:.1f} min\n")

total_benchmark_time = time.time() - start_benchmark
print(f"\n⏱️  Batch {batch_num} benchmark time: {total_benchmark_time/60:.1f} minutes")

# Calculate final batch metrics
print("\n" + "=" * 80)
print(f"BATCH {batch_num} METRICS")
print("=" * 80)

successful = [r for r in results if "error" not in r]
failed = [r for r in results if "error" in r]

merchant_correct = sum(1 for r in successful if r.get('merchant_match', False))
date_correct = sum(1 for r in successful if r.get('date_match', False))
total_correct = sum(1 for r in successful if r.get('total_match', False))
all_correct = sum(1 for r in successful if r.get('merchant_match', False) and r.get('date_match', False) and r.get('total_match', False))

total_samples = len(successful)

batch_metrics = {
    "batch_number": batch_num,
    "batch_range": f"{start_idx+1}-{end_idx}",
    "total_images": len(samples),
    "successful": len(successful),
    "failed": len(failed),
    "merchant_accuracy": (merchant_correct / total_samples * 100) if total_samples > 0 else 0,
    "date_accuracy": (date_correct / total_samples * 100) if total_samples > 0 else 0,
    "total_accuracy": (total_correct / total_samples * 100) if total_samples > 0 else 0,
    "overall_accuracy": (all_correct / total_samples * 100) if total_samples > 0 else 0,
    "avg_time": sum(r['time_seconds'] for r in successful) / len(successful) if successful else 0,
    "avg_confidence": sum(r['avg_confidence'] for r in successful) / len(successful) if successful else 0,
    "benchmark_time_minutes": total_benchmark_time / 60
}

print(f"\n📊 Batch {batch_num} Results:")
print(f"   Images: {batch_metrics['total_images']}")
print(f"   Success: {batch_metrics['successful']} ({batch_metrics['successful']/batch_metrics['total_images']*100:.1f}%)")
print(f"   Failed: {batch_metrics['failed']}")
print(f"\n📈 Accuracy:")
print(f"   Merchant Name: {batch_metrics['merchant_accuracy']:.1f}%")
print(f"   Date: {batch_metrics['date_accuracy']:.1f}%")
print(f"   Total Amount: {batch_metrics['total_accuracy']:.1f}%")
print(f"   Overall (all fields): {batch_metrics['overall_accuracy']:.1f}%")
print(f"\n⏱️  Performance:")
print(f"   Avg Time per Image: {batch_metrics['avg_time']:.2f}s")
print(f"   Batch Time: {batch_metrics['benchmark_time_minutes']:.1f} minutes")
print(f"   Avg Confidence: {batch_metrics['avg_confidence']:.2f}")

# Save final batch results
save_results_incremental(batch_file, {
    "timestamp": datetime.now().isoformat(),
    "dataset": "sroie_full",
    "batch_number": batch_num,
    "batch_range": f"{start_idx+1}-{end_idx}",
    "num_samples": len(samples),
    "benchmark_time_minutes": batch_metrics['benchmark_time_minutes'],
    "status": "complete"
}, batch_metrics, results)

print(f"\n💾 Batch {batch_num} results saved to: {batch_file}")
print("=" * 80)
print(f"✅ BATCH {batch_num} COMPLETE!")
print("=" * 80)
print(f"\nNext steps:")
if batch_num < 3:
    print(f"  - Run batch {batch_num + 1}: python scripts/benchmark_paddleocr_batch_resume.py {batch_num + 1}")
else:
    print(f"  - Combine all results: python scripts/combine_batch_results.py")
