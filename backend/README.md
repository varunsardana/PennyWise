# PennyWise Backend (Receipt Story)

## Run (local)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
uvicorn receipt_story.main:app --reload --app-dir src --host 0.0.0.0 --port 8000
