#!/usr/bin/env python3
"""
Qwen2.5-VL Vision LLM benchmark on FULL SROIE dataset
Tests direct image-to-structured-data extraction
Usage: python benchmark_qwen_full.py
"""
import sys
import json
import time
from pathlib import Path
from datetime import datetime
import signal
from contextlib import contextmanager

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.llm.vision_llm_processor import VisionLLMProcessor

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

def normalize_date(date_str: str) -> str:
    """Normalize date to YYYY-MM-DD format for comparison"""
    if not date_str:
        return ""
    
    from datetime import datetime
    
    # Common date formats found in receipts
    formats = [
        '%d/%m/%Y',    # 25/12/2018
        '%d-%m-%Y',    # 25-12-2018
        '%d.%m.%Y',    # 25.12.2018
        '%Y-%m-%d',    # 2018-12-25 (ISO)
        '%d/%m/%y',    # 25/12/18
        '%d-%m-%y',    # 25-12-18
        '%Y/%m/%d',    # 2018/12/25
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime('%Y-%m-%d')  # Return as ISO format
        except ValueError:
            continue
    
    # If parsing fails, return original
    return date_str

def load_existing_results(output_file: Path):
    """Load existing results if file exists"""
    if output_file.exists():
        with open(output_file, 'r') as f:
            data = json.load(f)
            return data.get('detailed_results', [])
    return []

def save_results_incremental(output_file: Path, metadata, metrics, results):
    """Save results incrementally"""
    with open(output_file, 'w') as f:
        json.dump({
            "metadata": metadata,
            "metrics": metrics,
            "detailed_results": results
        }, f, indent=2)

print("=" * 80)
print("QWEN2.5-VL VISION LLM BENCHMARK - FULL DATASET")
print("Direct Image-to-JSON Extraction")
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

# Check for existing results
output_dir = Path("results/qwen_sroie_full")
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

# Check if we should resume from an existing file
existing_files = sorted(output_dir.glob("results_*.json"))
if existing_files:
    latest_file = existing_files[-1]
    print(f"\n📂 Found existing results: {latest_file.name}")
    response = input("Resume from this file? (y/n): ").lower()
    if response == 'y':
        output_file = latest_file
        existing_results = load_existing_results(output_file)
        processed_images = {r['image'] for r in existing_results}
        remaining_samples = [(img, gt) for img, gt in all_samples if img.name not in processed_images]
        
        print(f"\n📊 Resume Status:")
        print(f"   Already processed: {len(processed_images)}")
        print(f"   Remaining: {len(remaining_samples)}")
        
        if not remaining_samples:
            print("✅ All images already processed!")
            sys.exit(0)
        
        all_samples = remaining_samples
        results = existing_results.copy()
    else:
        results = []
else:
    results = []

print(f"\nProcessing {len(all_samples)} receipts")
print(f"Estimated time: {len(all_samples) * 60 / 60:.1f} hours (at ~60s/image)\n")

# Initialize Qwen Vision LLM
print("🔧 Initializing Qwen2.5-VL...")
print(f"   Model: qwen2.5vl:7b")
print(f"   Base URL: http://localhost:11434")

vision_llm = VisionLLMProcessor(model="qwen2.5vl:7b")

print("   Checking if model is available...")
if not vision_llm.is_available():
    print("❌ Qwen2.5-VL not available!")
    print("\nTroubleshooting:")
    print("   1. Check if Ollama is running: ollama list")
    print("   2. Pull model if needed: ollama pull qwen2.5vl:7b")
    print("   3. Test model: ollama run qwen2.5vl:7b 'hello'")
    sys.exit(1)

print("✅ Qwen2.5-VL ready!")

# Test on first image
print("\n🧪 Testing on first image...")
test_img, test_gt = all_samples[0]
print(f"   Test image: {test_img.name}")

try:
    print("   Encoding image...")
    encoded = vision_llm.encode_image(str(test_img))
    print(f"   ✅ Image encoded ({len(encoded)} bytes)")
    
    print("   Sending to Qwen2.5-VL (this will take 60-120 seconds on CPU)...")
    print("   ⏳ Processing", end='', flush=True)
    
    import threading
    def show_progress():
        while not done_event.is_set():
            print(".", end='', flush=True)
            time.sleep(5)
    
    done_event = threading.Event()
    progress_thread = threading.Thread(target=show_progress, daemon=True)
    progress_thread.start()
    
    start_test = time.time()
    test_result = vision_llm.structure_receipt_from_image(str(test_img))
    test_time = time.time() - start_test
    
    done_event.set()
    progress_thread.join(timeout=1)
    print()  # New line after dots
    
    print(f"   ✅ Response received in {test_time:.2f}s")
    
    if "error" in test_result:
        print(f"   ❌ Error in response: {test_result['error']}")
        sys.exit(1)
    
    print(f"   Response preview: {json.dumps(test_result, indent=2)[:200]}...")
    print("\n✅ Test successful! Starting full benchmark...\n")
    print("💡 Tip: Each image takes ~60-120s on CPU. Consider using Gemini API instead (much faster).")
    print()
    
except Exception as e:
    print(f"   ❌ Test failed: {e}")
    print("\nDebug info:")
    print(f"   Image path: {test_img}")
    print(f"   Image exists: {test_img.exists()}")
    print(f"   Model: qwen2.5vl:7b")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Process each sample
start_benchmark = time.time()

for idx, (img_path, gt_path) in enumerate(all_samples, 1):
    global_idx = len(results) + 1
    print(f"[{idx}/{len(all_samples)}] (Global: {global_idx}/{len(all_samples) + len(results) - len(all_samples)}) Processing: {img_path.name}")

    # Load ground truth
    ground_truth = load_ground_truth(gt_path)

    try:
        # Run Vision LLM with timeout (120 seconds per image)
        start_time = time.time()
        
        print(f"   📤 Sending to Qwen2.5-VL...", end='', flush=True)
        
        try:
            with time_limit(120):
                result = vision_llm.structure_receipt_from_image(str(img_path))
        except TimeoutException:
            raise Exception("Vision LLM processing timed out after 120 seconds")
        
        elapsed = time.time() - start_time
        print(f" ✅ ({elapsed:.2f}s)")

        # Check for errors
        if "error" in result:
            raise Exception(result["error"])

        # Extract fields
        merchant_pred = result.get('merchant_name', '')
        date_pred = normalize_date(result.get('transaction_date', ''))
        total_pred = result.get('total_amount', '')
        
        print(f"   📝 Extracted: merchant='{merchant_pred[:30]}...' date='{date_pred}' total='{total_pred}'")

        # Normalize ground truth date
        date_truth = normalize_date(ground_truth['transaction_date'])

        # Fuzzy matching
        merchant_found = fuzzy_match(merchant_pred, ground_truth['merchant_name'])
        date_found = fuzzy_match(date_pred, date_truth)
        total_found = fuzzy_match(str(total_pred), ground_truth['total_amount'])

        result_entry = {
            "image": img_path.name,
            "ground_truth": ground_truth,
            "predictions": {
                "merchant_name": merchant_pred,
                "transaction_date": date_pred,
                "total_amount": str(total_pred)
            },
            "time_seconds": elapsed,
            "merchant_match": merchant_found,
            "date_match": date_found,
            "total_match": total_found
        }

        print(f"   ✅ Processed in {elapsed:.2f}s")
        print(f"   Merchant: {'✅' if merchant_found else '❌'} | Date: {'✅' if date_found else '❌'} | Total: {'✅' if total_found else '❌'}")

        results.append(result_entry)

    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ Error: {error_msg}")
        
        # Additional debug info for first few failures
        if len([r for r in results if "error" in r]) < 3:
            print(f"   Debug: Image={img_path.name}, GT={ground_truth}")
        
        results.append({
            "image": img_path.name,
            "ground_truth": ground_truth,
            "error": error_msg
        })

    # Save progress every 5 images
    if idx % 5 == 0:
        successful = [r for r in results if "error" not in r]
        metrics = {
            "progress": f"{len(results)}/{len(all_samples) + len(results) - len(all_samples)}",
            "successful": len(successful),
            "failed": len(results) - len(successful),
            "in_progress": True
        }
        save_results_incremental(output_file, {
            "timestamp": datetime.now().isoformat(),
            "dataset": "sroie_full",
            "model": "qwen2.5vl:7b",
            "status": "in_progress"
        }, metrics, results)
        print(f"   💾 Progress saved ({len(results)} processed)")

    # Progress update every 25 images
    if idx % 25 == 0:
        elapsed_time = time.time() - start_benchmark
        avg_time_per_image = elapsed_time / idx
        remaining_images = len(all_samples) - idx
        eta_seconds = remaining_images * avg_time_per_image
        print(f"\n   📊 Progress: {idx}/{len(all_samples)} ({idx/len(all_samples)*100:.1f}%)")
        print(f"   ⏱️  Elapsed: {elapsed_time/60:.1f} min | ETA: {eta_seconds/60:.1f} min\n")

total_benchmark_time = time.time() - start_benchmark
print(f"\n⏱️  Benchmark time: {total_benchmark_time/60:.1f} minutes")

# Calculate final metrics
print("\n" + "=" * 80)
print("FINAL METRICS")
print("=" * 80)

successful = [r for r in results if "error" not in r]
failed = [r for r in results if "error" in r]

merchant_correct = sum(1 for r in successful if r.get('merchant_match', False))
date_correct = sum(1 for r in successful if r.get('date_match', False))
total_correct = sum(1 for r in successful if r.get('total_match', False))
all_correct = sum(1 for r in successful if r.get('merchant_match', False) and r.get('date_match', False) and r.get('total_match', False))

total_samples = len(successful)

metrics = {
    "total_images": len(results),
    "successful": len(successful),
    "failed": len(failed),
    "merchant_accuracy": (merchant_correct / total_samples * 100) if total_samples > 0 else 0,
    "date_accuracy": (date_correct / total_samples * 100) if total_samples > 0 else 0,
    "total_accuracy": (total_correct / total_samples * 100) if total_samples > 0 else 0,
    "overall_accuracy": (all_correct / total_samples * 100) if total_samples > 0 else 0,
    "avg_time": sum(r.get('time_seconds', 0) for r in successful) / len(successful) if successful else 0,
    "benchmark_time_minutes": total_benchmark_time / 60
}

print(f"\n📊 Results:")
print(f"   Total: {metrics['total_images']}")
print(f"   Success: {metrics['successful']} ({metrics['successful']/metrics['total_images']*100:.1f}%)")
print(f"   Failed: {metrics['failed']}")
print(f"\n📈 Accuracy:")
print(f"   Merchant Name: {metrics['merchant_accuracy']:.1f}%")
print(f"   Date: {metrics['date_accuracy']:.1f}%")
print(f"   Total Amount: {metrics['total_accuracy']:.1f}%")
print(f"   Overall (all fields): {metrics['overall_accuracy']:.1f}%")
print(f"\n⏱️  Performance:")
print(f"   Avg Time per Image: {metrics['avg_time']:.2f}s")
print(f"   Total Time: {metrics['benchmark_time_minutes']:.1f} minutes")

# Save final results
save_results_incremental(output_file, {
    "timestamp": datetime.now().isoformat(),
    "dataset": "sroie_full",
    "model": "qwen2.5vl:7b",
    "num_samples": len(results),
    "benchmark_time_minutes": metrics['benchmark_time_minutes'],
    "status": "complete"
}, metrics, results)

print(f"\n💾 Results saved to: {output_file}")
print("=" * 80)
print("✅ BENCHMARK COMPLETE!")
print("=" * 80)
