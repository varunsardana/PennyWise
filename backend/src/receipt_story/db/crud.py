from sqlalchemy.orm import Session
from receipt_story.db.tables import Receipt

def create_receipt(db: Session, merchant: str, date: str | None, total: float, tax: float | None, category: str) -> Receipt:
    rec = Receipt(merchant=merchant, date=date, total=total, tax=tax, category=category)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec

def list_receipts(db: Session) -> list[Receipt]:
    return db.query(Receipt).order_by(Receipt.id.desc()).all()
