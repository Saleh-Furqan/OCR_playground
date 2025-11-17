#!/usr/bin/env python3
"""Vision LLM processor for direct image-to-JSON receipt parsing"""

import os
import json
import base64
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from PIL import Image
import io

load_dotenv()


class VisionLLMProcessor:
    """Process receipt images directly using vision-language models (Ollama)"""

    def __init__(self, model: str = "qwen2.5vl:7b"):
        """
        Initialize Vision LLM processor

        Args:
            model: Ollama vision model to use
                - "qwen2.5vl:7b" - Best for OCR tasks (Qwen 2.5 Vision) - DEFAULT
                - "qwen2-vl:7b" - Older version (Qwen 2 Vision)
                - "llama3.2-vision:11b" - Best general vision understanding
        """
        self.model = model
        self.base_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')

    def is_available(self) -> bool:
        """Check if Ollama and the vision model are available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return any(self.model in model["name"] for model in models)
            return False
        except Exception:
            return False

    def encode_image(self, image_path: str, max_size: int = 1536) -> str:
        """
        Encode image to base64 for Ollama API with optimal size for OCR

        Args:
            image_path: Path to image file
            max_size: Maximum dimension (width or height) - increased for OCR quality

        Returns:
            Base64 encoded image string
        """
        # Open image
        img = Image.open(image_path)

        # For OCR tasks, keep higher resolution (1536 instead of 1024)
        # Only resize if image is extremely large
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Encode to base64 with higher quality for OCR
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=95)  # Higher quality for OCR
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def structure_receipt_from_image(self, image_path: str) -> Dict[str, Any]:
        """
        Process receipt image directly to structured JSON

        Args:
            image_path: Path to receipt image

        Returns:
            Dictionary with structured receipt data and metadata
        """
        if not self.is_available():
            return {
                "error": f"Vision model {self.model} not available",
                "suggestion": f"Run: ollama pull {self.model}"
            }

        # IMPROVED prompt based on 2025 Qwen2-VL best practices research
        system_prompt = """You are a professional OCR system specialized in receipt data extraction. Your task is to extract text and structured information from this receipt image.

Extract all invoice details including merchant name, date, items with prices, and total amounts as structured JSON.

Return ONLY a valid JSON object in this exact format (no markdown, no explanations):
{
  "merchant_name": "Full merchant/store name exactly as shown",
  "merchant_address": "Complete address if visible",
  "transaction_date": "Date in YYYY-MM-DD format",
  "transaction_time": "Time in HH:MM format",
  "items": [
    {
      "name": "Exact item name",
      "quantity": 1,
      "unit_price": 5.99,
      "total_price": 5.99
    }
  ],
  "subtotal": 10.50,
  "tax_amount": 1.05,
  "total_amount": 11.55,
  "payment_method": "cash or card or other",
  "receipt_number": "receipt/invoice number if visible"
}

CRITICAL RULES:
1. Read ALL visible text carefully from the image
2. Extract the EXACT merchant name from the top of the receipt
3. Extract the EXACT total amount (usually labeled as "TOTAL" or "Total")
4. Extract the EXACT date in the format shown
5. All monetary values must be numbers (not strings): use 14.10 not "14.10"
6. Use null for any field that is not visible in the image
7. Do NOT make up or estimate any values
8. Return ONLY the JSON object, absolutely no other text

If the image is unclear or you cannot read the text, still return the JSON structure with null values for unreadable fields."""

        try:
            # Encode image
            image_b64 = self.encode_image(image_path)

            # Call Ollama vision API with streaming (more reliable for large responses)
            max_retries = 3
            last_error = None

            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        f"{self.base_url}/api/generate",
                        json={
                            "model": self.model,
                            "prompt": system_prompt + "\n\nNow analyze this receipt image and extract the data:",
                            "images": [image_b64],
                            "stream": False,
                            "format": "json",  # Request JSON format (Ollama 0.1.26+)
                            "options": {
                                "temperature": 0.0,  # Use 0 for deterministic output
                                "top_p": 0.9,  # Nucleus sampling
                                "top_k": 20,  # Reduce randomness
                                "num_predict": 3000,  # Increase for full JSON
                                "num_ctx": 8192,  # Larger context for vision models
                                "repeat_penalty": 1.1  # Avoid repetition
                            }
                        },
                        timeout=300,
                        headers={"Connection": "keep-alive"}
                    )

                    if response.status_code == 200:
                        break  # Success, exit retry loop
                    else:
                        last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                        if attempt < max_retries - 1:
                            print(f"  ⚠️  Vision LLM error (attempt {attempt+1}/{max_retries}), retrying...")
                            continue

                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout,
                        requests.exceptions.ChunkedEncodingError) as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        print(f"  ⚠️  Vision LLM connection failed (attempt {attempt+1}/{max_retries}), retrying...")
                        import time
                        time.sleep(2)  # Wait before retry
                        continue
                    else:
                        return {
                            "error": f"Vision LLM connection failed after {max_retries} attempts",
                            "details": str(last_error),
                            "merchant_name": None,
                            "transaction_date": None,
                            "total_amount": None
                        }

            # Check if we exited loop due to max retries
            if last_error and response.status_code != 200:
                return {
                    "error": f"Vision LLM failed after {max_retries} attempts",
                    "details": str(last_error),
                    "merchant_name": None,
                    "transaction_date": None,
                    "total_amount": None
                }

            if response.status_code == 200:
                data = response.json()
                content = data.get("response", "").strip()

                # Extract JSON from response
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:].strip()
                    content = content.strip().rstrip("```")

                try:
                    result = json.loads(content)
                    result["_metadata"] = {
                        "method": "vision_llm",
                        "model": self.model,
                        "success": True
                    }
                    return result
                except json.JSONDecodeError as e:
                    return {
                        "error": "Invalid JSON from vision model",
                        "raw_response": content[:500],
                        "json_error": str(e)
                    }
            else:
                return {
                    "error": f"Vision API error: {response.status_code}",
                    "details": response.text[:500]
                }

        except Exception as e:
            return {
                "error": f"Vision LLM processing failed: {str(e)}",
                "model": self.model
            }


class TextLLMProcessor:
    """Process OCR text using text-only LLM (faster, cheaper)"""

    def __init__(self, model: str = "llama3.1:8b"):
        """
        Initialize Text LLM processor

        Args:
            model: Ollama text model to use
        """
        self.model = model
        self.base_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')

    def is_available(self) -> bool:
        """Check if Ollama and the text model are available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return any(self.model in model["name"] for model in models)
            return False
        except Exception:
            return False

    def structure_receipt_from_text(self, ocr_text: str) -> Dict[str, Any]:
        """
        Convert OCR text to structured JSON

        Args:
            ocr_text: Raw text from OCR engine

        Returns:
            Dictionary with structured receipt data and metadata
        """
        if not self.is_available():
            return {
                "error": f"Text model {self.model} not available",
                "suggestion": f"Run: ollama pull {self.model}"
            }

        system_prompt = """You are an expert receipt parser. Convert OCR text into standardized JSON format.

Return ONLY valid JSON in this exact structure:
{
  "merchant_name": "Store Name",
  "merchant_address": "Address if found",
  "transaction_date": "YYYY-MM-DD or null",
  "transaction_time": "HH:MM or null",
  "items": [
    {
      "name": "Item Name",
      "quantity": 1,
      "unit_price": 5.99,
      "total_price": 5.99
    }
  ],
  "subtotal": 10.50,
  "tax_amount": 1.05,
  "total_amount": 11.55,
  "payment_method": "cash/card/null",
  "receipt_number": "number if found or null"
}

Rules:
- Use numbers for prices (not strings)
- Use null for missing data
- Clean up OCR errors in names
- Extract all visible items with prices
- Return ONLY the JSON, no explanations"""

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"{system_prompt}\n\nParse this receipt OCR text:\n\n{ocr_text}",
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 2048  # Full structured output needs more tokens
                    }
                },
                timeout=300  # Increased timeout for complex JSON generation (5 min)
            )

            if response.status_code == 200:
                data = response.json()
                content = data.get("response", "").strip()

                # Extract JSON from response
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:].strip()
                    content = content.strip().rstrip("```")

                try:
                    result = json.loads(content)
                    result["_metadata"] = {
                        "method": "ocr_text_llm",
                        "model": self.model,
                        "success": True
                    }
                    return result
                except json.JSONDecodeError as e:
                    return {
                        "error": "Invalid JSON from text model",
                        "raw_response": content[:500],
                        "json_error": str(e)
                    }
            else:
                return {
                    "error": f"Text API error: {response.status_code}",
                    "details": response.text[:500]
                }

        except Exception as e:
            return {
                "error": f"Text LLM processing failed: {str(e)}",
                "model": self.model
            }
