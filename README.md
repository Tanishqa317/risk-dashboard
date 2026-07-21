# SafeMate

**Watching over every shift.**

SafeMate is an AI-powered industrial plant safety command center. It treats a plant like a patient under continuous monitoring — real-time risk scoring, multi-agent AI consensus, predictive failure fingerprinting, and tamper-evident audit trails, all built on a live FastAPI backend and a React/TypeScript frontend.

## Features

| Feature | Description |
|---|---|
| **Core Vitals Dashboard** | Live risk scoring across 5 plant units via a Gemini-powered Correlation Engine + Cost-of-Risk Translator |
| **Oracle Swarm** | Three adversarial AI agents (Aggressive / Conservative / Adversarial) independently assess risk and reach consensus |
| **Vibration DNA Fingerprinting** | Predictive failure detection by comparing live vibration signatures against healthy baselines |
| **Swiss Cheese Layered Scan** | Visualizes overlapping safety-layer weaknesses (permits, guardrails, staffing) |
| **Counterfactual Replay Engine** | Replays historical incident timelines against a counterfactual "what if this safeguard hadn't caught it" scenario |
| **Evacuation Map & Rerouting** | Live evacuation path optimization around real-time danger zones |
| **Alarm Fatigue Compensator** | Folds low-priority alert floods into a single actionable summary |
| **Evidence Chain of Custody** | SHA-256 hash-chained, tamper-evident audit ledger |
| **Compliance Audit Agent** | RAG-based regulatory anomaly detection with corrective actions and citations |

## Architecture
frontend/ React + TypeScript + Vite + Tailwind + Framer Motion
backend/ FastAPI + Google Gemini (gemini-flash-latest)
data/ Synthetic + real (AI4I 2020) sensor dataset, plant layout, permits
The backend calls the Gemini API for risk reasoning and includes a caching + fallback layer: if Gemini is rate-limited or unavailable, previously-captured real responses are served automatically so the app degrades gracefully rather than failing.

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- A Gemini API key ([get one here](https://aistudio.google.com/apikey))

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env          # then add your GEMINI_API_KEY
uvicorn app.main:app --reload
```
Backend runs at `http://127.0.0.1:8000` — API docs at `http://127.0.0.1:8000/docs`.

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at `http://localhost:5173`.

## Data

`data/combined_dataset.csv` merges the [AI4I 2020 Predictive Maintenance dataset](https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset) (UCI) with synthetically generated permits, shift schedules, and plant layout, to simulate a realistic industrial monitoring environment.

## Team

Built during ET National Hackathon by Model Minds .
Team Members - 
Tanishqa Shetkar 
Divya Chaudhari

## License

MIT