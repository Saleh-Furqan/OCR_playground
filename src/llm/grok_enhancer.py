#!/usr/bin/env python3
"""Grok integration for receipt structuring and standardization"""

import json
import os
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class GrokEnhancer:
    def __init__(self):
        self.api_key = os.getenv('GROQ_API_KEY') or os.getenv('GROK_API_KEY')
        # Using Groq instead (faster inference)
        self.model = os.getenv('GROQ_MODEL', 'mixtral-8x7b-32768')
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
    
    def is_available(self) -> bool:
        """Check if Groq API is configured and available"""
        return bool(self.api_key)
    
    def structure_receipt(self, ocr_text: str) -> Dict[str, Any]:
        """Convert OCR text into standardized receipt JSON"""
        if not self.is_available():
            return {"error": "Grok API not configured"}
        
        system_prompt = """You are an expert receipt parser. Convert OCR text into a standardized JSON receipt format.
        
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

        prompt = f"Parse this receipt OCR text into standardized JSON:\n\n{ocr_text}"
        
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2048
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                
                # Extract JSON from response
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:].strip()
                
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return {"error": "Invalid JSON from Grok", "raw_response": content}
            else:
                error_detail = ""
                try:
                    error_data = response.json()
                    error_detail = error_data.get("error", {}).get("message", "")
                except:
                    error_detail = response.text
                return {"error": f"Grok API error: {response.status_code} - {error_detail}"}
                
        except Exception as e:
            return {"error": f"Grok API failed: {e}"}