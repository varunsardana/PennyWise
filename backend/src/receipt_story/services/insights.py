from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from receipt_story.db.tables import Receipt

def compute_insights(db: Session, range_name: str = "week"):
    receipts = db.query(Receipt).all()

    spend_by_category = defaultdict(float)
    merchants = []
    total_spend = 0.0

    for r in receipts:
        spend_by_category[r.category] += float(r.total or 0.0)
        merchants.append(r.merchant)
        total_spend += float(r.total or 0.0)

    top_merchants = [m for m, _ in Counter(merchants).most_common(3)]
    return {
        "receipt_count": len(receipts),
        "total_spend": round(total_spend, 2),
        "spend_by_category": {k: round(v, 2) for k, v in spend_by_category.items()},
        "top_merchants": top_merchants,
    }
