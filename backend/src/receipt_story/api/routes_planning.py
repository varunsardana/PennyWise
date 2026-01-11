"""API routes for budget planning mode"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

# Add src to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from receipt_story.services.planning import BudgetPlanningService
from receipt_story.api.routes_chatbot import get_db

router = APIRouter(prefix="/planning", tags=["budget-planning"])

# Initialize planning service
planning_service = BudgetPlanningService()


class PlanningMessage(BaseModel):
    """Message in planning conversation"""
    role: str  # "user" or "assistant"
    content: str


class PlanningRequest(BaseModel):
    """Request for planning conversation"""
    message: str
    conversation_history: Optional[List[PlanningMessage]] = None


class PlanningResponse(BaseModel):
    """Response from planning conversation"""
    response: str
    budget_proposal: Optional[Dict[str, Any]] = None
    stage: str
    ready_to_save: bool


class SaveBudgetRequest(BaseModel):
    """Request to save a budget plan"""
    budget_proposal: Dict[str, Any]


class SaveBudgetResponse(BaseModel):
    """Response after saving budget"""
    success: bool
    plan_id: Optional[str] = None
    message: str
    plan: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class RefineBudgetRequest(BaseModel):
    """Request to refine a budget proposal"""
    original_proposal: Dict[str, Any]
    feedback: str


class RefineBudgetResponse(BaseModel):
    """Response after refining budget"""
    response: str
    budget_proposal: Optional[Dict[str, Any]] = None
    success: bool


@router.post("/start", response_model=PlanningResponse)
async def start_planning(request: PlanningRequest, db: Session = Depends(get_db)):
    """
    Start or continue a budget planning conversation.
    
    The service will guide the user through:
    1. Understanding their financial goals
    2. Analyzing current spending
    3. Identifying priorities (what they won't cut vs. flexible areas)
    4. Proposing a realistic budget
    
    When ready, returns a budget_proposal that can be saved.
    
    Example conversation:
    User: "Help me create a budget"
    Bot: "I'd love to help! What's your main financial goal?"
    User: "I want to save $500/month for a house"
    Bot: "Great! Looking at your spending, you spent $450 on coffee..."
    """
    try:
        history = None
        if request.conversation_history:
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]
        
        result = planning_service.start_planning(request.message, db, history)
        
        return PlanningResponse(
            response=result["response"],
            budget_proposal=result.get("budget_proposal"),
            stage=result["stage"],
            ready_to_save=result["ready_to_save"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Planning error: {str(e)}"
        )


@router.post("/save", response_model=SaveBudgetResponse)
async def save_budget(request: SaveBudgetRequest, db: Session = Depends(get_db)):
    """
    Save a budget plan to the database.
    
    Call this after the planning conversation produces a budget_proposal
    that the user approves.
    
    This will:
    - Save the budget plan
    - Update user preferences
    - Deactivate any previous budget plans
    - Set the new plan as active
    """
    try:
        result = planning_service.save_budget_plan(request.budget_proposal, db)
        
        return SaveBudgetResponse(
            success=result["success"],
            plan_id=result.get("plan_id"),
            message=result["message"],
            plan=result.get("plan"),
            error=result.get("error")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error saving budget: {str(e)}"
        )


@router.post("/refine", response_model=RefineBudgetResponse)
async def refine_budget(request: RefineBudgetRequest, db: Session = Depends(get_db)):
    """
    Refine a budget proposal based on user feedback.
    
    Use this when the user wants to adjust the proposed budget.
    
    Example:
    User sees proposal with coffee at $100
    User: "I need at least $150 for coffee"
    Bot: Adjusts the budget, reducing other categories to compensate
    """
    try:
        result = planning_service.refine_budget(
            request.original_proposal,
            request.feedback,
            db
        )
        
        return RefineBudgetResponse(
            response=result["response"],
            budget_proposal=result.get("budget_proposal"),
            success=result["success"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error refining budget: {str(e)}"
        )
