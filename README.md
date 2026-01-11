# PennyWise 💸
**Scan receipts → save expenses → visualize trends & forecasts.**

PennyWise is a lightweight personal finance tracker that lets you:
- 📷 **Scan / upload receipts**
- 🔍 Extract totals, merchant, date, tax, category (OCR-first)
- 🧠 Optionally use a **Vision fallback (OpenAI / Anthropic)** when OCR is weak
- 💾 Store receipts in **SQLite**
- 📈 View **history + trends + simple forecasting** in a clean React dashboard

---

## Features

- Upload a receipt image → extract:
  - merchant, date, currency, subtotal/tax/total, category (and more)
- Hybrid extraction pipeline:
  - **OCR-first** (fast, local)
  - Optional **Vision LLM fallback** for difficult receipts
- Save receipts to **SQLite**
- Insights / trends endpoints for dashboards
- Chatbot support (Anthropic)

 ---

## Tech Stack

**Backend**
- Python + FastAPI
- EasyOCR + OpenCV preprocessing
- SQLite (local dev)

**Frontend**
- React + Vite

**LLMs**
- **Anthropic API key** → chatbot
- **OpenAI API key** → vision fallback extraction

---

## Repository Structure

```text
PennyWise/
├─ backend/
│  ├─ src/
│  │  └─ receipt_story/
│  │     ├─ api/                 # FastAPI routes (receipts, insights, trends, etc.)
│  │     ├─ core/                # settings/config
│  │     ├─ db/                  # SQLite engine + CRUD + tables
│  │     └─ services/
│  │        ├─ extraction/       # OCR + hybrid extraction pipeline
│  │        ├─ trends.py
│  │        └─ categorize.py
│  ├─ data/
│  │  └─ receipts.db             # local SQLite DB
│  ├─ requirements.txt
│  ├─ .env.example
│  └─ README.md
├─ receipt-ui/
│  ├─ src/
│  ├─ package.json
│  └─ vite.config.*
└─ README.md

```
## Quickstart (Local Development)

**1) Clone the repo**
```
git clone https://github.com/varunsardana/PennyWise.git
cd PennyWise
```

## Backend Setup (FastAPI)

**2) Create a virtual environment**
```
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

**3) Install backend dependencies**
```
pip install -r requirements.txt
```
**4) Create your .env**
```
cp .env.example .env
```
**Open backend/.env and set the keys like this:**
```
# -------------------------
# Core backend config
# -------------------------
EXTRACTION_BACKEND=hybrid
RECEIPT_FORCE_VISION=false

# -------------------------
# Chatbot (Anthropic)
# -------------------------
ANTHROPIC_API_KEY=your_anthropic_key_here

# -------------------------
# Receipt Vision Fallback (OpenAI)
# -------------------------
OPENAI_API_KEY=your_openai_key_here
```

Run the backend (port 8000)

**Run this from inside backend/ (with the venv activated):**
```
uvicorn receipt_story.main:app --app-dir src --host 0.0.0.0 --port 8000
```
**Backend docs:**

http://localhost:8000/docs


## Frontend Setup (React + Vite)

**6) Install frontend dependencies**

Open a new terminal:

```
cd receipt-ui
npm install
```

**7) Run the frontend (usually port 5173)**

```
npm run dev
```

**Frontend will be available at (usually):**

http://localhost:5173

## How Extraction Works

The receipt pipeline supports multiple modes (controlled by ```EXTRACTION_BACKEND```):

```easyocr```→ OCR-only extraction
```hybrid```→ OCR-first extraction + vision fallback when needed

## Vision fallback (OpenAI)

When OCR confidence is low or key fields are missing, the backend can call OpenAI Vision to extract receipt fields more reliably.
Requires:

```OPENAI_API_KEY```

Chatbot (Anthropic)

The chatbot feature uses Anthropic for responses.
Requires:

```ANTHROPIC_API_KEY```

##Useful Commands

**Backend health check**

```curl -s http://localhost:8000/health```

## Test receipt parsing (example)

(Adjust endpoint/field name if your route expects a different form key.)

```curl -s -X POST "http://localhost:8000/receipts/parse" \```
```-F "file=@/path/to/receipt.jpg"```

##Troubleshooting

**“ModuleNotFoundError: receipt_story”**

Make sure you:

are inside ```backend/```

include ```--app-dir src```

**Port 8000 already in use**

```lsof -nP -iTCP:8000 | grep LISTEN```
```kill -9 <PID>```

##Hybrid fallback not triggering

Confirm ```EXTRACTION_BACKEND=hybrid```

Confirm ```OPENAI_API_KEY``` is set

For testing: set ```RECEIPT_FORCE_VISION=true``` (if supported by your backend)

##Contributing / Workflow

-Create a branch from development

-Commit changes

-Open a PR into development












































