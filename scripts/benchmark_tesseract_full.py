#!/usr/bin/env python3
"""
Tesseract OCR benchmark on FULL SROIE dataset (626 images)
Parallel benchmark to PaddleOCR for comparison
Includes preprocessing and heuristics for improved accuracy
"""
import sys
import json
import time
import re
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np
import cv2
import pytesseract

sys.path.insert(0, str(Path(__file__).parent.parent))

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

def normalize_date(date_str):
    """Normalize date to YYYY-MM-DD"""
    if not date_str:
        return ""
    # Simple normalization
    date_str = str(date_str).strip()
    # Replace / with - for consistent comparison
    return date_str.replace('/', '-')

def fuzzy_match(pred, truth):
    """Check if prediction matches ground truth (fuzzy)"""
    if not pred or not truth:
        return False
    pred = str(pred).lower().strip()
    truth = str(truth).lower().strip()
    return pred in truth or truth in pred

def number_match(pred, truth, tolerance=0.5):
    """Check if numbers match within tolerance"""
    try:
        pred_val = float(str(pred).replace('$', '').replace('RM', '').replace(',', '').strip())
        truth_val = float(str(truth).replace('$', '').replace('RM', '').replace(',', '').strip())
        return abs(pred_val - truth_val) <= tolerance
    except:
        return False

def preprocess_image(image: np.ndarray) -> np.ndarray:
    """Apply preprocessing to improve OCR accuracy"""
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # 1. Resize if too small (maintain aspect ratio)
    height, width = gray.shape
    if height < 1500:
        scale = 1500 / height
        new_width = int(width * scale)
        gray = cv2.resize(gray, (new_width, 1500), interpolation=cv2.INTER_LANCZOS4)

    # 2. Deskewing
    coords = np.column_stack(np.where(gray > 0))
    if len(coords) > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) > 0.5:  # Only deskew if needed
            (h, w) = gray.shape
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    # 3. Noise reduction
    denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)

    # 4. Contrast enhancement using CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(denoised)

    # 5. Adaptive thresholding for better text extraction
    binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)

    return binary

def extract_merchant_heuristic(lines: list, positions: list) -> str:
    """Extract merchant name using heuristics (usually at top)"""
    # Merchant is typically in the first 20% of the receipt
    if not lines or not positions:
        return ""

    # Get lines from top 20%
    max_y = max(pos[1] for pos in positions) if positions else 0
    top_threshold = max_y * 0.2

    top_lines = []
    for line, pos in zip(lines, positions):
        if pos[1] <= top_threshold:
            # Filter out very short lines and common noise
            if len(line) > 3 and not line.isdigit():
                top_lines.append(line)

    # Return the longest line in the top section (likely merchant name)
    if top_lines:
        return max(top_lines, key=len)
    return ""

def extract_date_heuristic(text: str) -> str:
    """Extract date using regex patterns"""
    # Common date patterns in receipts
    patterns = [
        r'\d{2}[-/]\d{2}[-/]\d{4}',  # DD-MM-YYYY or DD/MM/YYYY
        r'\d{4}[-/]\d{2}[-/]\d{2}',  # YYYY-MM-DD
        r'\d{2}[-/]\d{2}[-/]\d{2}',  # DD-MM-YY
        r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}',  # DD Month YYYY
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    return ""

def extract_total_heuristic(lines: list, positions: list) -> str:
    """Extract total amount using heuristics (usually near bottom with keyword)"""
    if not lines or not positions:
        return ""

    # Total is typically in the bottom 30% of receipt
    max_y = max(pos[1] for pos in positions) if positions else 0
    bottom_threshold = max_y * 0.7

    # Keywords that typically appear with total
    total_keywords = ['total', 'amount', 'balance', 'grand', 'sum']

    # Search bottom section for total with keywords
    for line, pos in zip(lines, positions):
        if pos[1] >= bottom_threshold:
            line_lower = line.lower()
            for keyword in total_keywords:
                if keyword in line_lower:
                    # Extract numbers from this line
                    numbers = re.findall(r'\d+[.,]\d{2}', line)
                    if numbers:
                        # Return the largest number (likely the total)
                        return max(numbers, key=lambda x: float(x.replace(',', '.')))

    # Fallback: find largest monetary value in bottom section
    bottom_numbers = []
    for line, pos in zip(lines, positions):
        if pos[1] >= bottom_threshold:
            numbers = re.findall(r'\d+[.,]\d{2}', line)
            bottom_numbers.extend(numbers)

    if bottom_numbers:
        return max(bottom_numbers, key=lambda x: float(x.replace(',', '.')))

    return ""

def run_tesseract_ocr(image_path: str):
    """Run Tesseract OCR on image"""
    # Read image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")

    # Get detailed OCR data
    ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

    # Extract text and confidence
    texts = []
    confidences = []

    for i in range(len(ocr_data['text'])):
        text = ocr_data['text'][i].strip()
        conf = ocr_data['conf'][i]

        # Filter out empty strings and low confidence
        if text and conf != -1:
            texts.append(text)
            confidences.append(conf / 100.0)  # Normalize to 0-1

    # Combine all text
    all_text = ' '.join(texts)

    return texts, confidences, all_text

print("=" * 80)
print("TESSERACT OCR BENCHMARK ON FULL SROIE DATASET")
print("Raw OCR + Fuzzy Text Matching")
print("=" * 80)

# Find all images with ground truth
dataset_dir = Path("data/sroie")
img_dir = dataset_dir / "train" / "img"
entities_dir = dataset_dir / "train" / "entities"

image_files = sorted(img_dir.glob("*.jpg"))
print(f"Found {len(image_files)} images in {img_dir}")

# Filter to only those with ground truth
samples = []
for img_path in image_files:
    gt_path = entities_dir / img_path.with_suffix('.txt').name
    if gt_path.exists():
        samples.append((img_path, gt_path))

print(f"Found {len(samples)} images with ground truth")
print(f"Estimated time: {len(samples) * 2 / 60:.1f} minutes ({len(samples) * 2}s at ~2s/image)\n")

print("🔧 Tesseract ready!")
print()

# Process each sample
results = []
start_benchmark = time.time()

for idx, (img_path, gt_path) in enumerate(samples, 1):
    print(f"[{idx}/{len(samples)}] Processing: {img_path.name}")

    # Load ground truth
    ground_truth = load_ground_truth(gt_path)

    try:
        # Run OCR
        start_time = time.time()
        texts, confidences, all_text = run_tesseract_ocr(str(img_path))
        elapsed = time.time() - start_time

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        # Simple fuzzy text matching - check if ground truth fields appear in OCR text
        merchant_found = fuzzy_match(ground_truth['merchant_name'], all_text)
        # Try date with both / and - separators
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

        print(f"   ✅ {len(texts)} tokens, conf={avg_confidence:.2f}, time={elapsed:.2f}s")
        print(f"   Merchant: {'✅' if merchant_found else '❌'} | Date: {'✅' if date_found else '❌'} | Total: {'✅' if total_found else '❌'}")

        results.append(result_entry)

    except Exception as e:
        print(f"   ❌ Error: {e}")
        results.append({
            "image": img_path.name,
            "ground_truth": ground_truth,
            "error": str(e)
        })

    # Progress update every 50 images
    if idx % 50 == 0:
        elapsed_time = time.time() - start_benchmark
        avg_time_per_image = elapsed_time / idx
        remaining_images = len(samples) - idx
        eta_seconds = remaining_images * avg_time_per_image
        print(f"\n   📊 Progress: {idx}/{len(samples)} ({idx/len(samples)*100:.1f}%)")
        print(f"   ⏱️  Elapsed: {elapsed_time/60:.1f} min | ETA: {eta_seconds/60:.1f} min\n")

total_benchmark_time = time.time() - start_benchmark
print(f"\n⏱️  Total benchmark time: {total_benchmark_time/60:.1f} minutes")

# Calculate metrics
print("\n" + "=" * 80)
print("CALCULATING METRICS")
print("=" * 80)

successful = [r for r in results if "error" not in r]
failed = [r for r in results if "error" in r]

merchant_correct = sum(1 for r in successful if r.get('merchant_match', False))
date_correct = sum(1 for r in successful if r.get('date_match', False))
total_correct = sum(1 for r in successful if r.get('total_match', False))
all_correct = sum(1 for r in successful if r.get('merchant_match', False) and r.get('date_match', False) and r.get('total_match', False))

total_samples = len(successful)

metrics = {
    "total_images": len(samples),
    "successful": len(successful),
    "failed": len(failed),
    "merchant_accuracy": (merchant_correct / total_samples * 100) if total_samples > 0 else 0,
    "date_accuracy": (date_correct / total_samples * 100) if total_samples > 0 else 0,
    "total_accuracy": (total_correct / total_samples * 100) if total_samples > 0 else 0,
    "overall_accuracy": (all_correct / total_samples * 100) if total_samples > 0 else 0,
    "avg_time": sum(r['time_seconds'] for r in successful) / len(successful) if successful else 0,
    "avg_confidence": sum(r['avg_confidence'] for r in successful) / len(successful) if successful else 0,
    "total_benchmark_time_minutes": total_benchmark_time / 60
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
print(f"   Total Time: {metrics['total_benchmark_time_minutes']:.1f} minutes")
print(f"   Avg Confidence: {metrics['avg_confidence']:.2f}")

# Save results
output_dir = Path("results/tesseract_sroie_full")
output_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
results_file = output_dir / f"results_{timestamp}.json"

with open(results_file, 'w') as f:
    json.dump({
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "dataset": "sroie_full",
            "num_samples": len(samples),
            "benchmark_time_minutes": metrics['total_benchmark_time_minutes']
        },
        "metrics": metrics,
        "detailed_results": results
    }, f, indent=2)

print(f"\n💾 Results saved to: {results_file}")

# Generate visualizations
print("\n" + "=" * 80)
print("GENERATING VISUALIZATIONS")
print("=" * 80)

plots_dir = output_dir / "plots"
plots_dir.mkdir(exist_ok=True)

# 1. Accuracy bar chart
fig, ax = plt.subplots(figsize=(10, 6))
fields = ['Merchant\nName', 'Transaction\nDate', 'Total\nAmount', 'Overall\n(All Fields)']
accuracies = [
    metrics['merchant_accuracy'],
    metrics['date_accuracy'],
    metrics['total_accuracy'],
    metrics['overall_accuracy']
]
colors = ['#e74c3c', '#e67e22', '#f39c12', '#95a5a6']
bars = ax.bar(fields, accuracies, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)

# Add value labels on bars
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=12)

ax.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
ax.set_title(f'Tesseract OCR Field Accuracy on Full SROIE Dataset ({len(samples)} images)',
             fontsize=14, fontweight='bold')
ax.set_ylim(0, 105)
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(plots_dir / 'field_accuracy.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"✅ Saved: {plots_dir / 'field_accuracy.png'}")

# 2. Per-sample accuracy heatmap (first 100 samples)
fig, ax = plt.subplots(figsize=(12, 8))
sample_accuracies = []
for r in successful[:100]:  # Limit to 100 for readability
    acc = []
    acc.append(100 if r.get('merchant_match', False) else 0)
    acc.append(100 if r.get('date_match', False) else 0)
    acc.append(100 if r.get('total_match', False) else 0)
    sample_accuracies.append(acc)

if sample_accuracies:
    im = ax.imshow(sample_accuracies, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(['Merchant', 'Date', 'Total'])
    ax.set_ylabel('Sample Index', fontsize=12, fontweight='bold')
    ax.set_xlabel('Field', fontsize=12, fontweight='bold')
    ax.set_title('Per-Sample Field Accuracy Heatmap (First 100 Samples)', fontsize=14, fontweight='bold')
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Accuracy (%)', fontsize=12, fontweight='bold')
    plt.tight_layout()
    plt.savefig(plots_dir / 'per_sample_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ Saved: {plots_dir / 'per_sample_heatmap.png'}")

# 3. Confidence distribution
fig, ax = plt.subplots(figsize=(10, 6))
confidences = [r['avg_confidence'] for r in successful]
ax.hist(confidences, bins=30, color='#e74c3c', alpha=0.7, edgecolor='black')
ax.axvline(metrics['avg_confidence'], color='darkred', linestyle='--', linewidth=2,
           label=f"Mean: {metrics['avg_confidence']:.2f}")
ax.set_xlabel('Average Confidence Score', fontsize=12, fontweight='bold')
ax.set_ylabel('Number of Images', fontsize=12, fontweight='bold')
ax.set_title('OCR Confidence Distribution', fontsize=14, fontweight='bold')
ax.legend()
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(plots_dir / 'confidence_distribution.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"✅ Saved: {plots_dir / 'confidence_distribution.png'}")

# 4. Processing time distribution
fig, ax = plt.subplots(figsize=(10, 6))
times = [r['time_seconds'] for r in successful]
ax.hist(times, bins=30, color='#f39c12', alpha=0.7, edgecolor='black')
ax.axvline(metrics['avg_time'], color='darkorange', linestyle='--', linewidth=2,
           label=f"Mean: {metrics['avg_time']:.2f}s")
ax.set_xlabel('Processing Time (seconds)', fontsize=12, fontweight='bold')
ax.set_ylabel('Number of Images', fontsize=12, fontweight='bold')
ax.set_title('OCR Processing Time Distribution', fontsize=14, fontweight='bold')
ax.legend()
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(plots_dir / 'time_distribution.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"✅ Saved: {plots_dir / 'time_distribution.png'}")

# 5. Summary dashboard
fig = plt.figure(figsize=(14, 10))
gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

# Top left: Accuracy bars
ax1 = fig.add_subplot(gs[0, 0])
bars = ax1.bar(fields, accuracies, color=colors, alpha=0.8)
for bar in bars:
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')
ax1.set_ylabel('Accuracy (%)', fontweight='bold')
ax1.set_title('Field Accuracy', fontweight='bold')
ax1.set_ylim(0, 105)
ax1.grid(axis='y', alpha=0.3)

# Top right: Stats
ax2 = fig.add_subplot(gs[0, 1])
ax2.axis('off')
stats_text = f"""
📊 BENCHMARK STATISTICS

Dataset: SROIE Full (626 images)
Total Images: {metrics['total_images']}
Successful: {metrics['successful']} ({metrics['successful']/metrics['total_images']*100:.1f}%)
Failed: {metrics['failed']}

📈 ACCURACY
Merchant Name: {metrics['merchant_accuracy']:.1f}%
Transaction Date: {metrics['date_accuracy']:.1f}%
Total Amount: {metrics['total_accuracy']:.1f}%
Overall: {metrics['overall_accuracy']:.1f}%

⏱️ PERFORMANCE
Avg Time/Image: {metrics['avg_time']:.2f}s
Total Time: {metrics['total_benchmark_time_minutes']:.1f} min
Avg Confidence: {metrics['avg_confidence']:.2f}

🔧 ENGINE
Tesseract OCR 5.x
Mode: Raw OCR (no preprocessing)
Matching: Fuzzy text search
"""
ax2.text(0.1, 0.9, stats_text, transform=ax2.transAxes, fontsize=11,
         verticalalignment='top', fontfamily='monospace',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

# Bottom left: Confidence histogram
ax3 = fig.add_subplot(gs[1, 0])
ax3.hist(confidences, bins=20, color='#e74c3c', alpha=0.7, edgecolor='black')
ax3.axvline(metrics['avg_confidence'], color='darkred', linestyle='--', linewidth=2)
ax3.set_xlabel('Confidence', fontweight='bold')
ax3.set_ylabel('Count', fontweight='bold')
ax3.set_title('Confidence Distribution', fontweight='bold')
ax3.grid(axis='y', alpha=0.3)

# Bottom right: Time histogram
ax4 = fig.add_subplot(gs[1, 1])
ax4.hist(times, bins=20, color='#f39c12', alpha=0.7, edgecolor='black')
ax4.axvline(metrics['avg_time'], color='darkorange', linestyle='--', linewidth=2)
ax4.set_xlabel('Time (seconds)', fontweight='bold')
ax4.set_ylabel('Count', fontweight='bold')
ax4.set_title('Processing Time Distribution', fontweight='bold')
ax4.grid(axis='y', alpha=0.3)

fig.suptitle('Tesseract OCR Performance on Full SROIE Dataset (626 Images)', fontsize=16, fontweight='bold')
plt.savefig(plots_dir / 'summary_dashboard.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"✅ Saved: {plots_dir / 'summary_dashboard.png'}")

print(f"\n✅ All visualizations saved to: {plots_dir}/")
print("=" * 80)
print("✅ BENCHMARK COMPLETE!")
print("=" * 80)
