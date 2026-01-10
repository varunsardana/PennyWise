from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from receipt_story.db.engine import SessionLocal
from receipt_story.services.insights import compute_insights
from receipt_story.services.story import generate_story
from receipt_story.models.schemas import InsightsResponse

router = APIRouter(prefix="/insights", tags=["insights"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("", response_model=InsightsResponse)
def get_insights(range: str = "week", db: Session = Depends(get_db)):
    insights = compute_insights(db, range_name=range)
    story_insights, recommendation = generate_story(insights)

    return InsightsResponse(
        range=range,
        receipt_count=insights["receipt_count"],
        total_spend=insights["total_spend"],
        spend_by_category=insights["spend_by_category"],
        top_merchants=insights["top_merchants"],
        story_insights=story_insights,
        recommendation=recommendation,
    )