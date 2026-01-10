from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class ReceiptItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None

class ReceiptExtraction(BaseModel):
    merchant: str = Field(..., description="Merchant/store name")
    date: Optional[str] = Field(None, description="ISO date preferred (YYYY-MM-DD). May be None if not found.")
    currency: str = "USD"
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    tip: Optional[float] = None
    total: float
    items: List[ReceiptItem] = Field(default_factory=list)
    raw_text: Optional[str] = Field(None, description="OCR raw text for debugging (optional)")

class ReceiptPreview(ReceiptExtraction):
    category: str = Field(..., description="Assigned category (Coffee, Groceries, etc.)")

class ScanReceiptResponse(BaseModel):
    receipt_id: str
    preview: ReceiptPreview


class SaveReceiptRequest(ReceiptPreview):
    pass

class SaveReceiptResponse(BaseModel):
    receipt_id: str
    saved: bool = True

class InsightsResponse(BaseModel):
    range: str
    receipt_count: int
    total_spend: float
    spend_by_category: Dict[str, float]
    top_merchants: List[str]
    story_insights: List[str]
    recommendation: str
