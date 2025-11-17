#!/usr/bin/env python3
"""
Gemini Vision API benchmark on FULL SROIE dataset
Tests direct image-to-structured-data extraction using Google Gemini Flash (FREE tier)
Usage: python benchmark_gemini_full.py
Requires: GEMINI_API_KEY in .env or environment
Get free API key: https://aistudio.google.com/app/apikey
"""
import sys
import json
import time
from pathlib import Path
from datetime import datetime
import os
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image

load_dotenv()

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
print("GEMINI FLASH VISION API BENCHMARK - FULL DATASET")
print("Direct Image-to-JSON Extraction (FREE TIER)")
print("=" * 80)

# Check for API key
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print("❌ GEMINI_API_KEY not found!")
    print("\n📝 Get a free API key:")
    print("   1. Go to: https://aistudio.google.com/app/apikey")
    print("   2. Click 'Create API Key'")
    print("   3. Add to .env file: GEMINI_API_KEY=your_key_here")
    sys.exit(1)

# Configure Gemini
genai.configure(api_key=api_key)

# Create model with optimal settings for OCR
generation_config = {
    "temperature": 0.1,  # Low temperature for consistent extraction
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 2048,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",  # Free tier model
    generation_config=generation_config,
    safety_settings=safety_settings
)

print("✅ Gemini Flash configured!")

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
output_dir = Path("results/gemini_sroie_full")
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
print(f"Estimated time: {len(all_samples) * 3 / 60:.1f} minutes (at ~3s/image)")
print(f"Rate limit: 15 requests/minute (waiting 4s between requests)\n")

# Prompt for Gemini
PROMPT = """You are a professional OCR system specialized in receipt data extraction.

Analyze this receipt image and extract the following information:
- Merchant/store name (the main business name, not registration numbers)
- Transaction date (in YYYY-MM-DD format if possible)
- Total amount (the final total paid)

Return ONLY a valid JSON object with these exact fields (no markdown, no explanations):
{
  "merchant_name": "exact merchant name from receipt",
  "transaction_date": "date in YYYY-MM-DD or original format",
  "total_amount": "total amount as string"
}

If any field cannot be determined, use an empty string "".
"""

# Process each sample
start_benchmark = time.time()
request_count = 0
last_request_time = time.time()

for idx, (img_path, gt_path) in enumerate(all_samples, 1):
    global_idx = len(results) + 1
    print(f"[{idx}/{len(all_samples)}] (Global: {global_idx}/{len(all_samples) + len(results) - len(all_samples)}) Processing: {img_path.name}")

    # Load ground truth
    ground_truth = load_ground_truth(gt_path)

    try:
        # Rate limiting: Wait 4 seconds between requests (15 req/min limit)
        if request_count > 0:
            elapsed_since_last = time.time() - last_request_time
            if elapsed_since_last < 4.0:
                wait_time = 4.0 - elapsed_since_last
                time.sleep(wait_time)
        
        # Load and process image
        img = Image.open(img_path)
        
        # Generate content
        start_time = time.time()
        response = model.generate_content([PROMPT, img])
        elapsed = time.time() - start_time
        
        last_request_time = time.time()
        request_count += 1

        # Parse response
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        # Parse JSON
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            raise Exception(f"Failed to parse JSON response: {response_text[:100]}")

        # Extract fields
        merchant_pred = result.get('merchant_name', '')
        date_pred = normalize_date(result.get('transaction_date', ''))
        total_pred = result.get('total_amount', '')

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
        print(f"   ❌ Error: {e}")
        results.append({
            "image": img_path.name,
            "ground_truth": ground_truth,
            "error": str(e)
        })

    # Save progress every 10 images
    if idx % 10 == 0:
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
            "model": "gemini-1.5-flash",
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
    "model": "gemini-1.5-flash",
    "num_samples": len(results),
    "benchmark_time_minutes": metrics['benchmark_time_minutes'],
    "status": "complete"
}, metrics, results)

print(f"\n💾 Results saved to: {output_file}")
print("=" * 80)
print("✅ BENCHMARK COMPLETE!")
print("=" * 80)
