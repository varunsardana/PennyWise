"""Enhanced chatbot endpoints with budget context"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from receipt_story.models.schemas import ChatRequest, ChatResponse
from receipt_story.services.chatbot import ChatbotService
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
from pathlib import Path

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

# Initialize chatbot service
chatbot = ChatbotService()


def get_db():
    """Dependency to get database session"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Get the correct database path
    base_dir = Path(__file__).parent.parent.parent.parent # Go up to backend/
    db_path = base_dir / "data" / "receipts.db"
    
    # Create absolute path URI for SQLite
    db_url = f"sqlite:///{db_path.absolute()}"
    
    engine = create_engine(db_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Chatbot endpoint for conversational budget insights.
    
    Now includes:
    - Budget plan awareness
    - User preference context
    - Spending pattern analysis
    - Budget tracking
    
    Examples:
    - "How much did I spend this month?"
    - "Help me create a budget"
    - "Am I on track with my budget?"
    - "I need to adjust my budget for an unexpected expense"
    """
    try:
        # Convert Pydantic models to dicts for the service
        history = None
        if request.conversation_history:
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]
        
        result = chatbot.chat(request.message, db, history)
        
        return ChatResponse(
            response=result["response"],
            sql=result.get("sql"),
            results=result.get("results"),
            error=result.get("error")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chatbot error: {str(e)}"
        )


class BudgetSummaryResponse(BaseModel):
    """Response model for budget summary"""
    has_budget: bool
    plan: Optional[Dict[str, Any]] = None
    status: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


@router.get("/budget-summary", response_model=BudgetSummaryResponse)
async def get_budget_summary(db: Session = Depends(get_db)):
    """
    Get a quick summary of the user's current budget status.
    
    Returns:
    - Whether user has an active budget
    - Budget plan details
    - Current spending vs budget for each category
    - Overall progress
    """
    try:
        summary = chatbot.get_budget_summary(db)
        return BudgetSummaryResponse(**summary)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching budget summary: {str(e)}"
        )


@router.get("/suggestions")
async def get_suggestions(db: Session = Depends(get_db)):
    """
    Get suggested questions to ask the chatbot.
    Now context-aware based on whether user has a budget.
    """
    from scripts.helpers import get_active_budget_plan
    
    budget_plan = get_active_budget_plan(db)
    
    if budget_plan:
        # User has a budget - suggest tracking and adjustment questions
        return {
            "suggestions": [
                "How am I doing with my budget this month?",
                "Which categories am I overspending in?",
                "Show me my coffee spending vs my budget",
                "Am I on track to meet my savings goal?",
                "Help me adjust my budget for an unexpected expense",
                "What's my spending trend compared to last month?",
                "Which merchants am I spending the most at?",
                "Can I afford to increase my dining budget?"
            ]
        }
    else:
        # No budget - suggest analysis and planning questions
        return {
            "suggestions": [
                "Help me create a budget",
                "What are my biggest spending categories?",
                "How much did I spend this month?",
                "Show me all my coffee purchases",
                "Which merchant do I visit most?",
                "What's my average transaction amount?",
                "Analyze my spending patterns",
                "How much do I spend on groceries vs dining out?"
            ]
        }


@router.get("/context")
async def get_user_context(db: Session = Depends(get_db)):
    """
    Get the current user context (for debugging or UI display).
    Shows what information the chatbot has about the user.
    """
    from scripts.helpers import (
        get_active_budget_plan,
        get_user_preferences,
        analyze_spending_patterns
    )
    import json
    
    try:
        budget_plan = get_active_budget_plan(db)
        prefs = get_user_preferences(db)
        spending = analyze_spending_patterns(db)
        
        context = {
            "has_active_budget": budget_plan is not None,
            "budget_plan": None,
            "preferences": None,
            "spending_overview": spending
        }
        
        if budget_plan:
            context["budget_plan"] = {
                "period": budget_plan.period,
                "date_range": {
                    "start": budget_plan.start_date,
                    "end": budget_plan.end_date
                },
                "total_budget": budget_plan.total_budget,
                "category_budgets": json.loads(budget_plan.category_budgets),
                "protected_categories": json.loads(budget_plan.protected_categories),
                "flexible_categories": json.loads(budget_plan.flexible_categories),
                "savings_goal": budget_plan.savings_goal,
                "primary_goal": budget_plan.primary_goal
            }
        
        if prefs:
            context["preferences"] = {
                "wont_cut": json.loads(prefs.wont_cut) if prefs.wont_cut else [],
                "willing_to_cut": json.loads(prefs.willing_to_cut) if prefs.willing_to_cut else [],
                "primary_goal": prefs.primary_goal,
                "timeline": prefs.timeline
            }
        
        return context
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching context: {str(e)}"
        )


# """Chatbot endpoints for conversational budget insights"""

# from fastapi import APIRouter, HTTPException, Depends
# from sqlalchemy.orm import Session
# from receipt_story.models.schemas import ChatRequest, ChatResponse
# from receipt_story.services.chatbot import ChatbotService
# import os
# from pathlib import Path

# router = APIRouter(prefix="/chatbot", tags=["chatbot"])

# # Initialize chatbot service
# chatbot = ChatbotService()


# def get_db():
#     """Dependency to get database session"""
#     from sqlalchemy import create_engine
#     from sqlalchemy.orm import sessionmaker
    
#     # Get the correct database path
#     # backend/src/receipt_story/api/routes_chatbot.py -> backend/data/receipts.db
#     base_dir = Path(__file__).parent.parent.parent.parent  # Go up to backend/
#     db_path = base_dir / "data" / "receipts.db"
    
#     # Create absolute path URI for SQLite
#     db_url = f"sqlite:///{db_path.absolute()}"
    
#     engine = create_engine(db_url, echo=False)
#     SessionLocal = sessionmaker(bind=engine)
    
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# @router.post("/chat", response_model=ChatResponse)
# async def chat(request: ChatRequest, db: Session = Depends(get_db)):
#     """
#     Chatbot endpoint for conversational budget insights.
    
#     Examples:
#     - "How much did I spend this month?"
#     - "What are my top spending categories?"
#     - "Show me all my Starbucks purchases"
#     - "Am I spending more on dining than last month?"
#     """
#     try:
#         # Convert Pydantic models to dicts for the service
#         history = None
#         if request.conversation_history:
#             history = [
#                 {"role": msg.role, "content": msg.content}
#                 for msg in request.conversation_history
#             ]
        
#         result = chatbot.chat(request.message, db, history)
        
#         return ChatResponse(
#             response=result["response"],
#             sql=result["sql"],
#             results=result["results"],
#             error=result["error"]
#         )
        
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Chatbot error: {str(e)}"
#         )


# @router.get("/suggestions")
# async def get_suggestions():
#     """Get suggested questions to ask the chatbot"""
#     return {
#         "suggestions": [
#             "How much did I spend this month?",
#             "What are my top 3 spending categories?",
#             "Show me all coffee purchases this week",
#             "Which merchant do I visit most?",
#             "What's my average transaction amount?",
#             "How much did I spend on groceries last month?",
#             "Compare my spending this month vs last month",
#             "What were my most expensive purchases?",
#         ]
#     }