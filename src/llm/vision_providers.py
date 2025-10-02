#!/usr/bin/env python3
"""Vision-capable LLM providers for OCR tasks"""

import os
import requests
import json
import base64
from typing import Optional, Dict, Any
from PIL import Image
import io
from dotenv import load_dotenv

load_dotenv()


class VisionLLMProvider:
    """Base class for Vision LLM providers"""
    
    def extract_text_from_image(self, image_path: str, prompt: str = None) -> Dict[str, Any]:
        """Extract text from image using vision LLM"""
        raise NotImplementedError
    
    def is_available(self) -> bool:
        """Check if provider is available"""
        raise NotImplementedError


class QwenVisionProvider(VisionLLMProvider):
    """Qwen-VL/Qwen-OCR provider for advanced OCR tasks"""
    
    def __init__(self):
        self.api_key = os.getenv('QWEN_API_KEY') or os.getenv('DASHSCOPE_API_KEY')
        self.model = os.getenv('QWEN_MODEL', 'qwen-vl-ocr')
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        
    def _encode_image_base64(self, image_path: str) -> str:
        """Encode image to base64 string"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to encode image: {e}")
    
    def extract_text_from_image(self, image_path: str, prompt: str = None) -> Dict[str, Any]:
        """Extract text from image using Qwen-VL OCR"""
        
        if not self.api_key:
            return {"error": "QWEN_API_KEY not configured", "text": "", "confidence": 0.0}
        
        # Default OCR prompt optimized for receipts
        if not prompt:
            prompt = """
            Please extract ALL text from this receipt image with maximum accuracy. 
            
            Requirements:
            1. Extract every single word, number, and symbol visible in the image
            2. Preserve the exact layout and line structure
            3. Include merchant name, items, prices, totals, dates, times
            4. Maintain proper spacing and formatting
            5. If text is unclear, indicate with [unclear] but still attempt extraction
            
            Format the response as clean, readable text preserving the original structure.
            Focus on accuracy - this is for receipt processing.
            """
        
        try:
            # Encode image
            image_base64 = self._encode_image_base64(image_path)
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "model": self.model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "text": prompt
                                },
                                {
                                    "image": f"data:image/jpeg;base64,{image_base64}"
                                }
                            ]
                        }
                    ]
                },
                "parameters": {
                    "result_format": "message",
                    "max_tokens": 4096,
                    "temperature": 0.1
                }
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=60  # OCR can take longer
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if "output" in data and "choices" in data["output"]:
                    extracted_text = data["output"]["choices"][0]["message"]["content"].strip()
                    
                    # Calculate confidence based on response quality
                    confidence = self._calculate_confidence(extracted_text)
                    
                    return {
                        "text": extracted_text,
                        "confidence": confidence,
                        "model": self.model,
                        "method": "qwen_vision_ocr",
                        "metadata": {
                            "response": data,
                            "image_processed": True,
                            "text_length": len(extracted_text)
                        }
                    }
                else:
                    error_msg = data.get("message", "Unknown error")
                    return {"error": f"Qwen API error: {error_msg}", "text": "", "confidence": 0.0}
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}", "text": "", "confidence": 0.0}
                
        except Exception as e:
            return {"error": f"Qwen Vision OCR failed: {e}", "text": "", "confidence": 0.0}
    
    def _calculate_confidence(self, text: str) -> float:
        """Calculate confidence score for extracted text"""
        if not text or len(text.strip()) < 10:
            return 0.0
        
        score = 0.0
        
        # Length bonus (longer text usually means better extraction)
        length_score = min(len(text) / 200, 0.3)  # Up to 0.3 for 200+ chars
        score += length_score
        
        # Receipt-specific patterns
        import re
        
        # Price patterns
        price_patterns = len(re.findall(r'\$?\d+\.\d{2}', text))
        score += min(price_patterns * 0.1, 0.3)
        
        # Receipt keywords
        keywords = ['total', 'subtotal', 'tax', 'receipt', 'amount', 'item', 'date', 'time']
        keyword_count = sum(1 for kw in keywords if kw.lower() in text.lower())
        score += min(keyword_count * 0.05, 0.2)
        
        # Structure indicators (line breaks, proper formatting)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if len(lines) > 3:  # Multiple lines indicate good structure
            score += 0.2
        
        # Text quality (readable characters)
        readable_chars = len(re.findall(r'[a-zA-Z0-9\s$.,:/()-]', text))
        total_chars = len(text)
        if total_chars > 0:
            readability = readable_chars / total_chars
            score = score * readability  # Penalize unreadable text
        
        return min(max(score, 0.0), 1.0)
    
    def is_available(self) -> bool:
        """Check if Qwen provider is available"""
        return bool(self.api_key and self.api_key not in ['your-qwen-key-here', 'your-dashscope-key'])


class OpenAIVisionProvider(VisionLLMProvider):
    """OpenAI GPT-4V provider as fallback for OCR"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('OPENAI_VISION_MODEL', 'gpt-4o-mini')
        self.base_url = "https://api.openai.com/v1/chat/completions"
    
    def extract_text_from_image(self, image_path: str, prompt: str = None) -> Dict[str, Any]:
        """Extract text using OpenAI Vision API"""
        
        if not self.api_key:
            return {"error": "OPENAI_API_KEY not configured", "text": "", "confidence": 0.0}
        
        if not prompt:
            prompt = """
            Extract all visible text from this receipt image. Be extremely thorough and accurate.
            Include merchant name, all items, prices, totals, dates, and any other text.
            Preserve the original layout and structure. Output clean, readable text.
            """
        
        try:
            # Encode image
            image_base64 = self._encode_image_base64(image_path)
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 4096,
                "temperature": 0.1
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                extracted_text = data["choices"][0]["message"]["content"].strip()
                confidence = self._calculate_confidence(extracted_text)
                
                return {
                    "text": extracted_text,
                    "confidence": confidence,
                    "model": self.model,
                    "method": "openai_vision_ocr",
                    "metadata": {
                        "usage": data.get("usage", {}),
                        "text_length": len(extracted_text)
                    }
                }
            else:
                return {"error": f"OpenAI API error: {response.status_code}", "text": "", "confidence": 0.0}
                
        except Exception as e:
            return {"error": f"OpenAI Vision OCR failed: {e}", "text": "", "confidence": 0.0}
    
    def _encode_image_base64(self, image_path: str) -> str:
        """Encode image to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _calculate_confidence(self, text: str) -> float:
        """Calculate confidence score"""
        # Similar to QwenVisionProvider implementation
        if not text or len(text.strip()) < 10:
            return 0.0
        
        score = 0.0
        import re
        
        # Length and content quality
        score += min(len(text) / 200, 0.3)
        
        # Receipt patterns
        prices = len(re.findall(r'\$?\d+\.\d{2}', text))
        score += min(prices * 0.1, 0.3)
        
        keywords = ['total', 'subtotal', 'tax', 'receipt', 'amount']
        keyword_count = sum(1 for kw in keywords if kw.lower() in text.lower())
        score += min(keyword_count * 0.05, 0.2)
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if len(lines) > 3:
            score += 0.2
        
        return min(max(score, 0.0), 1.0)
    
    def is_available(self) -> bool:
        """Check if OpenAI provider is available"""
        return bool(self.api_key and self.api_key != 'your-openai-key-here')


def get_vision_llm_provider() -> Optional[VisionLLMProvider]:
    """Get the best available vision LLM provider for OCR"""
    
    # Use cloud APIs only (local providers removed)
    providers = [
        ('qwen_cloud', QwenVisionProvider),
        ('openai', OpenAIVisionProvider),
    ]
    
    for name, provider_class in providers:
        try:
            provider = provider_class()
            if provider.is_available():
                print(f"✅ Using cloud vision provider: {name}")
                return provider
            else:
                print(f"❌ {name} vision provider not available")
        except Exception as e:
            print(f"❌ {name} provider initialization failed: {e}")
    
    print("❌ No vision LLM providers available")
    return None