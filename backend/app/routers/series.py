from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field
from typing import List, Optional
import datetime
import shutil
from pathlib import Path

from app.db.database import get_db
from app.db.models import Series, Character, Location
from app.services.visual_bible import VisualBibleService, get_series_dir

router = APIRouter()


class CharacterCreate(BaseModel):
    name: str
    role_description: str
    visual_tags: str
    default_screen_position: str = Field(default="LEFT", description="LEFT or RIGHT for 180-deg rule")


class LocationCreate(BaseModel):
    name: str
    visual_tags: str


class SeriesCreate(BaseModel):
    title: str
    premise: str
    genre: Optional[str] = "Micro-Drama Thriller"
    locked_lighting: Optional[str] = (
        "High-contrast cinematic neo-noir lighting, soft warm fill with subtle teal rim lights, 8k shallow depth of field"
    )
    characters: List[CharacterCreate] = Field(default_factory=list)
    location: Optional[LocationCreate] = None


class CharacterOut(BaseModel):
    id: int
    name: str
    role_description: str
    visual_tags: str
    portrait_image_url: Optional[str]
    body_image_url: Optional[str]
    default_screen_position: str

    class Config:
        from_attributes = True


class LocationOut(BaseModel):
    id: int
    name: str
    visual_tags: str
    angle_a_image_url: Optional[str]
    angle_b_image_url: Optional[str]

    class Config:
        from_attributes = True


class EpisodeBriefOut(BaseModel):
    id: int
    episode_number: int
    title: str
    status: str

    class Config:
        from_attributes = True


class SeriesOut(BaseModel):
    id: int
    title: str
    premise: str
    genre: str
    locked_lighting: str
    created_at: datetime.datetime
    characters: List[CharacterOut]
    locations: List[LocationOut]
    episodes: List[EpisodeBriefOut] = []

    class Config:
        from_attributes = True


@router.get("", response_model=List[SeriesOut])
async def list_series(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Series)
        .options(
            selectinload(Series.characters),
            selectinload(Series.locations),
            selectinload(Series.episodes),
        )
        .order_by(Series.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=SeriesOut)
async def create_series(req: SeriesCreate, db: AsyncSession = Depends(get_db)):
    if len(req.characters) > 3:
        raise HTTPException(status_code=400, detail="Strict Consistency Rule: Max 3 characters allowed per Series.")

    new_series = Series(
        user_id=1,
        title=req.title,
        premise=req.premise,
        genre=req.genre or "Micro-Drama Thriller",
        locked_lighting=req.locked_lighting
        or "High-contrast cinematic neo-noir lighting, soft warm fill with subtle teal rim lights, 8k shallow depth of field",
    )
    db.add(new_series)
    await db.flush()

    for idx, c in enumerate(req.characters):
        pos = (c.default_screen_position or ("RIGHT" if idx == 0 else "LEFT")).upper()
        char_obj = Character(
            series_id=new_series.id,
            name=c.name,
            role_description=c.role_description,
            visual_tags=c.visual_tags,
            default_screen_position=pos,
        )
        db.add(char_obj)

    if req.location:
        loc_obj = Location(
            series_id=new_series.id,
            name=req.location.name,
            visual_tags=req.location.visual_tags,
        )
        db.add(loc_obj)

    await db.commit()

    result = await db.execute(
        select(Series)
        .options(
            selectinload(Series.characters),
            selectinload(Series.locations),
            selectinload(Series.episodes),
        )
        .filter_by(id=new_series.id)
    )
    return result.scalars().first()


@router.get("/{series_id}", response_model=SeriesOut)
async def get_series(series_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Series)
        .options(
            selectinload(Series.characters),
            selectinload(Series.locations),
            selectinload(Series.episodes),
        )
        .filter_by(id=series_id)
    )
    series_obj = result.scalars().first()
    if not series_obj:
        raise HTTPException(status_code=404, detail="Series not found")
    return series_obj


@router.delete("/{series_id}")
async def delete_series(series_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Series).filter_by(id=series_id))
    series_obj = result.scalars().first()
    if not series_obj:
        raise HTTPException(status_code=404, detail="Series not found")
    await db.delete(series_obj)
    await db.commit()
    return {"status": "deleted", "series_id": series_id}


class RegenerateAssetRequest(BaseModel):
    asset_type: str  # "char_portrait", "char_body", "loc_angle_a", "loc_angle_b"
    target_id: int


@router.post("/{series_id}/visual-bible/generate-all")
async def generate_all_visual_assets(series_id: int, db: AsyncSession = Depends(get_db)):
    try:
        assets = await VisualBibleService.generate_full_bible(series_id, db)
        return {"status": "success", "assets": assets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{series_id}/visual-bible/regenerate-asset")
async def regenerate_single_asset(
    series_id: int,
    req: RegenerateAssetRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Series)
        .options(selectinload(Series.characters), selectinload(Series.locations))
        .filter_by(id=series_id)
    )
    series = result.scalars().first()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    new_url = None
    if req.asset_type == "char_portrait":
        char = next((c for c in series.characters if c.id == req.target_id), None)
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")
        new_url = await VisualBibleService.generate_character_portrait(series, char, db)

    elif req.asset_type == "char_body":
        char = next((c for c in series.characters if c.id == req.target_id), None)
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")
        new_url = await VisualBibleService.generate_character_body(series, char, db)

    elif req.asset_type == "loc_angle_a":
        loc = next((l for l in series.locations if l.id == req.target_id), None)
        if not loc:
            raise HTTPException(status_code=404, detail="Location not found")
        new_url = await VisualBibleService.generate_location_angle_a(series, loc, db)

    elif req.asset_type == "loc_angle_b":
        loc = next((l for l in series.locations if l.id == req.target_id), None)
        if not loc:
            raise HTTPException(status_code=404, detail="Location not found")
        new_url = await VisualBibleService.generate_location_angle_b(series, loc, db)

    else:
        raise HTTPException(status_code=400, detail="Invalid asset_type")

    return {"status": "success", "asset_type": req.asset_type, "url": new_url}


@router.post("/{series_id}/visual-bible/upload-asset")
async def upload_asset_manually(
    series_id: int,
    asset_type: str = Form(...),
    target_id: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Series)
        .options(selectinload(Series.characters), selectinload(Series.locations))
        .filter_by(id=series_id)
    )
    series = result.scalars().first()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    series_dir = get_series_dir(series.id)
    ext = Path(file.filename or "image.jpg").suffix or ".jpg"
    ts = int(datetime.datetime.utcnow().timestamp())
    filename = f"{asset_type}_{target_id}_{ts}{ext}"
    filepath = series_dir / filename

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    url = f"/storage/series_{series.id}/{filename}?v={ts}"

    if asset_type == "char_portrait":
        char = next((c for c in series.characters if c.id == target_id), None)
        if char:
            char.portrait_image_url = url
    elif asset_type == "char_body":
        char = next((c for c in series.characters if c.id == target_id), None)
        if char:
            char.body_image_url = url
    elif asset_type == "loc_angle_a":
        loc = next((l for l in series.locations if l.id == target_id), None)
        if loc:
            loc.angle_a_image_url = url
    elif asset_type == "loc_angle_b":
        loc = next((l for l in series.locations if l.id == target_id), None)
        if loc:
            loc.angle_b_image_url = url

    await db.commit()
    return {"status": "success", "asset_type": asset_type, "url": url}
