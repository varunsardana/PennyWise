# PennyWise 💸
**Scan receipts → save expenses → visualize trends & forecasts.**

PennyWise is a lightweight personal finance tracker that lets you:
- 📷 **Scan / upload receipts**
- 🔍 Extract totals, merchant, date, tax, category (OCR-first)
- 🧠 Optionally use a **Vision fallback (OpenAI / Anthropic)** when OCR is weak
- 💾 Store receipts in **SQLite**
- 📈 View **history + trends + simple forecasting** in a clean React dashboard































# PennyWise

# Terminal A

cd backend

# Create venv if it doesn't exist
python3 -m venv .venv

# Activate venv
source .venv/bin/activate

# Upgrade pip (recommended)
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# (Optional) Create backend .env if missing (safe if it already exists)
# This file is ignored by git; teammates can add their keys locally
touch .env

# Run backend
uvicorn receipt_story.main:app --reload --app-dir src --host 127.0.0.1 --port 8000

Verify backend:

Open: http://127.0.0.1:8000/docs


# Terminal B — Run FRONTEND (Vite)

cd /path/to/PennyWise/receipt-ui

# Install frontend deps
npm install

# Create frontend env pointing to backend (Vite reads this)
echo "VITE_API_BASE=http://127.0.0.1:8000" > .env

# Run frontend
npm run dev

 # Optional Add OpenAI key for Vision Fallback (Backend)

If your project supports vision fallback, teammates can add this locally:

In Terminal A (backend), before running uvicorn:
cd backend
source .venv/bin/activate
export OPENAI_API_KEY="PASTE_KEY_HERE"
uvicorn receipt_story.main:app --reload --app-dir src --host 127.0.0.1 --port 8000
