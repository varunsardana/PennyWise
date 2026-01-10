#!/usr/bin/env bash
set -euo pipefail

# Run from repo root (PennyWise)
# This script creates: backend/src/receipt_story/... and backend/requirements.txt etc.

echo "==> Creating backend folder structure..."

mkdir -p backend/src/receipt_story/{api,core,models,services,db}
mkdir -p backend/src/receipt_story/services/extraction
mkdir -p backend/tests backend/scripts
mkdir -p backend/data

# --- create package marker files ---
touch backend/src/receipt_story/__init__.py
touch backend/src/receipt_story/api/__init__.py
touch backend/src/receipt_story/core/__init__.py
touch backend/src/receipt_story/models/__init__.py
touch backend/src/receipt_story/services/__init__.py
touch backend/src/receipt_story/services/extraction/__init__.py
touch backend/src/receipt_story/db/__init__.py

echo "==> Writing backend config + requirements..."

# --- create config template and requirements ---
cat > backend/.env.example <<'EOF'
# Copy to .env and fill values as needed
ENV=dev
APP_NAME=receipt-story-backend
HOST=0.0.0.0
PORT=8000

# Database (SQLite file path)
DATABASE_URL=sqlite:///./data/receipts.db

# OCR backend: "easyocr" for open-source OCR MVP
EXTRACTION_BACKEND=easyocr

# Optional: if you later add an LLM provider, put keys here (DO NOT COMMIT .env)
# OPENAI_API_KEY=...
EOF

cat > backend/requirements.txt <<'EOF'
fastapi==0.115.6
uvicorn[standard]==0.30.6
python-multipart==0.0.9
pydantic==2.9.2
pydantic-settings==2.6.1
sqlalchemy==2.0.35
python-dotenv==1.0.1
loguru==0.7.2

# OCR (open-source)
easyocr==1.7.2
opencv-python==4.10.0.84
Pillow==10.4.0

# Categorization helpers
rapidfuzz==3.9.7

# Date parsing
dateparser==1.2.0
EOF

echo "==> Updating .gitignore (root) to ignore backend runtime files..."

# Keep runtime data out of git (root .gitignore)
if ! grep -q "^backend/.env" .gitignore 2>/dev/null; then
  printf "\n# Backend runtime\nbackend/.env\nbackend/data/\nbackend/.venv/\n" >> .gitignore
fi

echo "==> Writing backend python modules..."

# --- core settings + logging ---
cat > backend/src/receipt_story/core/config.py <<'EOF'
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENV: str = "dev"
    APP_NAME: str = "receipt-story-backend"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    DATABASE_URL: str = "sqlite:///./data/receipts.db"
    EXTRACTION_BACKEND: str = "easyocr"

settings = Settings()
EOF

cat > backend/src/receipt_story/core/logging.py <<'EOF'
from loguru import logger
import sys

def configure_logging():
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    return logger
EOF

# --- Pydantic schemas (API contracts) ---
cat > backend/src/receipt_story/models/schemas.py <<'EOF'
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class ReceiptItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None

class ReceiptExtraction(BaseModel):
    merchant: str = Field(..., description="Merchant/store name")
    date: Optional[str] = Field(None, description="ISO date preferred (YYYY-MM-DD). May be None if not found.")
    currency: str = "USD"
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    tip: Optional[float] = None
    total: float
    items: List[ReceiptItem] = Field(default_factory=list)
    raw_text: Optional[str] = Field(None, description="OCR raw text for debugging (optional)")

class ReceiptPreview(ReceiptExtraction):
    category: str = Field(..., description="Assigned category (Coffee, Groceries, etc.)")

class SaveReceiptRequest(ReceiptPreview):
    pass

class SaveReceiptResponse(BaseModel):
    receipt_id: str
    saved: bool = True

class InsightsResponse(BaseModel):
    range: str
    receipt_count: int
    total_spend: float
    spend_by_category: Dict[str, float]
    top_merchants: List[str]
    story_insights: List[str]
    recommendation: str
EOF

# --- DB engine + models ---
cat > backend/src/receipt_story/db/engine.py <<'EOF'
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from receipt_story.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
EOF

cat > backend/src/receipt_story/db/tables.py <<'EOF'
import uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float

class Base(DeclarativeBase):
    pass

class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    merchant: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[str] = mapped_column(String, nullable=True)  # ISO string for MVP simplicity
    total: Mapped[float] = mapped_column(Float, nullable=False)
    tax: Mapped[float] = mapped_column(Float, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=True)
EOF

cat > backend/src/receipt_story/db/crud.py <<'EOF'
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
EOF

# --- Extraction ---
cat > backend/src/receipt_story/services/extraction/base.py <<'EOF'
from abc import ABC, abstractmethod
from receipt_story.models.schemas import ReceiptExtraction

class ReceiptExtractor(ABC):
    @abstractmethod
    def extract(self, image_bytes: bytes, mime_type: str) -> ReceiptExtraction:
        raise NotImplementedError
EOF

cat > backend/src/receipt_story/services/extraction/ocr_extractor.py <<'EOF'
import numpy as np
import cv2
import easyocr
from receipt_story.models.schemas import ReceiptExtraction

_reader = None

def get_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(["en"], gpu=False)
    return _reader

def _bytes_to_cv2(image_bytes: bytes):
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes")
    return img

def _preprocess(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 31, 10)
    return th

def _heuristic_parse(raw_text: str) -> ReceiptExtraction:
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    merchant = lines[0][:80] if lines else "UNKNOWN"

    import re
    money = []
    for ln in lines:
        nums = re.findall(r"\b\d{1,4}(?:[.,]\d{3})*(?:[.,]\d{2})\b", ln)
        for n in nums:
            v = n.replace(",", "")
            try:
                money.append(float(v))
            except:
                pass

    total = max(money, default=0.0)

    date = None
    try:
        import dateparser
        for ln in lines[:12]:
            dt = dateparser.parse(ln, settings={"PREFER_DATES_FROM": "past"})
            if dt:
                date = dt.date().isoformat()
                break
    except:
        date = None

    return ReceiptExtraction(
        merchant=merchant,
        date=date,
        total=total,
        items=[],
        raw_text=raw_text[:8000],
    )

class EasyOCRExtractor:
    def extract(self, image_bytes: bytes, mime_type: str) -> ReceiptExtraction:
        img = _bytes_to_cv2(image_bytes)
        proc = _preprocess(img)
        reader = get_reader()
        results = reader.readtext(proc)
        texts = [t[1] for t in results if t[1].strip()]
        raw_text = "\n".join(texts)
        return _heuristic_parse(raw_text)
EOF

# --- Categorization ---
cat > backend/src/receipt_story/services/categorize.py <<'EOF'
from rapidfuzz import process, fuzz

MERCHANT_RULES = {
    "STARBUCKS": "Coffee",
    "PEETS": "Coffee",
    "SAFEWAY": "Groceries",
    "COSTCO": "Groceries",
    "CHEVRON": "Gas",
    "SHELL": "Gas",
    "TARGET": "Shopping",
    "WALMART": "Shopping",
    "CVS": "Health",
    "WALGREENS": "Health",
}

def normalize_merchant(name: str) -> str:
    n = (name or "").upper()
    for ch in [",", ".", "#", "@"]:
        n = n.replace(ch, " ")
    return " ".join(n.split())

def categorize(merchant: str) -> str:
    m = normalize_merchant(merchant)

    for key, cat in MERCHANT_RULES.items():
        if key in m:
            return cat

    match = process.extractOne(m, list(MERCHANT_RULES.keys()), scorer=fuzz.WRatio)
    if match and match[1] >= 85:
        return MERCHANT_RULES[match[0]]

    return "Other"
EOF

# --- Insights + story ---
cat > backend/src/receipt_story/services/insights.py <<'EOF'
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
EOF

cat > backend/src/receipt_story/services/story.py <<'EOF'
def generate_story(insights: dict) -> tuple[list[str], str]:
    spend_by_category = insights.get("spend_by_category", {})
    receipt_count = insights.get("receipt_count", 0)
    total_spend = insights.get("total_spend", 0.0)

    if receipt_count == 0:
        return (["No receipts yet — upload a few to unlock insights."],
                "Start by scanning 2–3 receipts from different places this week.")

    biggest_cat, biggest_amt = None, 0.0
    for cat, amt in spend_by_category.items():
        if amt > biggest_amt:
            biggest_cat, biggest_amt = cat, amt

    insights_list = [
        f"You tracked {receipt_count} receipt(s) with total spend ${total_spend:.2f}.",
    ]
    if biggest_cat:
        pct = (biggest_amt / total_spend * 100) if total_spend > 0 else 0
        insights_list.append(f"Your biggest category is {biggest_cat} at ${biggest_amt:.2f} ({pct:.0f}%).")

    if biggest_cat and biggest_cat != "Other":
        rec = f"Try cutting {biggest_cat} by 10% next week — that’s about ${biggest_amt*0.10:.2f} saved."
    else:
        rec = "Try tagging a few more receipts this week to get clearer category trends."

    return (insights_list[:2], rec)
EOF

# --- API routes ---
cat > backend/src/receipt_story/api/health.py <<'EOF'
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok"}
EOF

cat > backend/src/receipt_story/api/routes_receipts.py <<'EOF'
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
EOF

cat > backend/src/receipt_story/api/routes_insights.py <<'EOF'
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
EOF

# --- main FastAPI app ---
cat > backend/src/receipt_story/main.py <<'EOF'
from fastapi import FastAPI
from receipt_story.core.logging import configure_logging
from receipt_story.api.health import router as health_router
from receipt_story.api.routes_receipts import router as receipts_router
from receipt_story.api.routes_insights import router as insights_router

logger = configure_logging()

def create_app() -> FastAPI:
    app = FastAPI(title="Receipt Story Backend", version="0.1.0")
    app.include_router(health_router)
    app.include_router(receipts_router)
    app.include_router(insights_router)

    @app.on_event("startup")
    def _startup():
        logger.info("Backend starting up...")

    return app

app = create_app()
EOF

cat > backend/README.md <<'EOF'
# PennyWise Backend (Receipt Story)

## Run (local)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
uvicorn receipt_story.main:app --reload --app-dir src --host 0.0.0.0 --port 8000
