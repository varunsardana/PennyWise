"""Helper functions for working with budget data"""

import json
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from pathlib import Path
import sys

# Add src to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from receipt_story.db.tables import (
    BudgetPlan, 
    BudgetAdjustment, 
    UserPreferences, 
    SpendingAlert,
    Receipt
)
from datetime import datetime, timezone
from collections import defaultdict


def get_active_budget_plan(db: Session, user_id: str = "default_user") -> Optional[BudgetPlan]:
    """Get the currently active budget plan for a user"""
    return db.query(BudgetPlan).filter(
        BudgetPlan.user_id == user_id,
        BudgetPlan.is_active == True
    ).first()


def get_user_preferences(db: Session, user_id: str = "default_user") -> Optional[UserPreferences]:
    """Get user preferences, create if doesn't exist"""
    prefs = db.query(UserPreferences).filter(
        UserPreferences.user_id == user_id
    ).first()
    
    if not prefs:
        prefs = UserPreferences(user_id=user_id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    
    return prefs


def analyze_spending_patterns(db: Session, start_date: str = None, end_date: str = None) -> Dict:
    """
    Analyze spending patterns from receipts.
    Returns category breakdowns, totals, and trends.
    """
    query = db.query(Receipt)
    
    if start_date:
        query = query.filter(Receipt.date >= start_date)
    if end_date:
        query = query.filter(Receipt.date <= end_date)
    
    receipts = query.all()
    
    # Calculate spending by category
    category_totals = defaultdict(float)
    merchant_counts = defaultdict(int)
    total_spend = 0.0
    
    for receipt in receipts:
        category_totals[receipt.category] += receipt.total
        merchant_counts[receipt.merchant] += 1
        total_spend += receipt.total
    
    # Calculate averages
    num_receipts = len(receipts)
    avg_transaction = total_spend / num_receipts if num_receipts > 0 else 0
    
    return {
        "total_spend": round(total_spend, 2),
        "num_transactions": num_receipts,
        "avg_transaction": round(avg_transaction, 2),
        "by_category": {k: round(v, 2) for k, v in category_totals.items()},
        "top_merchants": dict(sorted(merchant_counts.items(), key=lambda x: x[1], reverse=True)[:5]),
        "date_range": {
            "start": start_date,
            "end": end_date
        }
    }


def create_budget_plan(
    db: Session,
    period: str,
    start_date: str,
    end_date: str,
    category_budgets: Dict[str, float],
    protected_categories: List[str],
    flexible_categories: List[str],
    savings_goal: float = None,
    primary_goal: str = None,
    notes: str = None,
    user_id: str = "default_user"
) -> BudgetPlan:
    """Create a new budget plan"""
    
    # Deactivate any existing active plans
    existing_plans = db.query(BudgetPlan).filter(
        BudgetPlan.user_id == user_id,
        BudgetPlan.is_active == True
    ).all()
    
    for plan in existing_plans:
        plan.is_active = False
    
    # Calculate total budget
    total_budget = sum(category_budgets.values())
    
    # Create new plan
    new_plan = BudgetPlan(
        user_id=user_id,
        period=period,
        start_date=start_date,
        end_date=end_date,
        total_budget=total_budget,
        category_budgets=json.dumps(category_budgets),
        protected_categories=json.dumps(protected_categories),
        flexible_categories=json.dumps(flexible_categories),
        savings_goal=savings_goal,
        primary_goal=primary_goal,
        notes=notes,
        is_active=True
    )
    
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    
    return new_plan


def check_budget_status(db: Session, budget_plan: BudgetPlan) -> Dict:
    """
    Check current spending against budget plan.
    Returns status for each category and overall progress.
    """
    
    # Get spending since plan start date
    spending = analyze_spending_patterns(
        db, 
        start_date=budget_plan.start_date,
        end_date=None  # Current date
    )
    
    # Parse budget targets
    category_budgets = json.loads(budget_plan.category_budgets)
    
    # Compare actual vs budgeted
    status = {}
    for category, budgeted in category_budgets.items():
        actual = spending["by_category"].get(category, 0.0)
        remaining = budgeted - actual
        percent_used = (actual / budgeted * 100) if budgeted > 0 else 0
        
        # Determine status
        if percent_used >= 100:
            alert_level = "over_budget"
        elif percent_used >= 80:
            alert_level = "warning"
        elif percent_used >= 50:
            alert_level = "on_track"
        else:
            alert_level = "under_budget"
        
        status[category] = {
            "budgeted": budgeted,
            "actual": actual,
            "remaining": remaining,
            "percent_used": round(percent_used, 1),
            "alert_level": alert_level
        }
    
    # Overall status
    total_actual = spending["total_spend"]
    total_budgeted = budget_plan.total_budget
    
    return {
        "by_category": status,
        "overall": {
            "budgeted": total_budgeted,
            "actual": total_actual,
            "remaining": total_budgeted - total_actual,
            "percent_used": round((total_actual / total_budgeted * 100) if total_budgeted > 0 else 0, 1)
        },
        "period": budget_plan.period,
        "date_range": {
            "start": budget_plan.start_date,
            "end": budget_plan.end_date
        }
    }


def update_user_preferences(
    db: Session,
    wont_cut: List[str] = None,
    willing_to_cut: List[str] = None,
    primary_goal: str = None,
    timeline: str = None,
    lifestyle_notes: str = None,
    user_id: str = "default_user"
) -> UserPreferences:
    """Update user preferences"""
    
    prefs = get_user_preferences(db, user_id)
    
    if wont_cut is not None:
        prefs.wont_cut = json.dumps(wont_cut)
    if willing_to_cut is not None:
        prefs.willing_to_cut = json.dumps(willing_to_cut)
    if primary_goal is not None:
        prefs.primary_goal = primary_goal
    if timeline is not None:
        prefs.timeline = timeline
    if lifestyle_notes is not None:
        prefs.lifestyle_notes = lifestyle_notes
    
    prefs.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    
    db.commit()
    db.refresh(prefs)
    
    return prefs
