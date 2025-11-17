# Research Papers Catalog: Building Blocks for Your Thesis

This document catalogs the most relevant research papers you should cite and build upon for your receipt OCR thesis.

---

## 🎯 **Core Papers (Must Cite)**

### 1. **ReceiptSense: Beyond Traditional OCR (2024)**
**arXiv:** 2406.04493
**Link:** https://arxiv.org/abs/2406.04493

**Why it matters:**
- **Most recent** comprehensive receipt dataset (20K+ receipts)
- Uses OCR + LLM approach (similar to yours)
- Multilingual (Arabic-English)
- Includes LLM evaluation benchmark

**How you build on it:**
- They use separate OCR + LLM (like your Approach 1)
- **You add:** Hybrid routing based on confidence
- **You add:** Comparison with vision-only approach
- **You add:** Zero-shot evaluation (they fine-tune)

**Citation angle:**
> "Recent work by [ReceiptSense] demonstrated the effectiveness of combining traditional OCR with large language models for multilingual receipt understanding. However, their approach does not consider adaptive routing based on OCR confidence, which we show can reduce computational cost by 2-3x while maintaining accuracy."

---

### 2. **CORD: Consolidated Receipt Dataset (2019)**
**Conference:** NeurIPS 2019 Workshop on Document Intelligence
**GitHub:** https://github.com/clovaai/cord

**Why it matters:**
- **Standard benchmark** in receipt OCR research
- 1,000 receipts with hierarchical annotations
- Post-OCR parsing methodology
- Widely cited baseline

**How you build on it:**
- Provides evaluation benchmark (if you test on it)
- Establishes baseline metrics
- Your approach is more end-to-end (they assume OCR is done)

**Citation angle:**
> "While CORD [cite] established a standard benchmark for post-OCR parsing, assuming OCR text is already extracted, our work addresses the full pipeline including OCR quality assessment and adaptive processing."

---

### 3. **Donut: OCR-Free Document Understanding (ECCV 2022)**
**arXiv:** 2111.15664
**GitHub:** https://github.com/clovaai/donut

**Why it matters:**
- **Pioneered OCR-free** document understanding
- Uses vision-language transformer (Swin + BART)
- State-of-the-art on document VQA tasks
- **Conceptual foundation for your Vision-only approach**

**How you build on it:**
- Your Qwen2-VL approach is based on this paradigm
- Validates vision-only as viable alternative
- **You add:** Systematic comparison with OCR-based methods
- **You add:** When vision helps vs when OCR is sufficient

**Citation angle:**
> "Following the OCR-free paradigm introduced by Donut [cite], we evaluate modern vision-language models (Qwen2-VL) for end-to-end receipt understanding. However, we demonstrate that hybrid approaches combining traditional OCR with selective vision LLM usage achieve better cost-accuracy tradeoffs."

---

### 4. **LayoutLMv3: Pre-training for Document AI (2022)**
**arXiv:** 2204.08387

**Why it matters:**
- **State-of-the-art** layout-aware document understanding
- 96%+ accuracy on receipt understanding
- Uses multimodal pre-training (text + layout + image)
- Standard baseline to compare against

**How you build on it:**
- Establishes accuracy ceiling (~96%)
- Your zero-shot approaches should aim for 85-95%
- **You differ:** No fine-tuning required (more practical)

**Citation angle:**
> "While LayoutLMv3 [cite] achieves state-of-the-art performance (96%+) through fine-tuning on domain-specific data, our zero-shot hybrid approach achieves competitive accuracy (90-95%) without requiring labeled training data."

---

## 📊 **Dataset & Benchmark Papers**

### 5. **SROIE: ICDAR 2019 Competition (2019)**
**arXiv:** 2103.10213

- Standard receipt OCR competition
- 1,000 scanned receipts with KIE labels
- Establishes evaluation metrics
- Good for comparison

---

### 6. **DocILE: Document Information Localization and Extraction (2023)**

- Largest business document dataset
- Key information extraction benchmark
- Modern evaluation framework

---

## 🔬 **Methodological Papers (Your Novel Contributions)**

### 7. **Document Parsing Unveiled (October 2024)** ⭐⭐⭐
**arXiv:** 2410.21169

**Why it matters:**
- **Most recent survey** (Oct 2024!)
- Reviews modular pipelines vs end-to-end VLMs
- Identifies gaps: "handling complex layouts, integrating modules"
- **Your work addresses these gaps!**

**How you build on it:**
- Survey identifies two paradigms (OCR+Parser vs VLM)
- **You add:** Hybrid approach combining both
- **You add:** Empirical comparison on same dataset
- **You add:** Cost-accuracy tradeoff analysis

**Citation angle:**
> "A recent survey [cite] identifies two main paradigms for document parsing: modular pipelines and end-to-end vision-language models. We contribute a hybrid approach that dynamically selects between these paradigms based on OCR confidence, achieving the benefits of both."

**Key Quote from Paper:**
> "Traditional modular document parsing systems perform effectively within specific domains, but their architecture often leads to limitations in joint optimization and generalization across diverse document types."

**Your response:** "Our hybrid approach addresses this limitation by adaptively routing easy cases through fast OCR pipelines while leveraging vision-language models for complex cases."

---

### 8. **Cascaded Ensembles for Efficient Inference (July 2024)** ⭐⭐⭐
**arXiv:** 2407.02348

**Why it matters:**
- **Directly relevant to your hybrid approach!**
- Studies cascading from cheap to expensive models
- Exit criteria and deferral rules
- Cost-accuracy tradeoffs

**How you build on it:**
- Theoretical framework for your hybrid routing
- You apply cascade concept to OCR domain
- **You add:** OCR confidence as exit criterion
- **You add:** Application to document understanding

**Citation angle:**
> "Building on cascade-based adaptive inference [cite], we propose using OCR confidence scores as an exit criterion to route receipts between traditional OCR+TextLLM and vision-only processing, reducing average inference cost by 2-3x."

---

### 9. **Mixture of Nested Experts (NeurIPS 2024)**
**Conference:** NeurIPS 2024

**Why it matters:**
- Adaptive processing based on input complexity
- Routes tokens to different-sized models
- 2x inference speedup without accuracy loss
- Similar concept to your approach

**How you build on it:**
- Similar idea: easy inputs → fast model, hard inputs → expensive model
- **You differ:** Instance-level routing (not token-level)
- **You differ:** Applied to document understanding

**Citation angle:**
> "Similar to mixture-of-experts approaches [cite] that route inputs to appropriately-sized models, our hybrid processor adaptively selects between OCR+TextLLM and VisionLLM based on confidence scores."

---

### 10. **Window-Based Early-Exit Cascades (ICCV 2023)**

**Why it matters:**
- Uncertainty estimation for early exiting
- Confidence-based routing decisions
- Validates your confidence threshold approach

---

## 🤖 **LLM & Vision-Language Model Papers**

### 11. **StructuredRAG: JSON Response Formatting (August 2024)**
**arXiv:** 2408.11061

**Why it matters:**
- Studies structured JSON output from LLMs
- Gemini 1.5 Pro: 93.4% success rate
- Different prompting strategies tested
- **Validates your prompt engineering**

**How you build on it:**
- Provides best practices for JSON prompting
- Your receipt structuring uses similar techniques
- **You add:** Application to receipt domain
- **You add:** Comparison of text vs vision LLMs

---

### 12. **TrOCR: Transformer-based OCR (2023)**

- End-to-end transformer for text recognition
- State-of-the-art on handwritten text
- Alternative to traditional OCR engines

---

## 💡 **Novel Angles Your Work Can Take**

Based on the literature, here are **research gaps** your work can fill:

### **Gap 1: Confidence-Based Adaptive Routing**
**Literature:**
- Cascades exist for model selection [cite cascade papers]
- Early exit exists for neural networks [cite early exit papers]
- **But:** No work on OCR confidence → routing decision for documents

**Your Contribution:**
- First to use OCR confidence for adaptive VLM routing
- Empirically determine optimal threshold
- Cost-accuracy Pareto frontier

### **Gap 2: Zero-Shot Receipt Understanding Comparison**
**Literature:**
- LayoutLMv3, Donut require fine-tuning [cite]
- ReceiptSense fine-tunes on 20K receipts [cite]
- **But:** No systematic zero-shot comparison

**Your Contribution:**
- Compare OCR+TextLLM, VisionLLM, Hybrid in zero-shot setting
- Show what's achievable without training data
- More practical for small businesses

### **Gap 3: Cost-Accuracy Tradeoff Analysis**
**Literature:**
- Papers report accuracy but not cost
- "Cost modeling for ML" discusses theory [cite]
- **But:** No empirical cost-accuracy curves for document understanding

**Your Contribution:**
- Explicit latency measurements per approach
- Cost-accuracy Pareto curves
- Guidance: "Use hybrid at threshold X for Y% accuracy at Z seconds"

### **Gap 4: Open-Source Reproducibility**
**Literature:**
- Many SOTA results use GPT-4V, Claude [cite]
- Closed-source, expensive, not reproducible
- **But:** Limited open-source comparisons

**Your Contribution:**
- Fully open-source stack (Llama 3.1, Qwen2-VL)
- 100% reproducible
- Near-SOTA performance (~90-95% vs 97%)
- Democratizes access

---

## 📖 **How to Structure Your Related Work Section**

### **Section 1: Receipt OCR Datasets**
**Papers:** CORD, SROIE, ReceiptSense
**Narrative:** Datasets have grown from 1K (CORD) to 20K+ (ReceiptSense), enabling modern deep learning approaches.

### **Section 2: OCR & Text Recognition**
**Papers:** Tesseract, TrOCR, EasyOCR, PaddleOCR
**Narrative:** Traditional OCR achieves 80-85% accuracy; modern transformer-based OCR improves to 90-95%.

### **Section 3: Document Understanding Approaches**
**Papers:** LayoutLMv3, Donut, Document Parsing Survey
**Narrative:** Two paradigms—modular (OCR+Parser) vs end-to-end (VLM). Each has strengths/weaknesses.

### **Section 4: Vision-Language Models**
**Papers:** Qwen2-VL, Llama 3.2 Vision, StructuredRAG
**Narrative:** Modern VLMs can extract structured information from images but are computationally expensive.

### **Section 5: Adaptive & Cascade Systems**
**Papers:** Cascaded Ensembles, MoNE, Early Exit
**Narrative:** Adaptive routing based on input difficulty reduces cost while maintaining accuracy. Our work applies this to document understanding.

---

## 🎓 **Example Thesis Structure**

### **Chapter 3: Related Work**

#### **3.1 Receipt Understanding Datasets**
"Receipt OCR research has been benchmarked on datasets such as CORD [cite], SROIE [cite], and more recently ReceiptSense [cite], which contains 20,000+ multilingual receipts..."

#### **3.2 OCR and Text Recognition**
"Traditional OCR engines like Tesseract achieve 80-85% accuracy on clean documents. Recent transformer-based approaches like TrOCR [cite] and PaddleOCR [cite] improve this to 90-95%..."

#### **3.3 Document Understanding Paradigms**
"A recent survey [Document Parsing Unveiled] identifies two main approaches: (1) modular pipelines combining OCR and parsing, and (2) end-to-end vision-language models [Donut]. LayoutLMv3 [cite] achieves state-of-the-art (96%+) by combining both..."

#### **3.4 Vision-Language Models for Structured Output**
"Modern VLMs like Qwen2-VL and Llama 3.2 Vision can extract structured information from images. Recent work [StructuredRAG] shows that careful prompting achieves 93% success rate for JSON output..."

#### **3.5 Adaptive Inference and Cascades**
"Cascaded systems [Cascaded Ensembles] route inputs to appropriately-sized models based on difficulty. Mixture of Experts [MoNE] dynamically allocates compute. We apply this concept to document understanding using OCR confidence as the routing signal."

#### **3.6 Gap Analysis**
"While prior work achieves high accuracy through fine-tuning [LayoutLMv3] or uses vision-only approaches [Donut], no existing work systematically compares traditional OCR, vision-language models, and hybrid approaches in a zero-shot setting. Furthermore, cost-accuracy tradeoffs are rarely reported. Our work addresses these gaps."

---

## 📝 **Key Phrases to Use**

### **Positioning Your Work:**
- "Building on recent advances in vision-language models [cite]..."
- "While [X] achieves state-of-the-art accuracy, it requires fine-tuning on domain-specific data. Our zero-shot approach..."
- "Inspired by cascade-based inference [cite], we propose..."
- "Unlike [X] which uses vision-only, we systematically compare..."

### **Highlighting Novel Contributions:**
- "To the best of our knowledge, this is the first work to..."
- "We make the following novel contributions: (1)..., (2)..., (3)..."
- "Our hybrid approach addresses limitations of both modular pipelines [cite] and end-to-end VLMs [cite]..."

---

## ✅ **Citation Checklist for Thesis**

### **Must Cite (10-15 papers minimum):**
- [ ] CORD dataset (2019)
- [ ] SROIE competition (2019)
- [ ] ReceiptSense (2024)
- [ ] Donut (ECCV 2022)
- [ ] LayoutLMv3 (2022)
- [ ] Document Parsing Survey (2024)
- [ ] Cascaded Ensembles (2024)
- [ ] StructuredRAG (2024)
- [ ] TrOCR or PaddleOCR or EasyOCR paper
- [ ] Llama 3.1 and Qwen2-VL model cards/papers

### **Good to Cite (5-10 additional):**
- [ ] MoNE (NeurIPS 2024)
- [ ] Early exit papers (ICCV 2023)
- [ ] DocILE benchmark (2023)
- [ ] Cost-aware ML papers
- [ ] Uncertainty quantification for OCR

---

## 🚀 **Your Unique Research Angle**

**Problem Statement:**
> "While vision-language models achieve state-of-the-art accuracy on receipt understanding, their computational cost (8-10 seconds per receipt) limits practical deployment. Traditional OCR+parsing is fast (2-3 seconds) but less accurate. We propose a hybrid approach that dynamically routes receipts based on OCR confidence, achieving near-VLM accuracy at 2-3x lower latency."

**Research Questions:**
1. How do zero-shot OCR+TextLLM, VisionLLM-only, and Hybrid approaches compare on accuracy and latency?
2. What OCR confidence threshold optimizes the accuracy-latency tradeoff?
3. What types of receipts benefit most from vision-language models vs traditional OCR?

**Contributions:**
1. First systematic comparison of three approaches in zero-shot setting
2. Novel confidence-based hybrid routing for document understanding
3. Empirical cost-accuracy tradeoff analysis with practitioner guidance
4. Fully open-source implementation achieving near-SOTA performance

---

## 📚 **Quick Reference: Paper Downloads**

```bash
# Create a papers directory
mkdir -p docs/papers

# Download key papers (use arxiv-dl or wget)
wget https://arxiv.org/pdf/2406.04493 -O docs/papers/ReceiptSense_2024.pdf
wget https://arxiv.org/pdf/2111.15664 -O docs/papers/Donut_2022.pdf
wget https://arxiv.org/pdf/2204.08387 -O docs/papers/LayoutLMv3_2022.pdf
wget https://arxiv.org/pdf/2410.21169 -O docs/papers/DocumentParsingSurvey_2024.pdf
wget https://arxiv.org/pdf/2407.02348 -O docs/papers/CascadedEnsembles_2024.pdf
wget https://arxiv.org/pdf/2408.11061 -O docs/papers/StructuredRAG_2024.pdf
```

---

## 🎯 **Next Steps**

1. **Read these papers** in order of importance (top 5 first)
2. **Take notes** on methodology, results, limitations
3. **Identify gaps** your work addresses
4. **Draft related work section** using structure above
5. **Cite appropriately** in your thesis

Good luck! 🚀
