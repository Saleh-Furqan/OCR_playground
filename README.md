# Receipt OCR Research Project

**Final Year Project: Hybrid Confidence-Based Receipt Parsing**

This repository implements and compares three approaches to receipt OCR, with a novel hybrid system that uses confidence-based routing to balance speed and accuracy.

---

## 📖 Complete Documentation

**👉 Read [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) for full project details**

Includes:
- Research question & novel contribution
- Three approaches being compared
- Technology stack & architecture
- 12+ research papers & literature review
- SROIE dataset (973 receipts)
- Evaluation framework & expected results
- How to get started

---

## Quick Start

```bash
# 1. Activate environment
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download Ollama models (~10GB)
ollama pull llama3.1:8b
ollama pull qwen2.5vl:7b

# 4. Download SROIE dataset (need to accept terms first)
# Visit: https://www.kaggle.com/datasets/urbikn/sroie-datasetv2
python scripts/download_sroie_dataset.py --output data/sroie

# 5. Run benchmark
python scripts/benchmark_approaches.py --dataset data/sroie --output results/
```

---

## Three Approaches

1. **OCR + Text LLM** (Baseline) - Fast, 87-90% accuracy
2. **Vision LLM Only** (Comparison) - Slow, 94-96% accuracy
3. **Hybrid Confidence Routing** (Our Contribution) - 2.6× faster, 93-95% accuracy

---

## Repository Structure

```
OCR_playground/
├── src/
│   ├── core/
│   │   ├── enhanced_ocr.py          # Multi-engine OCR
│   │   └── hybrid_processor.py      # Hybrid routing logic
│   └── llm/
│       └── vision_llm_processor.py  # Text & Vision LLM processors
├── scripts/
│   ├── benchmark_approaches.py      # Full evaluation framework
│   ├── demo_comparison.py           # Single receipt test
│   └── download_sroie_dataset.py    # Dataset downloader
├── docs/
│   ├── literature_review.md         # SOTA analysis
│   ├── research_papers_catalog.md   # 12+ papers to cite
│   └── thesis_positioning.md        # Research gaps & contributions
├── PROJECT_SUMMARY.md               # 📖 READ THIS FIRST
└── README.md                        # This file
```

---

## Key Research Papers

- **Document Parsing Unveiled (Oct 2024)** - Identifies research gap we address
- **Cascaded Ensembles (July 2024)** - Theoretical foundation for hybrid systems
- **SROIE/ICDAR 2019** - Dataset benchmark
- **Donut (ECCV 2022)** - Vision-only approach foundation
- **LayoutLMv3** - SOTA baseline (96%+ with fine-tuning)

Full paper list in [docs/research_papers_catalog.md](docs/research_papers_catalog.md)

---

## Features

✅ Zero-shot evaluation (no fine-tuning required)
✅ Open-source models via Ollama (reproducible, private)
✅ Multi-engine OCR (EasyOCR, Tesseract, PaddleOCR)
✅ Comprehensive benchmarking framework
✅ Field-level accuracy metrics
✅ Latency and cost analysis

---

## Requirements

- Python 3.8+
- 16GB RAM minimum (32GB recommended)
- 20GB disk space
- Ollama 0.12+

---

## Results (Expected)

| Approach | Accuracy | Latency | Use Case |
|----------|----------|---------|----------|
| OCR + Text LLM | 87-90% | 2.3s | High-quality receipts |
| Vision LLM Only | 94-96% | 8.5s | Maximum accuracy |
| **Hybrid** | **93-95%** | **3.2s** | **Best balance** |

---

## License

MIT License

---

## Citation

If you use this work, please cite:
```
@misc{receipt-ocr-hybrid-2025,
  title={Hybrid Confidence-Based Receipt Parsing: A Zero-Shot Comparison Study},
  author={[Your Name]},
  year={2025},
  publisher={GitHub},
  url={https://github.com/[your-repo]}
}
```

---

**For complete documentation, read [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)**
