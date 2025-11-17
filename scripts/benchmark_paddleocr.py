#!/usr/bin/env python3
"""
Simple PaddleOCR benchmark on SROIE Clear dataset
Focus on what works - just PaddleOCR extraction and accuracy metrics
"""
import sys
import json
import time
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from paddleocr import PaddleOCR

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

print("=" * 80)
print("PADDLEOCR BENCHMARK ON SROIE CLEAR")
print("=" * 80)

# Find all images with ground truth
dataset_dir = Path("data/sroie_clear")
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

print(f"Found {len(samples)} images with ground truth\n")

# Initialize PaddleOCR once
print("🔧 Initializing PaddleOCR...")
ocr = PaddleOCR(use_textline_orientation=True, lang='en')
print("✅ PaddleOCR ready!\n")

# Process each sample
results = []
for idx, (img_path, gt_path) in enumerate(samples, 1):
    print(f"[{idx}/{len(samples)}] Processing: {img_path.name}")

    # Load ground truth
    ground_truth = load_ground_truth(gt_path)

    try:
        # Run OCR
        start_time = time.time()
        ocr_results = ocr.predict(str(img_path), use_textline_orientation=True)
        elapsed = time.time() - start_time

        # Extract text
        if ocr_results and len(ocr_results) > 0:
            result = ocr_results[0]
            texts = result.get('rec_texts', [])
            scores = result.get('rec_scores', [])

            # Combine all text
            all_text = '\n'.join(texts)
            avg_confidence = sum(scores) / len(scores) if scores else 0

            # Check if key fields are present in extracted text
            merchant_found = fuzzy_match(ground_truth['merchant_name'], all_text)
            date_found = fuzzy_match(ground_truth['transaction_date'].replace('/', '-'), all_text)
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

    except Exception as e:
        print(f"   ❌ Error: {e}")
        results.append({
            "image": img_path.name,
            "ground_truth": ground_truth,
            "error": str(e)
        })

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
    "avg_confidence": sum(r['avg_confidence'] for r in successful) / len(successful) if successful else 0
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
print(f"   Avg Time: {metrics['avg_time']:.2f}s")
print(f"   Avg Confidence: {metrics['avg_confidence']:.2f}")

# Save results
output_dir = Path("results/paddleocr_sroie_clear")
output_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
results_file = output_dir / f"results_{timestamp}.json"

with open(results_file, 'w') as f:
    json.dump({
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "dataset": "sroie_clear",
            "num_samples": len(samples)
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
colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c']
bars = ax.bar(fields, accuracies, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)

# Add value labels on bars
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=12)

ax.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
ax.set_title(f'PaddleOCR Field Accuracy on SROIE Clear ({len(samples)} images)',
             fontsize=14, fontweight='bold')
ax.set_ylim(0, 105)
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(plots_dir / 'field_accuracy.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"✅ Saved: {plots_dir / 'field_accuracy.png'}")

# 2. Per-sample accuracy heatmap
fig, ax = plt.subplots(figsize=(12, 8))
sample_accuracies = []
for r in successful[:50]:  # Limit to 50 for readability
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
    ax.set_title('Per-Sample Field Accuracy Heatmap', fontsize=14, fontweight='bold')
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Accuracy (%)', fontsize=12, fontweight='bold')
    plt.tight_layout()
    plt.savefig(plots_dir / 'per_sample_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ Saved: {plots_dir / 'per_sample_heatmap.png'}")

# 3. Confidence distribution
fig, ax = plt.subplots(figsize=(10, 6))
confidences = [r['avg_confidence'] for r in successful]
ax.hist(confidences, bins=20, color='#3498db', alpha=0.7, edgecolor='black')
ax.axvline(metrics['avg_confidence'], color='red', linestyle='--', linewidth=2,
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
ax.hist(times, bins=20, color='#2ecc71', alpha=0.7, edgecolor='black')
ax.axvline(metrics['avg_time'], color='red', linestyle='--', linewidth=2,
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

Dataset: SROIE Clear
Total Images: {metrics['total_images']}
Successful: {metrics['successful']} ({metrics['successful']/metrics['total_images']*100:.1f}%)
Failed: {metrics['failed']}

📈 ACCURACY
Merchant Name: {metrics['merchant_accuracy']:.1f}%
Transaction Date: {metrics['date_accuracy']:.1f}%
Total Amount: {metrics['total_accuracy']:.1f}%
Overall: {metrics['overall_accuracy']:.1f}%

⏱️ PERFORMANCE
Avg Time: {metrics['avg_time']:.2f}s
Avg Confidence: {metrics['avg_confidence']:.2f}

🔧 ENGINE
PaddleOCR PP-OCRv5
Language: English
Orientation: Enabled
"""
ax2.text(0.1, 0.9, stats_text, transform=ax2.transAxes, fontsize=11,
         verticalalignment='top', fontfamily='monospace',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

# Bottom left: Confidence histogram
ax3 = fig.add_subplot(gs[1, 0])
ax3.hist(confidences, bins=15, color='#3498db', alpha=0.7, edgecolor='black')
ax3.axvline(metrics['avg_confidence'], color='red', linestyle='--', linewidth=2)
ax3.set_xlabel('Confidence', fontweight='bold')
ax3.set_ylabel('Count', fontweight='bold')
ax3.set_title('Confidence Distribution', fontweight='bold')
ax3.grid(axis='y', alpha=0.3)

# Bottom right: Time histogram
ax4 = fig.add_subplot(gs[1, 1])
ax4.hist(times, bins=15, color='#2ecc71', alpha=0.7, edgecolor='black')
ax4.axvline(metrics['avg_time'], color='red', linestyle='--', linewidth=2)
ax4.set_xlabel('Time (seconds)', fontweight='bold')
ax4.set_ylabel('Count', fontweight='bold')
ax4.set_title('Processing Time Distribution', fontweight='bold')
ax4.grid(axis='y', alpha=0.3)

fig.suptitle('PaddleOCR Performance on SROIE Clear Dataset', fontsize=16, fontweight='bold')
plt.savefig(plots_dir / 'summary_dashboard.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"✅ Saved: {plots_dir / 'summary_dashboard.png'}")

print(f"\n✅ All visualizations saved to: {plots_dir}/")
print("=" * 80)
print("✅ BENCHMARK COMPLETE!")
print("=" * 80)
