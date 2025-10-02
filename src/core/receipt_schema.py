from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from decimal import Decimal
import uuid


class ReceiptItem(BaseModel):
    name: str
    quantity: Optional[int] = 1
    unit_price: Optional[Decimal] = None
    total_price: Decimal


class ReceiptData(BaseModel):
    receipt_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    device_id: Optional[str] = None
    merchant_name: Optional[str] = None
    merchant_address: Optional[str] = None
    transaction_date: Optional[datetime] = None
    transaction_time: Optional[str] = None
    items: List[ReceiptItem] = Field(default_factory=list)
    subtotal: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    payment_method: Optional[str] = None
    processed_at: datetime = Field(default_factory=datetime.now)
    raw_text: str = ""


class StandardizedReceipt(BaseModel):
    receipt_id: str
    device_id: Optional[str] = None
    merchant: str
    date: datetime
    items: List[ReceiptItem]
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    confidence_score: float = Field(ge=0.0, le=1.0)
    processed_at: datetime
    
    @classmethod
    def from_receipt_data(cls, receipt_data: ReceiptData, confidence: float = 0.8):
        return cls(
            receipt_id=receipt_data.receipt_id,
            device_id=receipt_data.device_id,
            merchant=receipt_data.merchant_name or "Unknown",
            date=receipt_data.transaction_date or datetime.now(),
            items=receipt_data.items,
            subtotal=receipt_data.subtotal or Decimal("0.00"),
            tax=receipt_data.tax_amount or Decimal("0.00"),
            total=receipt_data.total_amount or Decimal("0.00"),
            confidence_score=confidence,
            processed_at=receipt_data.processed_at
        )