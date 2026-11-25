# MicroDrama AI Studio (SaaS)

Full-stack SaaS web application that turns a story premise into a consistent, ready-to-post **60-second vertical (`9:16`) AI Micro-Drama episode** using Google's Gemini API (`gemini-omni-1.2-flash` Interactions API + Nano Banana `gemini-2.5-flash-image`) and an automated FFmpeg post-production pipeline.

## Features
- **Locked Visual Bible (Max 6 Reference Anchors):** Generates `9:16` character portraits, identity-chained full-body anchors, and 2-angle location sets (Angle A Front + Angle B Reverse) with per-asset regenerate & manual upload.
- **4-Beat Script Director (`180°` Spatial Rule):** Structured Gemini JSON output (`Hook`, `Escalation`, `Turn`, `Cliffhanger`) enforcing `LEFT`/`RIGHT` spatial blocking, props continuity, timestamped dialogue, and locked lighting prompt compilation.
- **2-Pass Cost-Optimized Rendering:**
  - **Pass 1 (`360p` Draft — $0.35 / 35 credits per 15s):** Fast blocking & lip-sync review.
  - **Targeted Fix (Multi-Turn Edit):** Refines existing clips via `previous_interaction_id` without regenerating from scratch.
  - **Prominent People Safety Fallback:** Catches likeness rejections without deducting credits and offers 1-click safe reframing.
  - **Pass 2 (`720p` Final — $1.04 / 104 credits per 15s):** High-resolution master clips.
- **SaaS Billing & CreditLedger:** Upfront cost estimator, atomic credit deduction, live balance navbar, and transaction history modal.
- **FFmpeg Auto-Assembly:** Normalizes and concatenates all 4x15s clips with `0.2s` audio crossfades, dialogue EQ, `-22dB` continuous BGM, cinematic color grading, burned `9:16` subtitles, and a `1.5s` cliffhanger end card.

## Quick Start

### 1. Backend (FastAPI + SQLite + FFmpeg)
```bash
cd backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt
copy .env.example .env
# Add your GEMINI_API_KEY inside backend/.env
cd ..
backend\venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend (Next.js 14 App Router + Tailwind CSS)
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3001](http://localhost:3001) (Backend health: [http://localhost:8000/health](http://localhost:8000/health)).

### 3. Docker Compose
```bash
docker-compose up --build
```
