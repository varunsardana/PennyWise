from pydantic import BaseModel
from typing import Dict, List, Optional


class ComparisonData(BaseModel):
    percent_change: float
    direction: str  # "up", "down", "same"
    message: str    # "15% more than last week"


class SpendingOverTimePoint(BaseModel):
    date: str       # "2026-01-06" or "Jan 2026"
    amount: float


class MerchantSpend(BaseModel):
    merchant: str
    amount: float
    count: int


class CategoryTrendPoint(BaseModel):
    date: str
    categories: Dict[str, float]


class DayOfWeekSpend(BaseModel):
    day: str        # "Mon", "Tue", etc.
    amount: float
    count: int


class TrendsResponse(BaseModel):
    period: str                              # "daily", "weekly", "monthly"
    period_start: str                        # "2026-01-06" (ISO date)
    period_end: str                          # "2026-01-10" (ISO date)
    spend_by_category: Dict[str, float]      # {"Groceries": 50.0, "Dining": 30.0}
    total_spend: float                       # 80.0
    receipt_count: int                       # 5
    comparison: Optional[ComparisonData]     # comparison to previous period


class ChartsDataResponse(BaseModel):
    spending_over_time: List[SpendingOverTimePoint]
    top_merchants: List[MerchantSpend]
    category_trends: List[CategoryTrendPoint]
    day_of_week: List[DayOfWeekSpend]
