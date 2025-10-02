#!/usr/bin/env python3

import json
import os
from typing import Dict, List, Optional, Tuple
from core.receipt_schema import ReceiptData, ReceiptItem, StandardizedReceipt
from decimal import Decimal
import re
from dotenv import load_dotenv
from .llm_providers import get_llm_provider

# Load environment variables
load_dotenv()


class LLMEnhancer:
    def __init__(self):
        self.llm_provider = get_llm_provider()
        
    def _call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """Make a request to the configured LLM provider"""
        if not self.llm_provider:
            return ""
        
        try:
            return self.llm_provider.generate(prompt, system_prompt)
        except Exception as e:
            print(f"LLM API error: {e}")
            return ""
    
    def enhance_merchant_name(self, raw_merchant: str) -> str:
        """Clean up and standardize merchant name"""
        if not raw_merchant or len(raw_merchant.strip()) < 2:
            return "Unknown Merchant"
        
        system_prompt = "Fix OCR errors. Return ONLY the corrected text, no explanations."
        
        prompt = f'Correct: "{raw_merchant}"'
        
        enhanced = self._call_llm(prompt, system_prompt)
        return enhanced if enhanced else raw_merchant
    
    def enhance_item_names(self, items: List[ReceiptItem]) -> List[ReceiptItem]:
        """Clean up and enhance item names"""
        if not items:
            return items
        
        system_prompt = "Fix OCR errors in item names. Return ONLY clean names, no explanations or notes."
        
        # Process items in batches to avoid token limits
        enhanced_items = []
        batch_size = 5
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i+batch_size]
            
            # Create prompt with batch of items
            item_list = "\n".join([f"{j+1}. {item.name}" for j, item in enumerate(batch)])
            
            prompt = f"""Fix OCR errors:
            {item_list}
            
            Return ONLY corrected names in same format:"""
            
            enhanced_text = self._call_llm(prompt, system_prompt)
            
            if enhanced_text:
                # Parse the enhanced names back
                lines = enhanced_text.strip().split('\n')
                for j, line in enumerate(lines):
                    if j < len(batch):
                        # Extract the enhanced name (remove number prefix)
                        enhanced_name = re.sub(r'^\d+\.\s*', '', line.strip())
                        if enhanced_name:
                            # Create new item with enhanced name
                            original_item = batch[j]
                            enhanced_item = ReceiptItem(
                                name=enhanced_name,
                                quantity=original_item.quantity,
                                unit_price=original_item.unit_price,
                                total_price=original_item.total_price
                            )
                            enhanced_items.append(enhanced_item)
                        else:
                            enhanced_items.append(batch[j])  # Keep original if parsing failed
                    else:
                        break
            else:
                # If LLM call failed, keep originals
                enhanced_items.extend(batch)
        
        return enhanced_items
    
    
    def generate_digital_receipt_html(self, receipt: ReceiptData) -> str:
        """Generate a properly formatted digital receipt HTML using LLM"""
        system_prompt = """You are a digital receipt formatter. Fill in the provided template with the given data.
        Return ONLY the filled HTML template with no changes to structure or styling, no explanations."""
        
        # Prepare receipt data for LLM
        items_text = ""
        for item in receipt.items:
            price = f"${item.total_price:.2f}"
            qty = f" x{item.quantity}" if item.quantity and item.quantity > 1 else ""
            items_text += f"{item.name}{qty} - {price}\n"
        
        template = """
<div class="ai-digital-receipt" style="font-family: 'Courier New', monospace; background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: 0 auto; text-align: center; line-height: 1.4;">
    <h1 style="font-size: 18px; font-weight: bold; margin: 0 0 10px 0; text-transform: uppercase; letter-spacing: 1px;">[MERCHANT_NAME]</h1>
    <div style="font-size: 12px; color: #666; margin-bottom: 15px;">[ADDRESS]</div>
    <div style="border-top: 1px dashed #999; margin: 15px 0; font-size: 10px; color: #999;">────────────────────────────────────────</div>
    
    <div style="text-align: left; font-size: 11px; margin-bottom: 10px;">
        <div>Date: [DATE]    Time: [TIME]</div>
        <div>Receipt: [RECEIPT_ID]</div>
    </div>
    
    <div style="border-top: 1px dashed #999; margin: 15px 0; font-size: 10px; color: #999;">────────────────────────────────────────</div>
    
    <div style="text-align: left; font-size: 11px;">
        [ITEMS_LIST]
    </div>
    
    <div style="border-top: 1px dashed #999; margin: 15px 0; font-size: 10px; color: #999;">────────────────────────────────────────</div>
    
    <div style="text-align: left; font-size: 11px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 3px;">
            <span>Subtotal:</span>
            <span>[SUBTOTAL]</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <span>Tax:</span>
            <span>[TAX]</span>
        </div>
        <div style="border-top: 2px solid #333; padding-top: 5px;">
            <div style="display: flex; justify-content: space-between; font-weight: bold; font-size: 13px;">
                <span>TOTAL:</span>
                <span>[TOTAL]</span>
            </div>
        </div>
    </div>
    
    <div style="border-top: 1px dashed #999; margin: 15px 0; font-size: 10px; color: #999;">────────────────────────────────────────</div>
    
    <div style="font-size: 10px; color: #666; text-align: center;">
        <div>Thank you for your business!</div>
        <div style="margin-top: 5px;">Digitized Receipt</div>
    </div>
</div>
        """
        
        # Format items for the template
        formatted_items = ""
        for item in receipt.items:
            price = f"${item.total_price:.2f}"
            qty_text = f" x{item.quantity}" if item.quantity and item.quantity > 1 else ""
            formatted_items += f'        <div style="display: flex; justify-content: space-between; margin-bottom: 3px;"><span>{item.name}{qty_text}</span><span>{price}</span></div>\n'
        
        prompt = f"""Fill in this exact template with the provided data. Replace only the bracketed placeholders:

{template}

Data to use:
[MERCHANT_NAME] = {receipt.merchant_name or 'UNKNOWN MERCHANT'}
[ADDRESS] = {receipt.merchant_address or ''}
[DATE] = {receipt.transaction_date.strftime('%m/%d/%Y') if receipt.transaction_date else 'N/A'}
[TIME] = {receipt.transaction_time or 'N/A'}
[RECEIPT_ID] = {receipt.receipt_id[:8] if receipt.receipt_id else 'N/A'}
[ITEMS_LIST] = 
{formatted_items}
[SUBTOTAL] = ${receipt.subtotal:.2f if receipt.subtotal else 0:.2f}
[TAX] = ${receipt.tax_amount:.2f if receipt.tax_amount else 0:.2f}
[TOTAL] = ${receipt.total_amount:.2f if receipt.total_amount else 0:.2f}

Return ONLY the filled template with no modifications to the HTML structure or styling."""

        html_content = self._call_llm(prompt, system_prompt)
        return html_content if html_content else self._generate_fallback_receipt_html(receipt)
    
    def _generate_fallback_receipt_html(self, receipt: ReceiptData) -> str:
        """Fallback receipt HTML if LLM is not available"""
        items_html = ""
        for item in receipt.items:
            qty_text = f" x{item.quantity}" if item.quantity and item.quantity > 1 else ""
            items_html += f"""
            <div class="receipt-item">
                <span>{item.name}{qty_text}</span>
                <span>${item.total_price:.2f}</span>
            </div>"""
        
        return f"""
        <div class="digital-receipt">
            <div class="receipt-header">
                <h2>{receipt.merchant_name or 'Unknown Merchant'}</h2>
                <div class="receipt-date">
                    {receipt.transaction_date.strftime('%m/%d/%Y') if receipt.transaction_date else 'N/A'}
                    {receipt.transaction_time or ''}
                </div>
            </div>
            <div class="receipt-separator">{'.' * 40}</div>
            <div class="receipt-items">{items_html}</div>
            <div class="receipt-separator">{'.' * 40}</div>
            <div class="receipt-totals">
                <div class="receipt-item">
                    <span>Subtotal:</span>
                    <span>${receipt.subtotal:.2f if receipt.subtotal else 0:.2f}</span>
                </div>
                <div class="receipt-item">
                    <span>Tax:</span>
                    <span>${receipt.tax_amount:.2f if receipt.tax_amount else 0:.2f}</span>
                </div>
                <div class="receipt-item total">
                    <span><strong>Total:</strong></span>
                    <span><strong>${receipt.total_amount:.2f if receipt.total_amount else 0:.2f}</strong></span>
                </div>
            </div>
        </div>"""

    def enhance_receipt_data(self, receipt: ReceiptData) -> Tuple[ReceiptData, Dict[str, str]]:
        """Main method to enhance all receipt data"""
        print("🤖 Enhancing receipt data with LLM...")
        
        # Enhance merchant name
        if receipt.merchant_name:
            enhanced_merchant = self.enhance_merchant_name(receipt.merchant_name)
            receipt.merchant_name = enhanced_merchant
            print(f"✅ Merchant enhanced: {enhanced_merchant}")
        
        # Enhance item names
        if receipt.items:
            enhanced_items = self.enhance_item_names(receipt.items)
            receipt.items = enhanced_items
            print(f"✅ Enhanced {len(enhanced_items)} items")
        
        # Generate digital receipt HTML
        digital_receipt_html = self.generate_digital_receipt_html(receipt)
        
        insights = {
            'digital_receipt_html': digital_receipt_html,
            'category': 'General',
            'store_type': 'Store'
        }
        
        print("✅ Digital receipt HTML generated")
        
        return receipt, insights
    
    def is_available(self) -> bool:
        """Check if any LLM provider is available"""
        return self.llm_provider is not None