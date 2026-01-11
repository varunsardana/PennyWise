from typing import Optional
from sqlalchemy.orm import Session
from receipt_story.db.tables import Receipt


def create_receipt(db: Session, merchant: str, date: Optional[str], total: float, tax: Optional[float], category: str) -> Receipt:
    rec = Receipt(merchant=merchant, date=date, total=total, tax=tax, category=category)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec

def list_receipts(db: Session) -> list[Receipt]:
    return db.query(Receipt).order_by(Receipt.id.desc()).all()


def delete_receipt(db: Session, receipt_id: str) -> bool:
    rec = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if rec:
        db.delete(rec)
        db.commit()
        return True
    return False


def update_receipt(db: Session, receipt_id: str, merchant: str = None, date: str = None, total: float = None, tax: float = None, category: str = None) -> Receipt:
    rec = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not rec:
        return None
    if merchant is not None:
        rec.merchant = merchant
    if date is not None:
        rec.date = date
    if total is not None:
        rec.total = total
    if tax is not None:
        rec.tax = tax
    if category is not None:
        rec.category = category
    db.commit()
    db.refresh(rec)
    return rec
