#!/usr/bin/env python3

import os
import requests
import json
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class LLMProvider:
    """Base class for LLM providers"""
    
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        raise NotImplementedError
    
    def is_available(self) -> bool:
        raise NotImplementedError


class GroqProvider(LLMProvider):
    """Groq API provider - Free tier: 14,400 requests/day"""
    
    def __init__(self):
        self.api_key = os.getenv('GROQ_API_KEY')
        self.model = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')
        self.base_url = "https://api.groq.com/openai/v1"
    
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        if not self.api_key or self.api_key == 'your-groq-key-here':
            return ""
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 100,
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content'].strip()
            else:
                print(f"Groq API error: {response.status_code} - {response.text}")
                return ""
                
        except Exception as e:
            print(f"Groq API exception: {e}")
            return ""
    
    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key != 'your-groq-key-here')


class HuggingFaceProvider(LLMProvider):
    """Hugging Face API provider - Free tier: 1000 requests/month"""
    
    def __init__(self):
        self.api_key = os.getenv('HUGGINGFACE_API_KEY')
        self.model = os.getenv('HUGGINGFACE_MODEL', 'microsoft/DialoGPT-medium')
        self.base_url = f"https://api-inference.huggingface.co/models/{self.model}"
    
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        if not self.api_key or self.api_key == 'your-hf-token-here':
            return ""
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Combine system and user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\nUser: {prompt}\nAssistant:"
        
        payload = {
            "inputs": full_prompt,
            "parameters": {
                "temperature": 0.1,
                "max_new_tokens": 500,
                "return_full_text": False
            }
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get('generated_text', '').strip()
                return ""
            else:
                print(f"HuggingFace API error: {response.status_code}")
                return ""
                
        except Exception as e:
            print(f"HuggingFace API exception: {e}")
            return ""
    
    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key != 'your-hf-token-here')


class GeminiProvider(LLMProvider):
    """Google Gemini API provider - Free tier: 15 requests/minute"""
    
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.model = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
    
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        if not self.api_key or self.api_key == 'your-google-key-here':
            return ""
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=1000
                )
            )
            
            return response.text.strip()
            
        except ImportError:
            print("Google Generative AI library not installed")
            return ""
        except Exception as e:
            print(f"Gemini API exception: {e}")
            return ""
    
    def is_available(self) -> bool:
        try:
            import google.generativeai
            return bool(self.api_key and self.api_key != 'your-google-key-here')
        except ImportError:
            return False


class OllamaProvider(LLMProvider):
    """Local Ollama provider - Free but requires local setup"""
    
    def __init__(self):
        self.url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'llama3.1:8b')
    
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "max_tokens": 1000}
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = requests.post(
                f"{self.url}/api/generate",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            return ""
            
        except Exception as e:
            return ""
    
    def is_available(self) -> bool:
        try:
            response = requests.get(f"{self.url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return any(model["name"].startswith(self.model) for model in models)
            return False
        except:
            return False


def get_llm_provider() -> Optional[LLMProvider]:
    """Get the configured LLM provider"""
    provider_name = os.getenv('LLM_PROVIDER', 'groq').lower()
    
    providers = {
        'groq': GroqProvider,
        'huggingface': HuggingFaceProvider,
        'gemini': GeminiProvider,
        'ollama': OllamaProvider
    }
    
    if provider_name in providers:
        provider = providers[provider_name]()
        if provider.is_available():
            return provider
        else:
            print(f"❌ {provider_name} provider not available")
    
    # Try fallback providers
    print("🔄 Trying fallback providers...")
    for name, provider_class in providers.items():
        if name != provider_name:
            provider = provider_class()
            if provider.is_available():
                print(f"✅ Using fallback provider: {name}")
                return provider
    
    print("❌ No LLM providers available")
    return None