# PennyWise Backend (Receipt Story)
Aliza Samad

# Created by Varun Sardana, Aliza Samad, Nikita Sharma, Rohil Jain
# An app to make today's spenders into tomorrow's savers

## Run (local)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
uvicorn receipt_story.main:app --reload --app-dir src --host 0.0.0.0 --port 8000
