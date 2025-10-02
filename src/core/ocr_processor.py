import cv2
import pytesseract
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Tuple, Dict, Any
from PIL import Image
import numpy as np

from .receipt_schema import ReceiptData, ReceiptItem
from .enhanced_ocr import EnhancedOCRProcessor
from llm.llm_enhancer import LLMEnhancer


class OCRProcessor:
    def __init__(self):
        self.price_pattern = re.compile(r'\$?(\d+\.?\d*)')
        self.date_patterns = [
            re.compile(r'(\d{1,2})/(\d{1,2})/(\d{2,4})'),
            re.compile(r'(\d{1,2})-(\d{1,2})-(\d{2,4})'),
            re.compile(r'(\d{4})-(\d{1,2})-(\d{1,2})'),
        ]
        self.time_pattern = re.compile(r'(\d{1,2}):(\d{2})')
        
        # Initialize Enhanced OCR processor
        self.enhanced_ocr = EnhancedOCRProcessor()
        
        # Initialize LLM enhancer
        self.llm_enhancer = LLMEnhancer()
        self.llm_available = self.llm_enhancer.is_available()
    
    def preprocess_image(self, image_path: str) -> list:
        """Preprocess image multiple ways for better OCR results"""
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Create multiple preprocessed versions
        processed_images = []
        
        # Version 1: Basic scaling and denoising
        height, width = gray.shape
        if height < 1500:
            scale_factor = 1500 / height
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            scaled = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        else:
            scaled = gray.copy()
        
        # Apply bilateral filter to reduce noise while preserving edges
        filtered = cv2.bilateralFilter(scaled, 9, 75, 75)
        processed_images.append(('bilateral', filtered))
        
        # Version 2: Adaptive thresholding
        thresh_adaptive = cv2.adaptiveThreshold(
            filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10
        )
        processed_images.append(('adaptive_thresh', thresh_adaptive))
        
        # Version 3: OTSU thresholding
        _, thresh_otsu = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed_images.append(('otsu', thresh_otsu))
        
        # Version 4: Histogram equalization + thresholding
        equalized = cv2.equalizeHist(filtered)
        _, thresh_eq = cv2.threshold(equalized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed_images.append(('equalized', thresh_eq))
        
        # Version 5: Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        morph = cv2.morphologyEx(thresh_adaptive, cv2.MORPH_CLOSE, kernel)
        processed_images.append(('morphological', morph))
        
        return processed_images
    
    def extract_text(self, image_path: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text from receipt image using Enhanced Multi-Engine OCR"""
        
        try:
            # Use the enhanced OCR processor with multiple engines
            text, metadata = self.enhanced_ocr.extract_text_multi_engine(image_path)
            
            # If enhanced OCR fails or returns empty, fallback to legacy method
            if not text or len(text.strip()) < 20:
                print("🔄 Enhanced OCR returned poor results, falling back to legacy method...")
                legacy_text = self._legacy_extract_text(image_path)
                
                # Use the better result
                if len(legacy_text.strip()) > len(text.strip()):
                    text = legacy_text
                    metadata["fallback_used"] = True
                    metadata["method"] = "legacy_tesseract"
                else:
                    metadata["fallback_used"] = False
                    metadata["method"] = "enhanced_but_short"
            
            return text, metadata
            
        except Exception as e:
            print(f"⚠️ Enhanced OCR failed: {e}, using legacy method...")
            text = self._legacy_extract_text(image_path)
            metadata = {"fallback_used": True, "method": "legacy_tesseract", "error": str(e)}
            return text, metadata
    
    def _legacy_extract_text(self, image_path: str) -> str:
        """Legacy Tesseract-only extraction method (fallback)"""
        processed_images = self.preprocess_image(image_path)
        
        # Try multiple Tesseract configurations
        configs = [
            '--oem 3 --psm 6',
            '--oem 3 --psm 4', 
            '--oem 3 --psm 7',
            '--oem 3 --psm 8',
            '--oem 3 --psm 11',
            '--oem 3 --psm 12',
            '--oem 3 --psm 13'
        ]
        
        best_text = ""
        best_confidence = 0
        best_combo = ""
        
        # Try each preprocessing method with each configuration
        for img_name, processed_img in processed_images:
            for config in configs:
                try:
                    text = pytesseract.image_to_string(processed_img, config=config)
                    # Calculate confidence score based on receipt characteristics
                    confidence = self._calculate_text_confidence(text)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_text = text
                        best_combo = f"{img_name} + {config}"
                except Exception as e:
                    continue
        
        return best_text.strip() if best_text else ""
    
    def _calculate_text_confidence(self, text: str) -> float:
        """Calculate confidence score for extracted text"""
        if not text or len(text.strip()) < 10:
            return 0.0
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if len(lines) < 2:
            return 0.1
        
        score = 0.0
        
        # Check for price patterns (high importance for receipts)
        price_matches = len(re.findall(r'\$?\d+\.\d{2}', text))
        score += min(price_matches * 0.15, 0.5)
        
        # Check for decimal numbers (prices without $)
        decimal_matches = len(re.findall(r'\b\d+\.\d{2}\b', text))
        score += min(decimal_matches * 0.1, 0.3)
        
        # Check for date patterns
        if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text):
            score += 0.15
        
        # Check for time patterns
        if re.search(r'\d{1,2}:\d{2}', text):
            score += 0.1
        
        # Check for common receipt words
        receipt_words = ['total', 'subtotal', 'tax', 'amount', 'receipt', 'order', 'item', 'qty', 'quantity']
        word_matches = sum(1 for word in receipt_words if word.lower() in text.lower())
        score += min(word_matches * 0.05, 0.25)
        
        # Check for reasonable line structure
        avg_line_length = sum(len(line) for line in lines) / len(lines)
        if 10 < avg_line_length < 80:  # Reasonable line lengths
            score += 0.1
        
        # Penalize excessive garbled/special characters
        total_chars = len(text)
        readable_chars = len(re.findall(r'[a-zA-Z0-9\s$.,:/()-]', text))
        readable_ratio = readable_chars / total_chars if total_chars > 0 else 0
        score *= readable_ratio
        
        # Bonus for having multiple price-like patterns
        if price_matches + decimal_matches > 2:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def parse_receipt_text(self, text: str) -> ReceiptData:
        """Parse extracted text into structured receipt data"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        receipt = ReceiptData(raw_text=text)
        
        # Extract merchant info (usually in first few lines)
        if lines:
            receipt.merchant_name = self._extract_merchant_name(lines[:5])
            receipt.merchant_address = self._extract_address(lines[:10])
        
        # Extract date and time
        receipt.transaction_date, receipt.transaction_time = self._extract_datetime(text)
        
        # Extract items and prices
        receipt.items = self._extract_items(lines)
        
        # Extract totals
        receipt.subtotal = self._extract_amount(text, ['subtotal', 'sub-total', 'sub total'])
        receipt.tax_amount = self._extract_amount(text, ['tax', 'gst', 'hst', 'pst'])
        receipt.total_amount = self._extract_amount(text, ['total', 'amount', 'balance'])
        
        return receipt
    
    def _extract_merchant_name(self, lines: List[str]) -> Optional[str]:
        """Extract merchant name from first few lines"""
        for line in lines:
            if len(line) > 3 and not re.match(r'^\d', line):
                return line
        return None
    
    def _extract_address(self, lines: List[str]) -> Optional[str]:
        """Extract address from early lines"""
        address_lines = []
        for line in lines[1:6]:  # Skip first line (likely merchant name)
            if any(keyword in line.lower() for keyword in ['st', 'ave', 'rd', 'blvd', 'drive', 'street']):
                address_lines.append(line)
        return ' '.join(address_lines) if address_lines else None
    
    def _extract_datetime(self, text: str) -> Tuple[Optional[datetime], Optional[str]]:
        """Extract date and time from text"""
        date_obj = None
        time_str = None
        
        # Extract date
        for pattern in self.date_patterns:
            match = pattern.search(text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups[2]) == 2:  # 2-digit year
                        year = 2000 + int(groups[2])
                    else:
                        year = int(groups[2])
                    date_obj = datetime(year, int(groups[0]), int(groups[1]))
                    break
                except (ValueError, IndexError):
                    continue
        
        # Extract time
        time_match = self.time_pattern.search(text)
        if time_match:
            time_str = f"{time_match.group(1)}:{time_match.group(2)}"
        
        return date_obj, time_str
    
    def _extract_items(self, lines: List[str]) -> List[ReceiptItem]:
        """Extract items from receipt lines"""
        items = []
        
        # Enhanced patterns for better item extraction
        item_patterns = [
            r'(.+?)\s+(\$?\d+\.\d{2})',  # Item name followed by price
            r'(.+?)\s+(\d+\.\d{2})',     # Item name followed by price (no $)
            r'(.+?)\s+(\d+)\s+(\$?\d+\.\d{2})',  # Item name, quantity, price
        ]
        
        for line in lines:
            # Skip lines that look like headers, totals, or addresses
            lower_line = line.lower()
            if any(skip in lower_line for skip in ['total', 'subtotal', 'tax', 'address', 'phone', 'thank', 'receipt', 'change', 'sub-total']):
                continue
            
            # Try different patterns
            for pattern in item_patterns:
                match = re.search(pattern, line)
                if match:
                    groups = match.groups()
                    if len(groups) >= 2:
                        name = groups[0].strip()
                        price_str = groups[-1].replace('$', '').strip()
                        
                        # Clean up the name
                        name = re.sub(r'\s+', ' ', name).strip()
                        
                        # Validate the name is reasonable
                        if len(name) > 2 and not re.match(r'^\d+$', name):
                            try:
                                price = Decimal(price_str)
                                if price > 0:  # Only add items with positive prices
                                    quantity = int(groups[1]) if len(groups) == 3 else 1
                                    items.append(ReceiptItem(
                                        name=name, 
                                        quantity=quantity,
                                        total_price=price
                                    ))
                                    break  # Found a match, move to next line
                            except (InvalidOperation, ValueError):
                                continue
        
        return items
    
    def _extract_amount(self, text: str, keywords: List[str]) -> Optional[Decimal]:
        """Extract amount for given keywords"""
        for keyword in keywords:
            # Multiple patterns to catch different formats
            patterns = [
                rf'{keyword}.*?(\$?[\d,]+\.\d{{2}})',  # Standard price format
                rf'{keyword}.*?(\d+\.\d{{2}})',        # Just numbers
                rf'{keyword}\s*[:=]\s*\$?(\d+\.\d{{2}})',  # Colon/equals format
                rf'{keyword}\s+(\$?\d+\.\d{{2}})',     # Space separated
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace('$', '').replace(',', '')
                    try:
                        amount = Decimal(amount_str)
                        # Sanity check - reasonable receipt amounts
                        if 0 < amount < 10000:  # Between $0 and $10,000
                            return amount
                    except InvalidOperation:
                        continue
        
        # If no keyword match, try to find the largest reasonable amount (likely total)
        if 'total' in keywords:
            amounts = []
            for match in re.finditer(r'\$?(\d+\.\d{2})', text):
                try:
                    amount = Decimal(match.group(1))
                    if 1 < amount < 10000:  # Reasonable range
                        amounts.append(amount)
                except InvalidOperation:
                    continue
            if amounts:
                return max(amounts)  # Return largest amount as likely total
        
        return None
    
    def process_receipt(self, image_path: str) -> tuple:
        """Full pipeline to process a receipt image"""
        text, ocr_metadata = self.extract_text(image_path)
        receipt_data = self.parse_receipt_text(text)
        
        # Add OCR metadata to receipt
        receipt_data.raw_text = text
        
        # Enhance with LLM if available
        insights = {"ocr_metadata": ocr_metadata}
        if self.llm_available:
            try:
                enhanced_receipt, llm_insights = self.llm_enhancer.enhance_receipt_data(receipt_data)
                # Merge insights
                insights.update(llm_insights)
                return enhanced_receipt, insights
            except Exception as e:
                return receipt_data, insights
        else:
            return receipt_data, insights