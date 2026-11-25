from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.config import settings
from app.db.database import init_db, AsyncSessionLocal
from app.db.models import User, CreditLedger
from app.routers import series, episodes, shots, billing


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).filter_by(id=1))
        user = result.scalars().first()
        if not user:
            default_user = User(
                id=1,
                email="director@microdrama.studio",
                name="Head Director",
                credits_balance=settings.INITIAL_USER_CREDITS,
            )
            session.add(default_user)
            await session.commit()

            ledger = CreditLedger(
                user_id=1,
                amount=settings.INITIAL_USER_CREDITS,
                balance_after=settings.INITIAL_USER_CREDITS,
                reason="Welcome Bonus: Initial Starter Credits",
                meta_info="System bootstrap",
            )
            session.add(ledger)
            await session.commit()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.0.0",
    description="MicroDrama AI Studio API - 60s Vertical Micro-Drama Generator",
    lifespan=lifespan,
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static media mount
app.mount("/storage", StaticFiles(directory=str(settings.STORAGE_PATH)), name="storage")

# Include Routers
app.include_router(series.router, prefix="/api/series", tags=["Series & Visual Bible"])
app.include_router(episodes.router, prefix="/api/episodes", tags=["Episodes & Scripts"])
app.include_router(shots.router, prefix="/api/shots", tags=["Shots & Video Gen"])
app.include_router(billing.router, prefix="/api/billing", tags=["Credits & Billing"])


@app.get("/health")
async def health_check():
    api_configured = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here")
    return {
        "status": "healthy",
        "version": "2.0.0",
        "service": settings.PROJECT_NAME,
        "env": settings.ENV,
        "storage_path": str(settings.STORAGE_PATH),
        "api_mode": "mock" if (settings.MOCK_VIDEO_MODE or not api_configured) else "live",
        "gemini_key_configured": api_configured,
        "models": {
            "director": settings.DIRECTOR_MODEL,
            "visual_bible": settings.NANO_BANANA_MODEL,
            "omni_video": settings.OMNI_VIDEO_MODEL,
        },
        "rates": {
            "pass1_usd": settings.PASS1_COST_USD,
            "pass2_usd": settings.PASS2_COST_USD,
            "pass1_credits": settings.PASS1_CREDITS,
            "pass2_credits": settings.PASS2_CREDITS,
            "image_credits": settings.IMAGE_GEN_CREDITS,
        },
    }
