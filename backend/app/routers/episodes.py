from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import List, Optional
import datetime

from app.config import settings
from app.db.database import get_db, AsyncSessionLocal
from app.db.models import Episode, Series, Shot, User
from app.services.director import DirectorService
from app.services.omni_video import OmniVideoService
from app.services.assembler import AssemblerService

router = APIRouter()


class ShotSimpleOut(BaseModel):
    id: int
    shot_number: int
    beat_type: str
    duration_sec: int
    camera_angle: str
    camera_movement: str
    spatial_blocking: Optional[str]
    props_continuity: Optional[str] = None
    dialogue: Optional[str]
    dialogue_lines_json: Optional[str] = None
    compiled_prompt: str
    pass1_status: str
    pass1_video_url: Optional[str]
    pass2_status: str
    pass2_video_url: Optional[str]
    previous_interaction_id: Optional[str]
    safety_retry_count: int = 0
    last_error_message: Optional[str] = None
    selected_pass: str
    final_video_url: Optional[str]

    class Config:
        from_attributes = True


class EpisodeOut(BaseModel):
    id: int
    series_id: int
    episode_number: int
    title: str
    premise: str
    outline_summary: Optional[str] = None
    continuity_notes: Optional[str] = None
    status: str
    final_video_url: Optional[str]
    created_at: datetime.datetime
    shots: List[ShotSimpleOut] = []

    class Config:
        from_attributes = True


class EpisodeCreate(BaseModel):
    series_id: int
    title: str
    premise: str
    episode_number: Optional[int] = 1


async def _run_batch_background(episode_id: int, pass_number: int):
    """Background task runner for non-blocking batch renders."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Episode).options(selectinload(Episode.shots)).filter_by(id=episode_id)
        )
        episode = result.scalars().first()
        if not episode:
            return
        for shot in sorted(episode.shots, key=lambda s: s.shot_number):
            try:
                await OmniVideoService.render_shot(shot_id=shot.id, pass_number=pass_number, db=db)
            except Exception as err:
                field = "pass1_status" if pass_number == 1 else "pass2_status"
                setattr(shot, field, "failed")
                shot.last_error_message = str(err)
                await db.commit()


@router.get("/series/{series_id}", response_model=List[EpisodeOut])
async def list_episodes_for_series(series_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Episode)
        .options(selectinload(Episode.shots))
        .filter_by(series_id=series_id)
        .order_by(Episode.episode_number.asc())
    )
    return result.scalars().all()


@router.post("", response_model=EpisodeOut)
async def create_episode(req: EpisodeCreate, db: AsyncSession = Depends(get_db)):
    series_res = await db.execute(select(Series).filter_by(id=req.series_id))
    if not series_res.scalars().first():
        raise HTTPException(status_code=404, detail="Series not found")

    ep = Episode(
        series_id=req.series_id,
        episode_number=req.episode_number or 1,
        title=req.title,
        premise=req.premise,
        status="draft",
    )
    db.add(ep)
    await db.commit()
    await db.refresh(ep)

    result = await db.execute(
        select(Episode).options(selectinload(Episode.shots)).filter_by(id=ep.id)
    )
    return result.scalars().first()


@router.get("/{episode_id}", response_model=EpisodeOut)
async def get_episode(episode_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Episode).options(selectinload(Episode.shots)).filter_by(id=episode_id)
    )
    ep = result.scalars().first()
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    return ep


@router.post("/{episode_id}/auto-direct")
async def auto_direct_episode(episode_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await DirectorService.direct_episode(episode_id, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{episode_id}/render-pass1")
async def render_pass1_batch(
    episode_id: int,
    background_tasks: BackgroundTasks,
    async_mode: bool = False,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Episode).options(selectinload(Episode.shots)).filter_by(id=episode_id)
    )
    episode = result.scalars().first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    if not episode.shots or len(episode.shots) != 4:
        raise HTTPException(status_code=400, detail="Episode must have 4 directed shots before rendering.")

    # Pre-check total batch credits
    user_res = await db.execute(select(User).filter_by(id=1))
    user = user_res.scalars().first()
    needed = 4 * settings.PASS1_CREDITS
    if not user or user.credits_balance < needed:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits: {needed} required for Pass 1 batch, balance is {user.credits_balance if user else 0}.",
        )

    if async_mode:
        for s in episode.shots:
            s.pass1_status = "processing"
        episode.status = "rendering"
        await db.commit()
        background_tasks.add_task(_run_batch_background, episode_id, 1)
        return {"status": "queued", "episode_id": episode_id, "pass": 1}

    rendered_results = []
    for shot in sorted(episode.shots, key=lambda s: s.shot_number):
        try:
            r = await OmniVideoService.render_shot(shot_id=shot.id, pass_number=1, db=db)
            rendered_results.append(r)
        except PermissionError as pe:
            raise HTTPException(status_code=402, detail=str(pe))
        except Exception as err:
            rendered_results.append({"status": "failed", "shot_id": shot.id, "error": str(err)})

    return {"status": "completed", "episode_id": episode_id, "pass": 1, "results": rendered_results}


@router.post("/{episode_id}/render-pass2")
async def render_pass2_batch(
    episode_id: int,
    background_tasks: BackgroundTasks,
    async_mode: bool = False,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Episode).options(selectinload(Episode.shots)).filter_by(id=episode_id)
    )
    episode = result.scalars().first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    if not episode.shots or len(episode.shots) != 4:
        raise HTTPException(status_code=400, detail="Episode must have 4 directed shots before rendering.")

    user_res = await db.execute(select(User).filter_by(id=1))
    user = user_res.scalars().first()
    needed = 4 * settings.PASS2_CREDITS
    if not user or user.credits_balance < needed:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits: {needed} required for Pass 2 batch, balance is {user.credits_balance if user else 0}.",
        )

    if async_mode:
        for s in episode.shots:
            s.pass2_status = "processing"
        episode.status = "rendering"
        await db.commit()
        background_tasks.add_task(_run_batch_background, episode_id, 2)
        return {"status": "queued", "episode_id": episode_id, "pass": 2}

    rendered_results = []
    for shot in sorted(episode.shots, key=lambda s: s.shot_number):
        try:
            r = await OmniVideoService.render_shot(shot_id=shot.id, pass_number=2, db=db)
            rendered_results.append(r)
        except PermissionError as pe:
            raise HTTPException(status_code=402, detail=str(pe))
        except Exception as err:
            rendered_results.append({"status": "failed", "shot_id": shot.id, "error": str(err)})

    return {"status": "completed", "episode_id": episode_id, "pass": 2, "results": rendered_results}


@router.post("/{episode_id}/assemble")
async def assemble_episode_pipeline(episode_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await AssemblerService.assemble_episode(episode_id, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
