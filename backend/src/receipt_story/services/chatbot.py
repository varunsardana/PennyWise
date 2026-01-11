"""Enhanced chatbot service with budget planning capabilities"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from anthropic import Anthropic
from receipt_story.services.text_to_sql import generate_sql, is_safe_query
from receipt_story.db.schema import get_schema_for_llm
from scripts.helpers import (
    get_active_budget_plan,
    get_user_preferences,
    analyze_spending_patterns,
    check_budget_status
)
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

client = Anthropic()


def get_enhanced_system_prompt(db: Session) -> str:
    """
    Build system prompt with current user context (budget, preferences, spending patterns)
    """
    schema = get_schema_for_llm()
    
    # Get user's current budget plan
    budget_plan = get_active_budget_plan(db)
    budget_context = ""
    if budget_plan:
        category_budgets = json.loads(budget_plan.category_budgets)
        protected = json.loads(budget_plan.protected_categories)
        flexible = json.loads(budget_plan.flexible_categories)
        
        budget_context = f"""
ACTIVE BUDGET PLAN:
- Period: {budget_plan.period}
- Date Range: {budget_plan.start_date} to {budget_plan.end_date}
- Total Budget: ${budget_plan.total_budget}
- Savings Goal: ${budget_plan.savings_goal if budget_plan.savings_goal else 'None'}
- Primary Goal: {budget_plan.primary_goal if budget_plan.primary_goal else 'None'}

Category Budgets:
{json.dumps(category_budgets, indent=2)}

Protected Categories (user won't cut): {protected}
Flexible Categories (user willing to adjust): {flexible}
"""
    else:
        budget_context = "NO ACTIVE BUDGET PLAN - User may need help creating one."
    
    # Get user preferences
    prefs = get_user_preferences(db)
    prefs_context = ""
    if prefs:
        wont_cut = json.loads(prefs.wont_cut) if prefs.wont_cut else []
        willing = json.loads(prefs.willing_to_cut) if prefs.willing_to_cut else []
        
        if wont_cut or willing or prefs.primary_goal:
            prefs_context = f"""
USER PREFERENCES:
- Won't Cut: {wont_cut if wont_cut else 'Not specified'}
- Willing to Cut: {willing if willing else 'Not specified'}
- Primary Goal: {prefs.primary_goal if prefs.primary_goal else 'Not specified'}
- Timeline: {prefs.timeline if prefs.timeline else 'Not specified'}
"""
    
    # Get recent spending overview
    spending = analyze_spending_patterns(db)
    spending_context = f"""
RECENT SPENDING OVERVIEW:
- Total Transactions: {spending['num_transactions']}
- Total Spent: ${spending['total_spend']}
- Average Transaction: ${spending['avg_transaction']}
- Top Categories: {list(spending['by_category'].keys())[:3]}
"""
    
    system_prompt = f"""You are a personalized budget coach named Penny. You help users understand their spending, create realistic budgets, and achieve their financial goals.

Database Schema:
{schema}

{budget_context}

{prefs_context}

{spending_context}

YOUR CAPABILITIES:

1. CHAT MODE (Default)
   - Answer questions about spending: "How much did I spend on coffee?"
   - Provide insights from receipt data
   - Be conversational and helpful

2. PLANNING MODE
   - Help users create personalized budget plans
   - Ask questions to understand their goals and priorities
   - Respect their preferences (what they won't cut vs. willing to adjust)
   - Create realistic, achievable budgets

3. TRACKING MODE
   - Monitor budget adherence
   - Alert users to overspending or approaching limits
   - Celebrate when they're on track or under budget

4. ADJUSTMENT MODE
   - Help users adapt their budget when life happens
   - Propose adjustments that respect their priorities
   - Rebalance budgets intelligently

KEY PRINCIPLES:
- Always respect protected categories (things user won't cut)
- Be encouraging and supportive, never judgmental
- Use specific numbers and data from their actual spending
- Be conversational and empathetic
- Remember context from the conversation
- Ask clarifying questions when needed
- Provide actionable, specific advice

WHEN TO USE SQL:
- If you need to query spending data to answer a question, generate SQL
- For planning/tracking, you may need to query receipts for analysis
- Always use the schema provided above

CONVERSATION STYLE:
- Friendly and supportive (like a helpful friend who's good with money)
- Use emojis sparingly (💰 ✅ 🎯 when appropriate)
- Keep responses concise but informative (2-4 sentences for simple questions)
- Ask users for only 1-2 questions at a time. Do not overwhelm them!!
- For complex topics (budget planning), take time to explain clearly"""

    return system_prompt


class ChatbotService:
    """Service for handling chatbot conversations about budget data"""
    
    def __init__(self):
        logger.info("ChatbotService initialized")
    
    def execute_query(self, sql: str, db: Session) -> List[Dict[str, Any]]:
        """Execute SQL query using SQLAlchemy session and return results"""
        logger.info(f"Executing SQL query: {sql}")
        
        try:
            result = db.execute(text(sql))
            rows = result.fetchall()
            
            if rows and hasattr(result, 'keys'):
                columns = result.keys()
                results = [dict(zip(columns, row)) for row in rows]
            else:
                results = []
            
            logger.info(f"Query returned {len(results)} rows")
            if results:
                logger.debug(f"First row: {results[0]}")
            
            return results
            
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            raise
    
    def chat(
        self, 
        message: str,
        db: Session,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message and return a response with data if needed.
        
        Args:
            message: User's message
            db: SQLAlchemy database session
            conversation_history: Previous messages in conversation
            
        Returns:
            Dict with response, sql (if executed), results (if any), and metadata
        """
        logger.info("=" * 80)
        logger.info(f"NEW CHAT REQUEST")
        logger.info(f"User message: {message}")
        logger.info(f"Conversation history length: {len(conversation_history) if conversation_history else 0}")
        
        if conversation_history is None:
            conversation_history = []
        
        # Build conversation for Claude
        messages = conversation_history.copy()
        messages.append({"role": "user", "content": message})
        
        # Get enhanced system prompt with user context
        system_prompt = get_enhanced_system_prompt(db)
        logger.debug(f"System prompt length: {len(system_prompt)} characters")
        
        # Step 1: Determine if we need to query the database
        decision_prompt = f"""Based on the conversation, does this question require querying the receipts database?

User said: "{message}"

Respond with ONLY "YES" or "NO".

Examples:
- "How much did I spend on coffee?" -> YES
- "What's my budget for groceries?" -> NO (budget info is already in context)
- "Show me my Starbucks purchases" -> YES
- "Help me create a budget" -> NO (conversational planning)
- "Am I over budget this month?" -> YES (need to compare actual vs budget)"""

        logger.info("Step 1: Asking Claude if data query is needed...")
        
        decision_response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": decision_prompt}]
        )
        
        decision = decision_response.content[0].text.strip().upper()
        needs_data = "YES" in decision
        
        logger.info(f"Claude decision: {decision}")
        logger.info(f"Needs database query: {needs_data}")
        
        if needs_data:
            logger.info("Step 2: Generating SQL query...")
            
            try:
                # Use the generate_sql function
                sql = generate_sql(message)
                logger.info(f"Generated SQL: {sql}")
                
                # Validate safety
                logger.info("Step 3: Validating SQL safety...")
                is_safe = is_safe_query(sql)
                logger.info(f"SQL is safe: {is_safe}")
                
                if not is_safe:
                    logger.warning("UNSAFE SQL DETECTED - Blocking execution")
                    return {
                        "response": "I couldn't generate a safe query for that. Could you rephrase your question?",
                        "sql": sql,
                        "results": None,
                        "error": "Unsafe query",
                        "mode": "chat"
                    }
                
                # Execute query using SQLAlchemy session
                logger.info("Step 4: Executing SQL query...")
                results = self.execute_query(sql, db)
                
                # Log results summary
                logger.info(f"Query successful: {len(results)} rows returned")
                if results:
                    logger.info(f"Sample result: {results[0]}")
                
                # Generate insights with full context
                logger.info("Step 5: Generating insights from results...")
                
                insights_prompt = f"""The user asked: "{message}"

Query executed: {sql}

Results ({len(results)} rows): {results[:10]}

Provide a natural, conversational response with insights about these results. 
Use the budget context and user preferences you have to make your response more personalized.
Be specific with numbers and helpful. Keep it concise (2-4 sentences)."""

                insights_response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=500,
                    temperature=0.7,
                    system=system_prompt,
                    messages=[{"role": "user", "content": insights_prompt}]
                )
                
                final_response = insights_response.content[0].text
                logger.info(f"Final response generated: {final_response[:100]}...")
                logger.info("=" * 80)
                
                return {
                    "response": final_response,
                    "sql": sql,
                    "results": results,
                    "error": None,
                    "mode": "chat"
                }
                
            except Exception as e:
                logger.error(f"Database error: {e}", exc_info=True)
                return {
                    "response": f"I had trouble querying the database. Could you rephrase your question?",
                    "sql": sql if 'sql' in locals() else None,
                    "results": None,
                    "error": str(e),
                    "mode": "chat"
                }
        
        else:
            # Just conversational, no data needed
            logger.info("Step 2: Generating conversational response (no SQL needed)...")
            
            conversational_response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=800,
                temperature=0.7,
                system=system_prompt,
                messages=messages
            )
            
            final_response = conversational_response.content[0].text
            logger.info(f"Conversational response: {final_response[:100]}...")
            logger.info("=" * 80)
            
            # Detect what mode we're in based on response content
            mode = "chat"
            response_lower = final_response.lower()
            if any(word in response_lower for word in ["budget plan", "let's create", "help you plan"]):
                mode = "planning"
            elif any(word in response_lower for word in ["over budget", "on track", "spending is"]):
                mode = "tracking"
            
            return {
                "response": final_response,
                "sql": None,
                "results": None,
                "error": None,
                "mode": mode
            }
    
    def get_budget_summary(self, db: Session) -> Dict[str, Any]:
        """Get a quick summary of budget status"""
        budget_plan = get_active_budget_plan(db)
        
        if not budget_plan:
            return {
                "has_budget": False,
                "message": "No active budget plan"
            }
        
        status = check_budget_status(db, budget_plan)
        
        return {
            "has_budget": True,
            "plan": {
                "period": budget_plan.period,
                "total_budget": budget_plan.total_budget,
                "savings_goal": budget_plan.savings_goal
            },
            "status": status
        }