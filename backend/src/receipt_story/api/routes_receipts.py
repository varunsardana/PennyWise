from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
import os

from receipt_story.core.config import settings
from receipt_story.db.engine import SessionLocal, engine
from receipt_story.db.tables import Base
from receipt_story.db import crud
from receipt_story.models.schemas import (
    ReceiptPreview,
    SaveReceiptRequest,
    SaveReceiptResponse,
    ScanReceiptResponse,
)
from receipt_story.services.categorize import categorize
from receipt_story.services.extraction.hybrid_extractor import HybridExtractor
from receipt_story.services.extraction.ocr_extractor import EasyOCRExtractor

router = APIRouter(prefix="/receipts", tags=["receipts"])

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_extractor():
    """
    Decide extraction backend from settings.
    - EXTRACTION_BACKEND=easyocr  -> OCR only
    - EXTRACTION_BACKEND=hybrid   -> OCR + Vision fallback
    """
    backend = getattr(settings, "EXTRACTION_BACKEND", "hybrid")

    if backend == "easyocr":
        return EasyOCRExtractor()

    if backend == "hybrid":
        return HybridExtractor()

    raise RuntimeError(f"Unsupported extractor configured: {backend}")


@router.post("/parse", response_model=ReceiptPreview)
async def parse_receipt(file: UploadFile = File(...)):
    # Debug: show whether force vision is set
    print("HIT /receipts/parse FORCE=", os.getenv("RECEIPT_FORCE_VISION"))

    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Unsupported image type. Use jpeg/png/webp.")

    img_bytes = await file.read()

    extractor = get_extractor()
    print("EXTRACTOR_IN_USE:", extractor.__class__.__name__)

    extracted = extractor.extract(img_bytes, mime_type=file.content_type)

    cat = categorize(extracted.merchant)

    preview = ReceiptPreview(
        **extracted.model_dump(exclude_none=False),
        category=cat,
    )
    return preview


@router.post("/scan", response_model=ScanReceiptResponse)
async def scan_receipt(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Hackathon MVP: Upload -> Parse -> Categorize -> Save -> Return receipt_id + preview
    """
    print("HIT /receipts/scan FORCE=", os.getenv("RECEIPT_FORCE_VISION"))

    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Unsupported image type. Use jpeg/png/webp.")

    img_bytes = await file.read()

    extractor = get_extractor()
    print("EXTRACTOR_IN_USE:", extractor.__class__.__name__)

    extracted = extractor.extract(img_bytes, mime_type=file.content_type)

    cat = categorize(extracted.merchant)

    preview = ReceiptPreview(
        **extracted.model_dump(exclude_none=False),
        category=cat,
    )

    # Save ONLY what your receipts table stores (MVP)
    rec = crud.create_receipt(
        db=db,
        merchant=preview.merchant,
        date=preview.date,
        total=preview.total,
        tax=preview.tax,
        category=preview.category,
    )

    return ScanReceiptResponse(receipt_id=rec.id, preview=preview)


@router.post("", response_model=SaveReceiptResponse)
def save_receipt(payload: SaveReceiptRequest, db: Session = Depends(get_db)):
    rec = crud.create_receipt(
        db=db,
        merchant=payload.merchant,
        date=payload.date,
        total=payload.total,
        tax=payload.tax,
        category=payload.category,
    )
    return SaveReceiptResponse(receipt_id=rec.id)


@router.get("")
def list_receipts(db: Session = Depends(get_db)):
    """
    Hackathon-simple: return DB rows as dictionaries.
    """
    rows = crud.list_receipts(db)
    return [
        {
            "id": r.id,
            "merchant": r.merchant,
            "date": r.date,
            "total": r.total,
            "tax": r.tax,
            "category": r.category,
            "created_at": getattr(r, "created_at", None),
        }
        for r in rows
    ]


@router.delete("/{receipt_id}")
def delete_receipt(receipt_id: str, db: Session = Depends(get_db)):
    """
    Delete a receipt by ID.
    """
    success = crud.delete_receipt(db, receipt_id)
    if not success:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return {"success": True, "message": "Receipt deleted"}


@router.put("/{receipt_id}")
def update_receipt(receipt_id: str, payload: SaveReceiptRequest, db: Session = Depends(get_db)):
    """
    Update a receipt by ID.
    """
    rec = crud.update_receipt(
        db=db,
        receipt_id=receipt_id,
        merchant=payload.merchant,
        date=payload.date,
        total=payload.total,
        tax=payload.tax,
        category=payload.category,
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return {
        "id": rec.id,
        "merchant": rec.merchant,
        "date": rec.date,
        "total": rec.total,
        "tax": rec.tax,
        "category": rec.category,
    }
