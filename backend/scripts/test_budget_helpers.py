"""
Test script to verify helpers work correctly.
"""
from helpers import analyze_spending_patterns, update_user_preferences, create_budget_plan, check_budget_status, get_user_preferences

def test_budget_helpers():
    """Test the budget helper functions"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from pathlib import Path
    
    # Setup database connection
    base_dir = Path(__file__).parent.parent
    db_path = base_dir / "data" / "receipts.db"
    db_url = f"sqlite:///{db_path.absolute()}"
    
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Test 1: Analyze spending patterns
        print("\n=== Test 1: Analyze Spending ===")
        patterns = analyze_spending_patterns(db)
        print(f"Total spend: ${patterns['total_spend']}")
        print(f"By category: {patterns['by_category']}")
        
        # Test 2: Get/create user preferences
        print("\n=== Test 2: User Preferences ===")
        prefs = get_user_preferences(db)
        print(f"User preferences: {prefs.id}")
        
        # Test 3: Update preferences
        print("\n=== Test 3: Update Preferences ===")
        update_user_preferences(
            db,
            wont_cut=["coffee", "gym"],
            willing_to_cut=["dining_out", "gas"],
            primary_goal="Save for house",
            timeline="1 year"
        )
        print("Preferences updated!")
        
        # Test 4: Create a budget plan
        print("\n=== Test 4: Create Budget Plan ===")
        plan = create_budget_plan(
            db,
            period="monthly",
            start_date="2025-01-01",
            end_date="2025-01-31",
            category_budgets={
                "coffee": 100,
                "groceries": 400,
                "dining_out": 200,
                "gas": 150
            },
            protected_categories=["coffee"],
            flexible_categories=["dining_out", "gas"],
            savings_goal=500,
            primary_goal="Save for house",
            notes="First budget plan created during onboarding"
        )
        print(f"Budget plan created: {plan.id}")
        
        # Test 5: Check budget status
        print("\n=== Test 5: Check Budget Status ===")
        status = check_budget_status(db, plan)
        print(f"Overall: {status['overall']}")
        print(f"By category: {status['by_category']}")
        
        print("\n✅ All tests passed!")
        
    finally:
        db.close()


if __name__ == "__main__":
    test_budget_helpers()