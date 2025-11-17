#!/usr/bin/env python3
"""
Combine batch results from PaddleOCR benchmark and generate overall plots
Run after all 3 batches are complete
"""
import json
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np

print("=" * 80)
print("COMBINING BATCH RESULTS")
print("=" * 80)

# Load all batch results
batches_dir = Path("results/paddleocr_sroie_full/batches")

batch_files = []
for i in [1, 2, 3]:
    batch_file = batches_dir / f"batch_{i}_results.json"
    if not batch_file.exists():
        print(f"❌ Missing batch {i} results: {batch_file}")
        print(f"   Please run: python scripts/benchmark_paddleocr_batch.py {i}")
        continue
    batch_files.append(batch_file)

if len(batch_files) != 3:
    print(f"\n❌ Only found {len(batch_files)}/3 batches. Please run all batches first.")
    exit(1)

print(f"✅ Found all 3 batch result files\n")

# Load and combine results
all_results = []
combined_metrics = {
    "total_images": 0,
    "successful": 0,
    "failed": 0,
    "total_benchmark_time_minutes": 0
}

print("Loading batch results...")
for batch_file in sorted(batch_files):
    with open(batch_file, 'r') as f:
        batch_data = json.load(f)
    
    batch_num = batch_data['metadata']['batch_number']
    batch_results = batch_data['detailed_results']
    batch_metrics = batch_data['batch_metrics']
    
    # Handle both old and new key names
    benchmark_time = batch_metrics.get('benchmark_time_minutes') or batch_data['metadata'].get('benchmark_time_minutes', 0)
    print(f"  Batch {batch_num}: {len(batch_results)} images, {benchmark_time:.1f} min")
    
    all_results.extend(batch_results)
    combined_metrics['total_images'] += batch_metrics.get('total_images', len(batch_results))
    combined_metrics['successful'] += batch_metrics.get('successful', len([r for r in batch_results if 'error' not in r and 'skipped' not in r]))
    combined_metrics['failed'] += batch_metrics.get('failed', len([r for r in batch_results if 'error' in r or 'skipped' in r]))
    combined_metrics['total_benchmark_time_minutes'] += benchmark_time

print(f"\n✅ Combined {len(all_results)} results from all batches")

# Calculate overall metrics
print("\n" + "=" * 80)
print("CALCULATING OVERALL METRICS")
print("=" * 80)

successful = [r for r in all_results if "error" not in r and "skipped" not in r]
failed = [r for r in all_results if "error" in r]
skipped = [r for r in all_results if "skipped" in r]

merchant_correct = sum(1 for r in successful if r.get('merchant_match', False))
date_correct = sum(1 for r in successful if r.get('date_match', False))
total_correct = sum(1 for r in successful if r.get('total_match', False))
all_correct = sum(1 for r in successful if r.get('merchant_match', False) and r.get('date_match', False) and r.get('total_match', False))

total_samples = len(successful)

metrics = {
    "total_images": combined_metrics['total_images'],
    "successful": len(successful),
    "failed": len(failed),
    "skipped": len(skipped),
    "merchant_accuracy": (merchant_correct / total_samples * 100) if total_samples > 0 else 0,
    "date_accuracy": (date_correct / total_samples * 100) if total_samples > 0 else 0,
    "total_accuracy": (total_correct / total_samples * 100) if total_samples > 0 else 0,
    "overall_accuracy": (all_correct / total_samples * 100) if total_samples > 0 else 0,
    "avg_time": sum(r.get('time_seconds', 0) for r in successful) / len(successful) if successful else 0,
    "avg_confidence": sum(r.get('avg_confidence', 0) for r in successful) / len(successful) if successful else 0,
    "total_benchmark_time_minutes": combined_metrics['total_benchmark_time_minutes']
}

print(f"\n📊 Overall Results:")
print(f"   Total: {metrics['total_images']}")
print(f"   Success: {metrics['successful']} ({metrics['successful']/metrics['total_images']*100:.1f}%)")
print(f"   Failed: {metrics['failed']}")
if metrics['skipped'] > 0:
    print(f"   Skipped: {metrics['skipped']} (images too large for WSL)")
print(f"\n📈 Accuracy:")
print(f"   Merchant Name: {metrics['merchant_accuracy']:.1f}%")
print(f"   Date: {metrics['date_accuracy']:.1f}%")
print(f"   Total Amount: {metrics['total_accuracy']:.1f}%")
print(f"   Overall (all fields): {metrics['overall_accuracy']:.1f}%")
print(f"\n⏱️  Performance:")
print(f"   Avg Time per Image: {metrics['avg_time']:.2f}s")
print(f"   Total Time: {metrics['total_benchmark_time_minutes']:.1f} minutes")
print(f"   Avg Confidence: {metrics['avg_confidence']:.2f}")

# Save combined results
output_dir = Path("results/paddleocr_sroie_full")
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
results_file = output_dir / f"results_combined_{timestamp}.json"

with open(results_file, 'w') as f:
    json.dump({
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "dataset": "sroie_full",
            "num_samples": len(all_results),
            "benchmark_time_minutes": metrics['total_benchmark_time_minutes'],
            "combined_from_batches": [1, 2, 3]
        },
        "metrics": metrics,
        "detailed_results": all_results
    }, f, indent=2)

print(f"\n💾 Combined results saved to: {results_file}")

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
ax.set_title(f'PaddleOCR Field Accuracy on Full SROIE Dataset ({len(all_results)} images)',
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
ax.hist(confidences, bins=30, color='#3498db', alpha=0.7, edgecolor='black')
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
ax.hist(times, bins=30, color='#2ecc71', alpha=0.7, edgecolor='black')
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

Dataset: SROIE Full ({metrics['total_images']} images)
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
PaddleOCR PP-OCRv5
Mode: Raw OCR (no preprocessing)
Matching: Fuzzy text search
Processing: 3 batches combined
"""
ax2.text(0.1, 0.9, stats_text, transform=ax2.transAxes, fontsize=11,
         verticalalignment='top', fontfamily='monospace',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

# Bottom left: Confidence histogram
ax3 = fig.add_subplot(gs[1, 0])
ax3.hist(confidences, bins=20, color='#3498db', alpha=0.7, edgecolor='black')
ax3.axvline(metrics['avg_confidence'], color='red', linestyle='--', linewidth=2)
ax3.set_xlabel('Confidence', fontweight='bold')
ax3.set_ylabel('Count', fontweight='bold')
ax3.set_title('Confidence Distribution', fontweight='bold')
ax3.grid(axis='y', alpha=0.3)

# Bottom right: Time histogram
ax4 = fig.add_subplot(gs[1, 1])
ax4.hist(times, bins=20, color='#2ecc71', alpha=0.7, edgecolor='black')
ax4.axvline(metrics['avg_time'], color='red', linestyle='--', linewidth=2)
ax4.set_xlabel('Time (seconds)', fontweight='bold')
ax4.set_ylabel('Count', fontweight='bold')
ax4.set_title('Processing Time Distribution', fontweight='bold')
ax4.grid(axis='y', alpha=0.3)

fig.suptitle(f'PaddleOCR Performance on Full SROIE Dataset ({metrics["total_images"]} Images)', 
             fontsize=16, fontweight='bold')
plt.savefig(plots_dir / 'summary_dashboard.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"✅ Saved: {plots_dir / 'summary_dashboard.png'}")

print(f"\n✅ All visualizations saved to: {plots_dir}/")
print("=" * 80)
print("✅ BATCH COMBINATION COMPLETE!")
print("=" * 80)
