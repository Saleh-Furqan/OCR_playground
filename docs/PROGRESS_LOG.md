# Project Progress Log & Design Decisions

**Project**: Hybrid Receipt OCR System Comparison
**Goal**: Compare OCR+TextLLM, VisionLLM, and Hybrid approaches for receipt information extraction

---

## Timeline & Major Milestones

### Phase 1: Initial Setup & Model Selection (Session 1-2)
- **Decision**: Use Ollama for local LLM inference instead of cloud APIs
  - *Rationale*: Free, private, reproducible results
- **Decision**: Selected llama3.1:8b for text processing
  - *Rationale*: Good instruction following, 8B size balances performance/speed
- **Decision**: Selected qwen2.5vl:7b for vision processing
  - *Initial mistake*: Tried `qwen2-vl:7b` (doesn't exist)
  - *Correction*: Found correct model name `qwen2.5vl:7b` via Ollama docs
  - *Rationale*: Strong OCR capabilities, multilingual support

### Phase 2: Dataset Selection (Session 2)
- **Decision**: Use SROIE 2019 dataset over CORD
  - *Rationale*:
    - Simpler structure (4 fields: company, date, address, total)
    - Well-established benchmark from ICDAR competition
    - 626 training + 347 test images = 973 total samples
    - English receipts (matches our LLM strengths)
  - *Alternative considered*: CORD dataset (too complex with 30+ fields)

### Phase 3: Approach Design Philosophy

#### Three Approaches Comparison
1. **Approach 1: OCR + Text LLM (Baseline)**
   - Enhanced Tesseract OCR with preprocessing
   - Extract text → Feed to llama3.1:8b for structured extraction
   - *Purpose*: Represents traditional pipeline approach

2. **Approach 2: Vision LLM Only (Comparison)**
   - Direct image → qwen2.5vl:7b → structured output
   - No OCR preprocessing
   - *Purpose*: Test modern end-to-end vision-language models

3. **Approach 3: Hybrid Confidence-Based Routing (Novel Contribution)**
   - **Initial Design** (Session 3):
     - Run OCR first, calculate confidence score
     - If confidence > threshold (0.7): Use OCR + Text LLM path
     - If confidence < threshold: Fall back to Vision LLM
     - *Rationale*: OCR is faster, use it when reliable; vision is more robust for poor quality

   - **Key Innovation**: Confidence-based routing without training
     - Uses OCR confidence metrics (character-level certainty)
     - Zero-shot approach - no labeled data needed
     - Practical for real-world deployment

### Phase 4: Benchmark Design (Current Session)

#### Important Realization: Zero-Shot vs Training-Based
- **Initial assumption**: We might need to train/fine-tune models
- **Pivot decision** (Session 3):
  - Use ALL pre-trained models in zero-shot mode
  - *Rationale*:
    - Faster to implement
    - More practical (no labeled data needed in deployment)
    - Fair comparison across approaches
    - Still allows for novel contribution via routing strategy

- **Future enhancement identified**: Add threshold optimization
  - Use validation set to find optimal confidence threshold
  - Currently hardcoded at 0.7
  - Would provide training-like curves and optimization plots for thesis

#### Benchmark Metrics Decided
1. **Accuracy Metrics**:
   - Field-level accuracy (merchant_name, date, total_amount)
   - Overall accuracy
   - Fuzzy matching for merchant names (handles minor OCR errors)
   - Exact matching for dates/amounts

2. **Performance Metrics**:
   - Mean/median/std latency per approach
   - Per-sample timing breakdown

3. **Visualization Requirements** (Added this session):
   - Field accuracy comparison (grouped bar chart)
   - Latency comparison (bar chart)
   - Accuracy vs Latency trade-off (scatter plot)
   - Per-sample accuracy heatmap (shows consistency)
   - Accuracy distribution (box plot - shows variance)
   - Comprehensive dashboard (multi-panel summary)

   *Rationale*: Need publication-quality figures for thesis report

### Phase 5: Implementation Challenges & Solutions

#### Challenge 1: Import Path Issues
- **Problem**: `ModuleNotFoundError: No module named 'llm'`
- **Solution**: Fixed relative imports in `hybrid_processor.py`
  - Changed: `from llm.vision_llm_processor import ...`
  - To: `from src.llm.vision_llm_processor import ...`

#### Challenge 2: Dataset Format Mismatch
- **Problem**: Benchmark expected `.json` files, SROIE provides `.txt` files
- **Problem**: Benchmark looked in wrong directory structure
- **Solution**:
  - Updated benchmark to handle SROIE structure (`train/img/` and `train/entities/`)
  - Added ground truth format conversion (SROIE → standardized format)
  - Mapping: `company → merchant_name`, `total → total_amount`

#### Challenge 3: Progress Visibility
- **User feedback**: "Include print statements so you can see how it runs"
- **Solution**: Added comprehensive progress output:
  - Show ground truth for each receipt
  - Show extracted results from each approach
  - Show timing per approach
  - Show overall progress [X/626]
  - *Rationale*: Long-running process (626 receipts × 3 approaches × LLM inference)

#### Challenge 4: Visualization Requirements
- **User requirement**: "Loads of metrics and benchmark plots and figures for the report"
- **Solution**: Implemented 6 comprehensive visualizations (see Phase 4)
- **Technical details**:
  - Used matplotlib with non-interactive backend (Agg)
  - High DPI (300) for publication quality
  - Color scheme: Blue (OCR+Text), Red (Vision), Green (Hybrid - ours)

---

## Key Technical Decisions Summary

| Decision | Options Considered | Choice Made | Rationale |
|----------|-------------------|-------------|-----------|
| LLM Backend | OpenAI API, Anthropic, Groq, Ollama | Ollama | Free, local, reproducible |
| Text LLM | llama3.1:8b, llama3.1:70b, mistral | llama3.1:8b | Best balance of performance/speed |
| Vision LLM | qwen2.5vl, llava, moondream | qwen2.5vl:7b | Strong OCR, good docs |
| Dataset | CORD, SROIE, Custom | SROIE 2019 | Simple, established benchmark |
| Approach | Fine-tuning, Few-shot, Zero-shot | Zero-shot | Practical, fast, fair comparison |
| Hybrid Strategy | Model ensembling, Confidence routing, Voting | Confidence routing | Fast, no training needed |
| Confidence Threshold | Dynamic, Learned, Fixed | Fixed (0.7) with future optimization | Simple baseline, can improve |

---

## Hypothesis Evolution

### Initial Hypothesis (Session 1)
- Vision LLMs might be significantly better than OCR for poor quality receipts
- OCR might be faster but less accurate

### Refined Hypothesis (Session 3)
- **OCR + Text LLM**: Fast, accurate for high-quality images, struggles with noise/blur
- **Vision LLM Only**: Slower (larger model), more robust to image quality issues
- **Hybrid**: Should achieve:
  - Speed close to OCR+Text (since most receipts are good quality)
  - Accuracy better than OCR+Text (fallback handles edge cases)
  - More efficient than Vision-only (doesn't always use heavy model)

### Expected Results
- **Accuracy**: Hybrid ≥ Vision-only > OCR+Text
- **Latency**: OCR+Text < Hybrid < Vision-only
- **Trade-off**: Hybrid offers best accuracy/latency balance

---

## Future Work & Extensions (Ideas Generated)

1. **Threshold Optimization**
   - Use validation set to find optimal confidence threshold
   - Generate optimization curves for thesis
   - Currently: hardcoded 0.7

2. **Adaptive Routing**
   - Train small neural network to predict best route
   - Features: blur score, contrast, noise level, text density
   - Would add "learned" component to thesis

3. **Multi-Modal Fusion**
   - Instead of routing, combine outputs from both paths
   - Weighted averaging based on confidence
   - More complex but potentially more robust

4. **Additional Datasets**
   - Test on CORD (complex receipts)
   - Test on receipts-in-the-wild (various languages, formats)
   - Demonstrate generalization

5. **Production Optimization**
   - Batch processing for throughput
   - Model quantization for faster inference
   - Caching for repeated processing

6. **Error Analysis**
   - Which types of receipts fail with each approach?
   - Analyze failure modes
   - Guide future improvements

---

## Open Questions & TODOs

- [ ] What is optimal confidence threshold? (Need to run threshold sweep)
- [ ] How does hybrid performance scale with different quality receipts?
- [ ] Can we predict routing decision before OCR? (Pre-processing analysis)
- [ ] Should we use test set or validation split from training data?
- [ ] Do we need statistical significance tests? (t-tests, confidence intervals)
- [ ] Should we report F1 scores in addition to accuracy?

---

## Lessons Learned

1. **Model naming matters**: Spent time debugging incorrect model name (hyphens vs no hyphens)
2. **Dataset format compatibility**: Always check ground truth format first
3. **Progress visibility critical**: Long-running experiments need detailed logging
4. **Visualization planning**: Think about thesis figures early, not as afterthought
5. **Zero-shot is powerful**: Don't overcomplicate with training if not needed
6. **Document everything**: This log is crucial for thesis methodology section!

---

## Thesis Structure Planning

### Methodology Section (Will include):
- Three-approach comparison framework
- Zero-shot evaluation rationale
- SROIE dataset choice justification
- Confidence-based routing algorithm
- Evaluation metrics design

### Results Section (Will include):
- All 6 visualization plots
- Statistical significance tests
- Per-field accuracy breakdown
- Latency analysis
- Trade-off discussion

### Discussion Section (Will include):
- Why hybrid works (or doesn't)
- Comparison with related work
- Limitations of zero-shot approach
- Future work: threshold optimization

---

*Last Updated: 2025-11-13 (Benchmark running session)*
*Next Steps: Complete benchmark run on 626 receipts, analyze results, generate plots*
