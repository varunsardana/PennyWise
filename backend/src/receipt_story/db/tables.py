import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Float, Boolean, ForeignKey, Text



class Base(DeclarativeBase):
    pass


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    merchant: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[str] = mapped_column(String, nullable=True)  # keep as ISO string for MVP simplicity
    total: Mapped[float] = mapped_column(Float, nullable=False)
    tax: Mapped[float] = mapped_column(Float, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=False)

    # Always store UTC ISO timestamp string
    created_at: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

class BudgetPlan(Base):
    """Stores user's budget plans with goals and constraints"""
    __tablename__ = 'budget_plans'
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, default="default_user")  # MVP: single user
    
    # Plan metadata
    name: Mapped[str] = mapped_column(String, nullable=True)  # "Summer Savings Plan"
    period: Mapped[str] = mapped_column(String)  # "weekly", "monthly", "quarterly", "yearly"
    start_date: Mapped[str] = mapped_column(String)  # ISO date
    end_date: Mapped[str] = mapped_column(String)  # ISO date
    
    # Budget targets (stored as JSON strings)
    total_budget: Mapped[float] = mapped_column(Float)
    category_budgets: Mapped[str] = mapped_column(Text)  # JSON: {"coffee": 100, "groceries": 400}
    
    # Preferences (what user won't cut vs willing to cut)
    protected_categories: Mapped[str] = mapped_column(Text)  # JSON: ["coffee", "gym"]
    flexible_categories: Mapped[str] = mapped_column(Text)  # JSON: ["gas", "dining"]
    
    # Goals
    savings_goal: Mapped[float] = mapped_column(Float, nullable=True)
    primary_goal: Mapped[str] = mapped_column(String, nullable=True)  # "Save for house"
    notes: Mapped[str] = mapped_column(Text, nullable=True)  # Agent's summary of conversation
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(
        String,
        default=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    updated_at: Mapped[str] = mapped_column(
        String,
        default=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    
    # Relationships
    adjustments = relationship("BudgetAdjustment", back_populates="budget_plan")


class BudgetAdjustment(Base):
    """Tracks modifications to budget plans"""
    __tablename__ = 'budget_adjustments'
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    budget_plan_id: Mapped[str] = mapped_column(String, ForeignKey('budget_plans.id'))
    
    # What triggered the adjustment
    trigger: Mapped[str] = mapped_column(String)  # "overspending", "unexpected_expense", "user_request"
    trigger_details: Mapped[str] = mapped_column(Text)  # JSON with details
    
    # The adjustment made
    previous_budgets: Mapped[str] = mapped_column(Text)  # JSON: old category budgets
    new_budgets: Mapped[str] = mapped_column(Text)  # JSON: new category budgets
    reasoning: Mapped[str] = mapped_column(Text)  # Agent's explanation
    
    created_at: Mapped[str] = mapped_column(
        String,
        default=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    
    # Relationships
    budget_plan = relationship("BudgetPlan", back_populates="adjustments")


class UserPreferences(Base):
    """Stores user's spending personality and financial goals"""
    __tablename__ = 'user_preferences'
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, default="default_user")
    
    # Spending personality (stored as JSON)
    wont_cut: Mapped[str] = mapped_column(Text, default="[]")  # JSON: ["coffee", "gym"]
    willing_to_cut: Mapped[str] = mapped_column(Text, default="[]")  # JSON: ["gas", "dining_out"]
    
    # Financial goals
    primary_goal: Mapped[str] = mapped_column(String, nullable=True)  # "save for house"
    secondary_goals: Mapped[str] = mapped_column(Text, nullable=True)  # JSON: ["build emergency fund"]
    timeline: Mapped[str] = mapped_column(String, nullable=True)  # "6 months", "1 year"
    
    # Additional context
    lifestyle_notes: Mapped[str] = mapped_column(Text, nullable=True)  # Free-form notes from conversations
    
    created_at: Mapped[str] = mapped_column(
        String,
        default=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    updated_at: Mapped[str] = mapped_column(
        String,
        default=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )


class SpendingAlert(Base):
    """Tracks budget alerts and warnings"""
    __tablename__ = 'spending_alerts'
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    budget_plan_id: Mapped[str] = mapped_column(String, ForeignKey('budget_plans.id'))
    
    # Alert details
    alert_type: Mapped[str] = mapped_column(String)  # "approaching_limit", "over_budget", "under_budget"
    category: Mapped[str] = mapped_column(String)  # Which category triggered it
    severity: Mapped[str] = mapped_column(String)  # "info", "warning", "critical"
    
    # Amounts
    budgeted_amount: Mapped[float] = mapped_column(Float)
    actual_amount: Mapped[float] = mapped_column(Float)
    difference: Mapped[float] = mapped_column(Float)
    
    # Message
    message: Mapped[str] = mapped_column(Text)  # Human-readable alert message
    
    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[str] = mapped_column(
        String,
        default=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )