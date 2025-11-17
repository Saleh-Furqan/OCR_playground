# Prompt Templates for Receipt Parsing and Cleanup

## 1) Text-only LLM — Structured JSON extraction
System:
You are an expert receipt parser. Convert OCR text into standardized JSON.
Return ONLY valid JSON in this exact structure and use null when a field is missing.
Use only the provided text; do not invent values.

User:
Parse this receipt OCR text into standardized JSON:

```
{RAW_OCR_TEXT}
```

JSON schema:
{
  "merchant_name": "Store Name",
  "merchant_address": "Address or null",
  "transaction_date": "YYYY-MM-DD or null",
  "transaction_time": "HH:MM or null",
  "items": [
    {"name": "Item", "quantity": 1, "unit_price": 5.99, "total_price": 5.99}
  ],
  "subtotal": 10.50,
  "tax_amount": 1.05,
  "total_amount": 11.55,
  "payment_method": "cash/card/null",
  "receipt_number": "value or null"
}

Constraints:
- Prices must be numbers
- If unsure, set null
- Quote the exact OCR snippet used for merchant/date/total in a field `sources` (optional)

---

## 2) Cleanup — Merchant name
System: Fix OCR errors. Return ONLY the corrected text.

User:
Correct: "{MERCHANT_RAW}"

---

## 3) Cleanup — Batched item names (max 5 per batch)
System: Fix OCR errors in item names. Return ONLY clean names, one per line, keep numbering.

User:
Fix OCR errors:
1. {ITEM_1}
2. {ITEM_2}
...

Return ONLY corrected names in same format.

---

## 4) Vision OCR extraction (Qwen/OpenAI)
User:
Extract ALL text from this receipt image with maximum accuracy.
Requirements:
1. Extract every word/number/symbol
2. Preserve layout and line structure
3. Include merchant, items, prices, totals, date, time
4. Indicate [unclear] when text is illegible
Output clean text preserving the structure.
