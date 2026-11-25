# MicroDrama AI Studio — Developer Handoff & Context Summary

> Use this file when resuming development on a new PC. Tell your AI assistant: **"Read `HANDOFF.md` and continue from Phase 5."**

---

## 1. Current Project Status (v2.0.0 — MVP 100% Complete & Live-Verified)

- **Repository:** `https://github.com/hichamlaachiri/ai_VED` (`main` branch)
- **Phase 1 (Foundation):** FastAPI + SQLite (`aiosqlite` + SQLAlchemy) + Next.js 14 App Router + Tailwind Dark Studio UI + Dockerfiles.
- **Phase 2 (Visual Bible & Director):**
  - `backend/app/services/visual_bible.py`: Nano Banana (`gemini-2.5-flash-image`) 6-anchor generator with true **image-to-image chaining** (Char A/B Portrait &rarr; Full Body; Location Angle A &rarr; Reverse Angle B), Imagen 3 secondary fallback, per-asset regen, manual upload, and `?v=<ts>` cache-busting.
  - `backend/app/services/director.py`: Structured Pydantic `response_schema` via `gemini-2.5-flash` producing 4x15s beats (`Hook`, `Escalation`, `Turn`, `Cliffhanger`), strict 180° spatial blocking (`LEFT`/`RIGHT`), `props_continuity`, exact `dialogue_lines_json` timestamps, and locked-lighting Prompt Compiler.
- **Phase 3 (Gemini Omni Video & Credits):**
  - `backend/app/services/omni_video.py`: Live-verified `gemini-omni-1.2-flash` via `google-genai 2.33.0` Interactions API:
    - `input=[{"type":"text","text":...}, {"type":"image","data":b64,"mime_type":"image/jpeg"}, ...]` (up to 6 Visual Bible anchors)
    - `response_modalities=["video"]`
    - `response_format={"type":"video","aspect_ratio":"9:16","duration":"15s","resolution":"360p"|"720p","delivery":"uri"}` (**IMPORTANT:** `duration` MUST be a string `"15s"`, not int `15`)
    - `generation_config={"video_config":{"task":"reference_to_video"|"edit"}}`
    - Top-level `previous_interaction_id` for Targeted Multi-Turn Fixes
    - Async polling on `poll.status` (`completed`/`failed`), downloading `poll.output_video.uri` with `headers={"x-goog-api-key": api_key}`
    - Prominent-people safety policy rejection catch without deducting credits + 1-click **Reframe Safely & Retry**
    - Non-blocking `BackgroundTasks` (`?async_mode=true`) + frontend 2.5s live polling
  - Billing & `CreditLedger` with interactive modal & top-up in `frontend/components/Navbar.tsx`.
- **Phase 4 (FFmpeg Auto-Assembly):**
  - `backend/app/services/assembler.py`: Uses bundled `imageio-ffmpeg` (no system FFmpeg install required). Normalizes all clips to uniform `9:16` 24fps 44.1kHz stereo, chains real `0.2s` audio crossfades (`acrossfade=d=0.2`), dialogue EQ (`highpass=80,lowpass=12000`), `-22dB` continuous suspense BGM, unified color grade (`eq`), burned centered-bottom SRT subtitles from `dialogue_lines_json`, and a `1.5s` cliffhanger end card.

---

## 2. Setup on the New PC (5 Minutes)

```bash
git clone https://github.com/hichamlaachiri/ai_VED.git
cd ai_VED
```

### Backend
```powershell
python -m venv backend/venv
backend\venv\Scripts\pip install -r backend/requirements.txt
copy backend\.env.example backend\.env
# Edit backend/.env and paste your GEMINI_API_KEY
# Optional: set MOCK_VIDEO_MODE=true for free testing without video API charges
backend\venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

### Frontend
```powershell
cd frontend
npm install
npm run dev
```
- **Frontend:** `http://localhost:3001` (port 3001 avoids conflicts on 3000)
- **Backend Health:** `http://127.0.0.1:8000/health` (verify `"api_mode": "live"`)

### Automated Tests (Zero API Cost)
```powershell
$env:PYTHONPATH="backend"; $env:MOCK_VIDEO_MODE="true"
backend\venv\Scripts\python backend/test_phase2.py
backend\venv\Scripts\python backend/test_phase3.py
backend\venv\Scripts\python backend/test_phase4.py
```

---

## 3. Verified Models Available on API Key
- `gemini-2.5-flash` (Director)
- `gemini-2.5-flash-image` / `gemini-3.1-flash-image` / `gemini-3-pro-image` (Visual Bible / Nano Banana)
- `gemini-omni-1.2-flash` (Video Generation & Multi-Turn Edits)

---

## 4. Next Recommended Phase (Phase 5 — Commercial SaaS Launch)
1. **Authentication:** Multi-user auth (JWT / Supabase / Clerk) replacing default `user_id=1`.
2. **Real Payments:** Stripe Checkout + Webhook to purchase credit packs and auto-credit `CreditLedger`.
3. **Cloud Storage & DB:** Migrate local `storage/` to Cloudflare R2 / AWS S3 and SQLite to PostgreSQL (Neon/Supabase).
4. **Deployment:** Deploy `frontend/` to Vercel and `backend/` (via `backend/Dockerfile`) to Railway / Render / Fly.io.
