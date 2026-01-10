from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from receipt_story.core.config import settings
from receipt_story.db.engine import SessionLocal, engine
from receipt_story.db.tables import Base
from receipt_story.db import crud
from receipt_story.models.schemas import ReceiptPreview, SaveReceiptRequest, SaveReceiptResponse
from receipt_story.services.categorize import categorize
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
    if settings.EXTRACTION_BACKEND != "easyocr":
        raise RuntimeError("Only easyocr extractor configured for MVP")
    return EasyOCRExtractor()

@router.post("/parse", response_model=ReceiptPreview)
async def parse_receipt(file: UploadFile = File(...)):
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Unsupported image type. Use jpeg/png/webp.")

    img_bytes = await file.read()
    extractor = get_extractor()
    extracted = extractor.extract(img_bytes, mime_type=file.content_type)

    cat = categorize(extracted.merchant)
    preview = ReceiptPreview(**extracted.model_dump(exclude_none=False), category=cat)
    return preview

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
