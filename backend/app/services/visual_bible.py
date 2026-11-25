import asyncio
import io
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from PIL import Image as PILImage, ImageDraw

logger = logging.getLogger("uvicorn.error")
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.models import Series, Character, Location

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


def get_series_dir(series_id: int) -> Path:
    series_dir = settings.STORAGE_PATH / f"series_{series_id}"
    series_dir.mkdir(parents=True, exist_ok=True)
    return series_dir


def create_cinematic_fallback_card(
    title: str,
    subtitle: str,
    details: str,
    accent_color: tuple = (245, 158, 11),
    output_path: Optional[Path] = None,
) -> Optional[Path]:
    """Creates a high-contrast cinematic 9:16 visual anchor card when API key is offline or in mock mode."""
    width, height = 720, 1280
    img = PILImage.new("RGB", (width, height), color=(12, 14, 20))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        factor = y / height
        r = int(12 + (accent_color[0] * 0.16 * factor))
        g = int(14 + (accent_color[1] * 0.16 * factor))
        b = int(20 + (accent_color[2] * 0.26 * factor))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    draw.rectangle([40, 40, width - 40, height - 40], outline=(45, 55, 78), width=2)
    draw.rectangle([60, 60, 270, 100], fill=(20, 24, 36), outline=(65, 75, 100))
    draw.text((75, 72), "NANO BANANA 9:16 ANCHOR", fill=(245, 158, 11))

    box_top, box_bottom = 220, 1020
    draw.rectangle([80, box_top, width - 80, box_bottom], outline=(60, 70, 95), width=2)

    draw.line([(width // 2 - 30, height // 2), (width // 2 + 30, height // 2)], fill=(100, 116, 139), width=2)
    draw.line([(width // 2, height // 2 - 30), (width // 2, height // 2 + 30)], fill=(100, 116, 139), width=2)

    draw.text((100, box_top + 40), title.upper()[:40], fill=(255, 255, 255))
    draw.text((100, box_top + 80), subtitle[:48], fill=(245, 158, 11))

    words = details.split()
    lines = []
    current_line = []
    for w in words:
        current_line.append(w)
        if len(" ".join(current_line)) > 36:
            lines.append(" ".join(current_line))
            current_line = []
    if current_line:
        lines.append(" ".join(current_line))

    y_text = box_top + 140
    for line in lines[:10]:
        draw.text((100, y_text), line, fill=(185, 195, 210))
        y_text += 32

    draw.text((100, box_bottom - 60), "LOCKED VISUAL ANCHOR • CONSISTENCY BIBLE", fill=(148, 163, 184))

    if output_path:
        img.save(output_path, "JPEG", quality=92)
    return output_path


async def generate_image_with_gemini(
    prompt: str,
    output_path: Path,
    reference_image_path: Optional[Path] = None,
    aspect_ratio: str = "9:16",
) -> Tuple[bool, Optional[str]]:
    """
    Generates a 9:16 Visual Bible anchor via google-genai SDK:
    1. Primary: Nano Banana multimodal image generation (`gemini-2.5-flash-image`), supporting
       true image-to-image chaining when `reference_image_path` is provided.
    2. Secondary fallback: Imagen 3 (`imagen-3.0-generate-002`).
    Returns (success, error_message_if_failed).
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key == "your_gemini_api_key_here" or genai is None or settings.MOCK_VIDEO_MODE:
        return False, "API key missing or MOCK_VIDEO_MODE enabled"

    last_err: Optional[str] = None
    try:
        client = genai.Client(api_key=api_key)

        # 1. Primary: Nano Banana (supports native image-to-image chaining!)
        try:
            contents = []
            if reference_image_path and reference_image_path.exists():
                ref_img = PILImage.open(reference_image_path).convert("RGB")
                contents.append(ref_img)
            contents.append(prompt)

            cfg_kwargs: Dict[str, Any] = {"response_modalities": ["IMAGE"]}
            if hasattr(types, "ImageConfig"):
                cfg_kwargs["image_config"] = types.ImageConfig(aspect_ratio=aspect_ratio)

            resp = await asyncio.to_thread(
                client.models.generate_content,
                model=settings.NANO_BANANA_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(**cfg_kwargs),
            )
            if resp.candidates:
                for part in resp.candidates[0].content.parts:
                    if getattr(part, "inline_data", None) and part.inline_data.data:
                        img = PILImage.open(io.BytesIO(part.inline_data.data)).convert("RGB")
                        img.save(output_path, "JPEG", quality=92)
                        return True, None
            last_err = f"Nano Banana returned no image parts (candidates={len(resp.candidates or [])})"
            logger.warning(f"[VisualBible] {last_err}")
        except Exception as nb_err:
            last_err = f"Nano Banana ({settings.NANO_BANANA_MODEL}) error: {nb_err}"
            logger.warning(f"[VisualBible] {last_err}")

        # 2. Secondary: Imagen 3 fallback
        try:
            result = await asyncio.to_thread(
                client.models.generate_images,
                model=settings.IMAGEN_FALLBACK_MODEL,
                prompt=prompt,
                config=dict(
                    number_of_images=1,
                    aspect_ratio=aspect_ratio,
                    output_mime_type="image/jpeg",
                ),
            )
            if result.generated_images:
                img_bytes = result.generated_images[0].image.image_bytes
                with open(output_path, "wb") as f:
                    f.write(img_bytes)
                return True, None
        except Exception as im_err:
            last_err = f"{last_err} | Imagen fallback error: {im_err}"
            logger.warning(f"[VisualBible] Imagen fallback notice: {im_err}")

    except Exception as exc:
        last_err = f"GenAI client error: {exc}"
        logger.warning(f"[VisualBible] {last_err}")

    return False, last_err


class VisualBibleService:

    @classmethod
    async def generate_character_portrait(
        cls,
        series: Series,
        character: Character,
        db: AsyncSession,
    ) -> str:
        series_dir = get_series_dir(series.id)
        filename = f"char_{character.id}_portrait.jpg"
        filepath = series_dir / filename

        prompt = (
            f"Cinematic close-up portrait, 9:16 vertical orientation, eye-level, neutral studio film backdrop. "
            f"Character: {character.name}, {character.role_description}. "
            f"Visual identity details: {character.visual_tags}. "
            f"Lighting: {series.locked_lighting}. "
            f"Hyper-detailed facial features, 8k, photorealistic, professional cinema still, no text."
        )

        success, _ = await generate_image_with_gemini(prompt, filepath)
        if not success:
            create_cinematic_fallback_card(
                title=f"{character.name} - Portrait",
                subtitle=f"Role: {character.role_description} ({character.default_screen_position})",
                details=f"{character.visual_tags}\nLighting: {series.locked_lighting}",
                accent_color=(245, 158, 11),
                output_path=filepath,
            )

        character.portrait_image_url = f"/storage/series_{series.id}/{filename}?v={int(time.time())}"
        await db.commit()
        return character.portrait_image_url

    @classmethod
    async def generate_character_body(
        cls,
        series: Series,
        character: Character,
        db: AsyncSession,
    ) -> str:
        series_dir = get_series_dir(series.id)
        filename = f"char_{character.id}_body.jpg"
        filepath = series_dir / filename
        portrait_path = series_dir / f"char_{character.id}_portrait.jpg"

        prompt = (
            f"Full-length head-to-toe standing character reference photo, 9:16 vertical orientation. "
            f"STRICTLY preserve the exact face, hairstyle, age, and likeness of the person in the reference image. "
            f"Character: {character.name}, {character.role_description}. "
            f"Wardrobe & props: {character.visual_tags}. "
            f"Lighting: {series.locked_lighting}. "
            f"Photorealistic cinema costume test still, no text."
        )

        success, _ = await generate_image_with_gemini(
            prompt=prompt,
            output_path=filepath,
            reference_image_path=portrait_path if portrait_path.exists() else None,
        )
        if not success:
            create_cinematic_fallback_card(
                title=f"{character.name} - Full Body",
                subtitle=f"Identity-Locked from Portrait ({character.default_screen_position})",
                details=f"{character.visual_tags}\nFull wardrobe & standing posture.\nLighting: {series.locked_lighting}",
                accent_color=(59, 130, 246),
                output_path=filepath,
            )

        character.body_image_url = f"/storage/series_{series.id}/{filename}?v={int(time.time())}"
        await db.commit()
        return character.body_image_url

    @classmethod
    async def generate_location_angle_a(
        cls,
        series: Series,
        location: Location,
        db: AsyncSession,
    ) -> str:
        series_dir = get_series_dir(series.id)
        filename = f"loc_{location.id}_angle_a.jpg"
        filepath = series_dir / filename

        prompt = (
            f"Cinematic location establishing shot, Front View Angle A, 9:16 vertical composition. "
            f"Location: {location.name}. Architecture & details: {location.visual_tags}. "
            f"Lighting: {series.locked_lighting}. "
            f"Empty film set with zero people, high dynamic range, crisp architecture, cinema production still, no text."
        )

        success, _ = await generate_image_with_gemini(prompt, filepath)
        if not success:
            create_cinematic_fallback_card(
                title=f"{location.name} - Angle A (Front)",
                subtitle="Master Location Establishing View",
                details=f"{location.visual_tags}\nLocked lighting: {series.locked_lighting}",
                accent_color=(16, 185, 129),
                output_path=filepath,
            )

        location.angle_a_image_url = f"/storage/series_{series.id}/{filename}?v={int(time.time())}"
        await db.commit()
        return location.angle_a_image_url

    @classmethod
    async def generate_location_angle_b(
        cls,
        series: Series,
        location: Location,
        db: AsyncSession,
    ) -> str:
        series_dir = get_series_dir(series.id)
        filename = f"loc_{location.id}_angle_b.jpg"
        filepath = series_dir / filename
        angle_a_path = series_dir / f"loc_{location.id}_angle_a.jpg"

        prompt = (
            f"Reverse Angle B (180-degree opposite camera view) of the EXACT same room shown in the reference image, 9:16 vertical. "
            f"Looking back toward the opposite wall and entry door of {location.name}. "
            f"Maintain identical wall materials, floor reflections, color palette, and set dressing from Angle A. "
            f"Lighting: {series.locked_lighting}. Empty film set, zero people, no text."
        )

        success, _ = await generate_image_with_gemini(
            prompt=prompt,
            output_path=filepath,
            reference_image_path=angle_a_path if angle_a_path.exists() else None,
        )
        if not success:
            create_cinematic_fallback_card(
                title=f"{location.name} - Angle B (Reverse)",
                subtitle="180-Degree Reverse Wall / Door View",
                details=f"Chained from Angle A materials & lighting.\n{location.visual_tags}",
                accent_color=(168, 85, 247),
                output_path=filepath,
            )

        location.angle_b_image_url = f"/storage/series_{series.id}/{filename}?v={int(time.time())}"
        await db.commit()
        return location.angle_b_image_url

    @classmethod
    async def generate_full_bible(cls, series_id: int, db: AsyncSession) -> Dict[str, Any]:
        """Generates up to 6 locked visual assets (Char A Portrait+Body, Char B Portrait+Body, Location Angle A+B)."""
        result = await db.execute(
            select(Series)
            .options(selectinload(Series.characters), selectinload(Series.locations))
            .filter_by(id=series_id)
        )
        series = result.scalars().first()
        if not series:
            raise ValueError(f"Series {series_id} not found")

        generated_assets: Dict[str, str] = {}

        # 1. Primary 2 Characters (Portrait -> chained Full Body)
        chars = series.characters[:2]
        for c in chars:
            p_url = await cls.generate_character_portrait(series, c, db)
            b_url = await cls.generate_character_body(series, c, db)
            generated_assets[f"char_{c.id}_portrait"] = p_url
            generated_assets[f"char_{c.id}_body"] = b_url

        # 2. Primary Location (Angle A -> chained Reverse Angle B)
        if series.locations:
            loc = series.locations[0]
            a_url = await cls.generate_location_angle_a(series, loc, db)
            b_url = await cls.generate_location_angle_b(series, loc, db)
            generated_assets[f"loc_{loc.id}_angle_a"] = a_url
            generated_assets[f"loc_{loc.id}_angle_b"] = b_url

        return generated_assets
