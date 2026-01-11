"""Chatbot service for conversational budget insights with SQLAlchemy"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from anthropic import Anthropic
from receipt_story.services.text_to_sql import generate_sql, is_safe_query
from receipt_story.db.schema import get_schema_for_llm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

client = Anthropic()


class ChatbotService:
    """Service for handling chatbot conversations about budget data"""
    
    def __init__(self):
        logger.info("ChatbotService initialized")
    
    def execute_query(self, sql: str, db: Session) -> List[Dict[str, Any]]:
        """Execute SQL query using SQLAlchemy session and return results"""
        logger.info(f"Executing SQL query: {sql}")
        
        try:
            # Execute raw SQL using SQLAlchemy
            result = db.execute(text(sql))
            
            # Convert to list of dicts
            rows = result.fetchall()
            
            # Get column names from result
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
            Dict with response, sql (if executed), and results (if any)
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
        
        schema = get_schema_for_llm()
        logger.debug(f"Schema loaded: {len(schema)} characters")
        
        # Step 1: Determine if we need to query the database
        decision_prompt = f"""You are a helpful budget insights assistant.

Database Schema:
{schema}

The user said: "{message}"

Does this question require querying the database for data?
Respond with ONLY "YES" or "NO"."""

        logger.info("Step 1: Asking Claude if data is needed...")
        
        decision_response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            temperature=0,
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
                        "error": "Unsafe query"
                    }
                
                # Execute query using SQLAlchemy session
                logger.info("Step 4: Executing SQL query...")
                results = self.execute_query(sql, db)
                
                # Log results summary
                logger.info(f"Query successful: {len(results)} rows returned")
                if results:
                    logger.info(f"Sample result: {results[0]}")
                
                # Generate insights
                logger.info("Step 5: Generating insights from results...")
                
                insights_prompt = f"""The user asked: "{message}"

Query executed: {sql}

Results ({len(results)} rows): {results[:10]}

Provide a natural, conversational response with insights about these results. Be specific with numbers and helpful. Keep it concise (2-4 sentences)."""

                insights_response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=500,
                    temperature=0.7,
                    messages=[{"role": "user", "content": insights_prompt}]
                )
                
                final_response = insights_response.content[0].text
                logger.info(f"Final response generated: {final_response[:100]}...")
                logger.info("=" * 80)
                
                return {
                    "response": final_response,
                    "sql": sql,
                    "results": results,
                    "error": None
                }
                
            except Exception as e:
                logger.error(f"Database error: {e}", exc_info=True)
                return {
                    "response": f"I had trouble querying the database. Could you rephrase your question?",
                    "sql": sql if 'sql' in locals() else None,
                    "results": None,
                    "error": str(e)
                }
        
        else:
            # Just conversational, no data needed
            logger.info("Step 2: Generating conversational response (no SQL needed)...")
            
            conversational_response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                temperature=0.7,
                system="You are a helpful budget insights assistant. Be friendly and conversational.",
                messages=messages
            )
            
            final_response = conversational_response.content[0].text
            logger.info(f"Conversational response: {final_response[:100]}...")
            logger.info("=" * 80)
            
            return {
                "response": final_response,
                "sql": None,
                "results": None,
                "error": None
            }