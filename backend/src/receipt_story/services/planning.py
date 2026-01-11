"""Budget Planning Mode - Guided budget creation through conversation"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from anthropic import Anthropic
from datetime import datetime, timedelta
import json

from pathlib import Path
import sys

# Add src to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from scripts.helpers import (
    analyze_spending_patterns,
    create_budget_plan,
    update_user_preferences,
    get_user_preferences
)

logger = logging.getLogger(__name__)
client = Anthropic()


class BudgetPlanningService:
    """Service for guided budget plan creation through conversation"""
    
    def __init__(self):
        self.planning_system_prompt = """You are Penny, a friendly budget planning assistant. Your job is to guide users through creating a personalized budget plan.

PLANNING STAGES:
1. ANALYZE - Understand their current spending
2. GOALS - Learn their financial goals and timeline
3. PREFERENCES - Identify what they won't cut vs. willing to adjust
4. PROPOSE - Create a realistic budget plan
5. REFINE - Adjust based on their feedback
6. FINALIZE - Save the budget plan

YOUR APPROACH:
- Ask ONE question at a time (don't overwhelm)
- Be conversational and encouraging
- Use their actual spending data to ground the conversation
- Respect their lifestyle and priorities
- Suggest realistic cuts, not extreme changes
- Explain your reasoning

CONVERSATION FLOW EXAMPLE:
User: "Help me create a budget"
You: "I'd love to help! I see you spent $1,234 last month. What's your main financial goal? (e.g., save for vacation, pay off debt, build emergency fund)"

User: "I want to save for a house down payment"
You: "That's a great goal! How much are you hoping to save per month, and what's your timeline?"

User: "I want to save $500/month over the next year"
You: "Perfect! To save $500/month, we need to find $500 in your current spending. Looking at your receipts, you spent $450 on coffee and $800 on dining out last month. Are either of these non-negotiable for you?"

User: "Coffee is my life, don't touch it"
You: "I respect that! Coffee stays at $450 ✓ Let's look at other areas. You also spent $200 on Uber and $300 on entertainment. Would you be open to reducing either of these?"

And so on...

KEEP TRACK OF:
- What stage you're in
- What you've learned (goals, preferences, constraints)
- What numbers make sense based on their spending
- Whether they seem comfortable with suggestions

OUTPUT FORMAT:
When you have enough information to propose a budget, respond with a JSON object wrapped in <budget_proposal></budget_proposal> tags:

<budget_proposal>
{
  "period": "monthly",
  "start_date": "2025-02-01",
  "end_date": "2025-02-28",
  "category_budgets": {
    "coffee": 450,
    "groceries": 400,
    "dining_out": 600,
    "transportation": 50,
    "entertainment": 150
  },
  "protected_categories": ["coffee"],
  "flexible_categories": ["dining_out", "transportation", "entertainment"],
  "savings_goal": 500,
  "primary_goal": "Save for house down payment",
  "total_budget": 2150,
  "reasoning": "Reduced dining out by $200, switched from Uber to public transit (-$150), and reduced entertainment by $150 to reach $500/month savings goal while protecting coffee budget."
}
</budget_proposal>

Otherwise, just respond conversationally to continue the planning conversation."""
    
    def start_planning(
        self,
        message: str,
        db: Session,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Guide user through budget planning.
        
        Returns:
            Dict with response and optionally a budget_proposal if ready to create
        """
        logger.info("=== BUDGET PLANNING MODE ===")
        logger.info(f"User message: {message}")
        
        if conversation_history is None:
            conversation_history = []
        
        # Analyze their current spending to provide context
        spending = analyze_spending_patterns(db)
        prefs = get_user_preferences(db)
        
        # Build context for Claude
        spending_context = f"""
USER'S CURRENT SPENDING DATA:
- Total monthly spend: ${spending['total_spend']}
- Number of transactions: {spending['num_transactions']}
- Average transaction: ${spending['avg_transaction']}

Breakdown by category:
{json.dumps(spending['by_category'], indent=2)}

Top merchants:
{json.dumps(spending['top_merchants'], indent=2)}
"""
        
        prefs_context = ""
        if prefs.primary_goal or prefs.wont_cut != "[]":
            wont_cut = json.loads(prefs.wont_cut) if prefs.wont_cut else []
            willing = json.loads(prefs.willing_to_cut) if prefs.willing_to_cut else []
            prefs_context = f"""
KNOWN PREFERENCES (from previous conversations):
- Primary Goal: {prefs.primary_goal or 'Not set'}
- Won't Cut: {wont_cut or 'Not specified'}
- Willing to Cut: {willing or 'Not specified'}
"""
        
        # Build conversation
        messages = conversation_history.copy()
        messages.append({"role": "user", "content": message})
        
        full_system_prompt = self.planning_system_prompt + "\n\n" + spending_context + prefs_context
        
        # Call Claude
        logger.info("Calling Claude for planning guidance...")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            temperature=0.7,
            system=full_system_prompt,
            messages=messages
        )
        
        response_text = response.content[0].text
        logger.info(f"Claude response: {response_text[:200]}...")
        
        # Check if Claude has proposed a budget
        import re
        budget_match = re.search(
            r'<budget_proposal>(.*?)</budget_proposal>',
            response_text,
            re.DOTALL
        )
        
        if budget_match:
            logger.info("Budget proposal detected!")
            try:
                # Extract and parse the JSON
                budget_json = budget_match.group(1).strip()
                budget_data = json.loads(budget_json)
                
                # Remove the JSON from the response text
                response_text = re.sub(
                    r'<budget_proposal>.*?</budget_proposal>',
                    '',
                    response_text,
                    flags=re.DOTALL
                ).strip()
                
                return {
                    "response": response_text,
                    "budget_proposal": budget_data,
                    "stage": "proposal",
                    "ready_to_save": True
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse budget JSON: {e}")
                return {
                    "response": "I created a budget plan but there was an error formatting it. Let me try again.",
                    "budget_proposal": None,
                    "stage": "error",
                    "ready_to_save": False
                }
        
        # Still in conversation - determine stage
        stage = self._detect_stage(response_text)
        logger.info(f"Current stage: {stage}")
        
        return {
            "response": response_text,
            "budget_proposal": None,
            "stage": stage,
            "ready_to_save": False
        }
    
    def _detect_stage(self, response_text: str) -> str:
        """Detect what stage of planning we're in based on response"""
        text_lower = response_text.lower()
        
        if any(word in text_lower for word in ["goal", "saving for", "trying to achieve"]):
            return "goals"
        elif any(word in text_lower for word in ["won't cut", "non-negotiable", "willing to reduce"]):
            return "preferences"
        elif any(word in text_lower for word in ["here's a plan", "budget proposal", "sound good"]):
            return "proposal"
        elif any(word in text_lower for word in ["let's analyze", "you spent", "looking at your receipts"]):
            return "analyze"
        else:
            return "conversation"
    
    def save_budget_plan(
        self,
        budget_data: Dict[str, Any],
        db: Session,
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """
        Save a budget plan to the database and update user preferences.
        
        Args:
            budget_data: The budget proposal from Claude
            db: Database session
            user_id: User ID
            
        Returns:
            Dict with saved plan details
        """
        logger.info("Saving budget plan to database...")
        
        try:
            # Update user preferences if they were captured
            if budget_data.get("protected_categories") or budget_data.get("flexible_categories"):
                update_user_preferences(
                    db,
                    wont_cut=budget_data.get("protected_categories", []),
                    willing_to_cut=budget_data.get("flexible_categories", []),
                    primary_goal=budget_data.get("primary_goal"),
                    user_id=user_id
                )
                logger.info("User preferences updated")
            
            # Create the budget plan
            plan = create_budget_plan(
                db,
                period=budget_data["period"],
                start_date=budget_data["start_date"],
                end_date=budget_data["end_date"],
                category_budgets=budget_data["category_budgets"],
                protected_categories=budget_data.get("protected_categories", []),
                flexible_categories=budget_data.get("flexible_categories", []),
                savings_goal=budget_data.get("savings_goal"),
                primary_goal=budget_data.get("primary_goal"),
                notes=budget_data.get("reasoning", ""),
                user_id=user_id
            )
            
            logger.info(f"Budget plan saved with ID: {plan.id}")
            
            return {
                "success": True,
                "plan_id": plan.id,
                "message": "Budget plan created successfully! 🎉",
                "plan": {
                    "period": plan.period,
                    "total_budget": plan.total_budget,
                    "savings_goal": plan.savings_goal,
                    "category_budgets": json.loads(plan.category_budgets)
                }
            }
            
        except Exception as e:
            logger.error(f"Error saving budget plan: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to save budget plan. Please try again."
            }
    
    def refine_budget(
        self,
        original_proposal: Dict[str, Any],
        user_feedback: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Refine a budget proposal based on user feedback.
        
        Args:
            original_proposal: The original budget proposal
            user_feedback: User's feedback/concerns
            db: Database session
            
        Returns:
            Dict with refined proposal
        """
        logger.info("Refining budget based on feedback...")
        
        spending = analyze_spending_patterns(db)
        
        refinement_prompt = f"""The user gave feedback on this budget proposal:

ORIGINAL PROPOSAL:
{json.dumps(original_proposal, indent=2)}

USER FEEDBACK:
"{user_feedback}"

CURRENT SPENDING DATA:
{json.dumps(spending['by_category'], indent=2)}

Please adjust the budget based on their feedback while still trying to meet their savings goal if possible.
Respond with a refined budget proposal in the same <budget_proposal></budget_proposal> format."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            temperature=0.7,
            system=self.planning_system_prompt,
            messages=[{"role": "user", "content": refinement_prompt}]
        )
        
        response_text = response.content[0].text
        
        # Extract refined proposal
        import re
        budget_match = re.search(
            r'<budget_proposal>(.*?)</budget_proposal>',
            response_text,
            re.DOTALL
        )
        
        if budget_match:
            try:
                budget_json = budget_match.group(1).strip()
                refined_data = json.loads(budget_json)
                
                response_text = re.sub(
                    r'<budget_proposal>.*?</budget_proposal>',
                    '',
                    response_text,
                    flags=re.DOTALL
                ).strip()
                
                return {
                    "response": response_text,
                    "budget_proposal": refined_data,
                    "success": True
                }
            except json.JSONDecodeError:
                return {
                    "response": "I had trouble refining the budget. Could you clarify what you'd like to change?",
                    "budget_proposal": None,
                    "success": False
                }
        
        return {
            "response": response_text,
            "budget_proposal": None,
            "success": False
        }