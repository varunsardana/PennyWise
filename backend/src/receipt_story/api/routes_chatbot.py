"""Chatbot endpoints for conversational budget insights"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from receipt_story.models.schemas import ChatRequest, ChatResponse
from receipt_story.services.chatbot import ChatbotService
import os
from pathlib import Path

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

# Initialize chatbot service
chatbot = ChatbotService()


def get_db():
    """Dependency to get database session"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Get the correct database path
    # backend/src/receipt_story/api/routes_chatbot.py -> backend/data/receipts.db
    base_dir = Path(__file__).parent.parent.parent.parent  # Go up to backend/
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
    
    Examples:
    - "How much did I spend this month?"
    - "What are my top spending categories?"
    - "Show me all my Starbucks purchases"
    - "Am I spending more on dining than last month?"
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
            sql=result["sql"],
            results=result["results"],
            error=result["error"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chatbot error: {str(e)}"
        )


@router.get("/suggestions")
async def get_suggestions():
    """Get suggested questions to ask the chatbot"""
    return {
        "suggestions": [
            "How much did I spend this month?",
            "What are my top 3 spending categories?",
            "Show me all coffee purchases this week",
            "Which merchant do I visit most?",
            "What's my average transaction amount?",
            "How much did I spend on groceries last month?",
            "Compare my spending this month vs last month",
            "What were my most expensive purchases?",
        ]
    }