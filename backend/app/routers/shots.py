from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional

from app.db.database import get_db
from app.db.models import Shot, Episode
from app.config import settings
from app.services.omni_video import OmniVideoService

router = APIRouter()

class ShotUpdate(BaseModel):
    compiled_prompt: Optional[str] = None
    dialogue: Optional[str] = None
    spatial_blocking: Optional[str] = None
    selected_pass: Optional[str] = None

class RenderShotRequest(BaseModel):
    pass_number: int = 1  # 1 (360p) or 2 (720p)

class EditShotRequest(BaseModel):
    edit_instruction: str

class CostEstimateResponse(BaseModel):
    shot_count: int
    duration_total_sec: int
    pass1_cost_usd: float
    pass1_credits: int
    pass2_cost_usd: float
    pass2_credits: int
    full_pipeline_usd: float
    full_pipeline_credits: int

@router.get("/estimate", response_model=CostEstimateResponse)
async def get_render_estimate(shot_count: int = 4):
    p1_usd = round(shot_count * settings.PASS1_COST_USD, 2)
    p2_usd = round(shot_count * settings.PASS2_COST_USD, 2)
    p1_cred = shot_count * settings.PASS1_CREDITS
    p2_cred = shot_count * settings.PASS2_CREDITS
    return CostEstimateResponse(
        shot_count=shot_count,
        duration_total_sec=shot_count * 15,
        pass1_cost_usd=p1_usd,
        pass1_credits=p1_cred,
        pass2_cost_usd=p2_usd,
        pass2_credits=p2_cred,
        full_pipeline_usd=round(p1_usd + p2_usd, 2),
        full_pipeline_credits=p1_cred + p2_cred
    )

@router.patch("/{shot_id}")
async def update_shot(shot_id: int, req: ShotUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Shot).filter_by(id=shot_id))
    shot = result.scalars().first()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")
    
    if req.compiled_prompt is not None:
        shot.compiled_prompt = req.compiled_prompt
    if req.dialogue is not None:
        shot.dialogue = req.dialogue
    if req.spatial_blocking is not None:
        shot.spatial_blocking = req.spatial_blocking
    if req.selected_pass is not None:
        shot.selected_pass = req.selected_pass
        
    await db.commit()
    await db.refresh(shot)
    return shot

@router.post("/{shot_id}/render")
async def render_single_shot(
    shot_id: int,
    req: RenderShotRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await OmniVideoService.render_shot(
            shot_id=shot_id,
            pass_number=req.pass_number,
            db=db
        )
        return result
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{shot_id}/edit")
async def edit_single_shot(
    shot_id: int,
    req: EditShotRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await OmniVideoService.render_shot(
            shot_id=shot_id,
            pass_number=1,  # Targeted fixes run on pass 1 draft first
            db=db,
            edit_instruction=req.edit_instruction
        )
        return result
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{shot_id}/reframe-safety")
async def reframe_safety_and_retry(
    shot_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await OmniVideoService.reframe_safely_and_retry(shot_id=shot_id, db=db)
        return result
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
