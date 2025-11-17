#!/usr/bin/env python3
"""
Test script to verify OCR and Vision LLM fixes
"""
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.enhanced_ocr import EnhancedOCRProcessor
from src.llm.vision_llm_processor import VisionLLMProcessor
import time

def test_paddleocr(image_path: str):
    """Test PaddleOCR extraction"""
    print("=" * 80)
    print("TEST 1: PaddleOCR Extraction")
    print("=" * 80)

    try:
        processor = EnhancedOCRProcessor()

        if 'paddle' not in processor.engines:
            print("❌ PaddleOCR not available!")
            return False

        print(f"✅ PaddleOCR initialized")
        print(f"📷 Processing: {Path(image_path).name}")

        start_time = time.time()

        # Get best OCR text
        text, metadata = processor.extract_text_multi_engine(image_path)

        elapsed = time.time() - start_time

        print(f"\n⏱️  Time: {elapsed:.2f}s")
        print(f"🔧 Best engine: {metadata['best_result']['engine']}")
        print(f"📊 Confidence: {metadata['best_result']['confidence']:.2f}")
        print(f"📝 Text length: {len(text)} characters")
        print(f"\n📄 Extracted Text (first 500 chars):\n{'-'*80}\n{text[:500]}\n{'-'*80}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_vision_llm(image_path: str):
    """Test Vision LLM extraction"""
    print("\n" + "=" * 80)
    print("TEST 2: Vision LLM (Qwen2.5-VL) Extraction")
    print("=" * 80)

    try:
        processor = VisionLLMProcessor(model="qwen2.5vl:7b")

        if not processor.is_available():
            print("❌ Vision LLM not available!")
            print(f"   Run: ollama pull qwen2.5vl:7b")
            return False

        print(f"✅ Vision LLM available: qwen2.5vl:7b")
        print(f"📷 Processing: {Path(image_path).name}")

        start_time = time.time()

        # Extract from image
        result = processor.structure_receipt_from_image(image_path)

        elapsed = time.time() - start_time

        print(f"\n⏱️  Time: {elapsed:.2f}s")

        if "error" in result:
            print(f"❌ Error: {result['error']}")
            if "raw_response" in result:
                print(f"📄 Raw response: {result['raw_response'][:300]}")
            return False

        print(f"✅ Successfully extracted data")
        print(f"\n📊 Extracted Fields:")
        print(f"   Merchant: {result.get('merchant_name', 'N/A')}")
        print(f"   Date: {result.get('transaction_date', 'N/A')}")
        print(f"   Time: {result.get('transaction_time', 'N/A')}")
        print(f"   Total: ${result.get('total_amount', 'N/A')}")
        print(f"   Items: {len(result.get('items', []))} items")

        print(f"\n📄 Full JSON:\n{'-'*80}")
        print(json.dumps(result, indent=2)[:1000])
        print(f"{'-'*80}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Test with a sample receipt
    test_image = "data/sroie/train/img/X51005255805.jpg"

    if not Path(test_image).exists():
        print(f"❌ Test image not found: {test_image}")
        print("   Please provide a valid receipt image path")
        sys.exit(1)

    print("\n🧪 TESTING FIXED OCR AND VISION LLM IMPLEMENTATIONS")
    print(f"📷 Test Image: {test_image}\n")

    # Test PaddleOCR
    ocr_pass = test_paddleocr(test_image)

    # Test Vision LLM
    vision_pass = test_vision_llm(test_image)

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"PaddleOCR Test: {'✅ PASS' if ocr_pass else '❌ FAIL'}")
    print(f"Vision LLM Test: {'✅ PASS' if vision_pass else '❌ FAIL'}")
    print("=" * 80)

    if ocr_pass and vision_pass:
        print("\n🎉 All tests passed! Ready for benchmarking.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
        sys.exit(1)
