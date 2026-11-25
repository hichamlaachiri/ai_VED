import base64
import logging
import time
import asyncio
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.models import Shot, Episode, Series, User, CreditLedger

logger = logging.getLogger("uvicorn.error")

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = "ffmpeg"

try:
    from google import genai
except ImportError:
    genai = None


SAFETY_ERROR_KEYWORDS = (
    "prominent",
    "likeness",
    "celebrity",
    "public figure",
    "safety",
    "policy",
    "blocked",
    "prohibited",
)


def strip_query(url: Optional[str]) -> str:
    if not url:
        return ""
    return url.split("?", 1)[0]


def get_shot_storage_dir(series_id: int, episode_id: int) -> Path:
    shot_dir = settings.STORAGE_PATH / f"series_{series_id}" / f"ep_{episode_id}"
    shot_dir.mkdir(parents=True, exist_ok=True)
    return shot_dir


def generate_mock_video(
    output_path: Path,
    title: str,
    pass_name: str,
    resolution: str,  # "360p" or "720p"
    duration_sec: int = 15,
) -> bool:
    """Generates a valid 9:16 MP4 video clip with audio stream using bundled ffmpeg for testing & dev mode."""
    width, height = (360, 640) if resolution == "360p" else (720, 1280)
    fontsize = 22 if resolution == "360p" else 44

    safe_title = title.replace("'", "").replace(":", "-")[:35]
    drawtext = (
        f"drawtext=text='{safe_title}':fontcolor=white:fontsize={fontsize}:x=(w-text_w)/2:y=h/3,"
        f"drawtext=text='{pass_name} - {resolution} (9\\:16)':fontcolor=0xF59E0B:fontsize={fontsize//2}:x=(w-text_w)/2:y=h/3+60,"
        f"drawtext=text='%{{pts\\:hms}}':fontcolor=0x94A3B8:fontsize={fontsize//2}:x=(w-text_w)/2:y=h*0.7"
    )

    cmd = [
        FFMPEG_EXE, "-y",
        "-f", "lavfi", "-i", f"color=c=0x0E111B:s={width}x{height}:d={duration_sec}:r=24",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-vf", drawtext,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(duration_sec),
        str(output_path),
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except Exception as e:
        print(f"[OmniVideo] Mock video drawtext fallback: {e}")
        simple_cmd = [
            FFMPEG_EXE, "-y",
            "-f", "lavfi", "-i", f"color=c=0x0E111B:s={width}x{height}:d={duration_sec}:r=24",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
            "-c:a", "aac",
            "-t", str(duration_sec),
            str(output_path),
        ]
        subprocess.run(simple_cmd, capture_output=True, check=True)
        return True


def collect_reference_anchors(series: Series, shot: Shot) -> List[Path]:
    """Collects up to 6 Visual Bible reference images for the shot (Char A/B Portrait+Body + matching Location Angle)."""
    anchors: List[Path] = []

    for char in series.characters[:2]:
        for raw_url in (char.portrait_image_url, char.body_image_url):
            clean = strip_query(raw_url)
            if clean:
                p_path = settings.STORAGE_PATH.parent / clean.lstrip("/")
                if p_path.exists():
                    anchors.append(p_path)

    if series.locations:
        loc = series.locations[0]
        is_angle_b = "angle b" in (shot.camera_angle or "").lower() or "reverse" in (shot.camera_angle or "").lower()
        ordered_urls = (
            [loc.angle_b_image_url, loc.angle_a_image_url]
            if is_angle_b
            else [loc.angle_a_image_url, loc.angle_b_image_url]
        )
        for raw_url in ordered_urls:
            clean = strip_query(raw_url)
            if clean:
                l_path = settings.STORAGE_PATH.parent / clean.lstrip("/")
                if l_path.exists():
                    anchors.append(l_path)

    return anchors[:6]


def _is_safety_rejection(msg: str) -> bool:
    low = (msg or "").lower()
    return any(k in low for k in SAFETY_ERROR_KEYWORDS)


class OmniVideoService:

    @classmethod
    async def render_shot(
        cls,
        shot_id: int,
        pass_number: int,  # 1 (360p) or 2 (720p)
        db: AsyncSession,
        edit_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes Pass 1 (360p) or Pass 2 (720p) rendering via Gemini Omni 1.2 Flash Interactions API or mock pipeline."""
        result = await db.execute(
            select(Shot)
            .options(
                selectinload(Shot.episode).selectinload(Episode.series).selectinload(Series.characters),
                selectinload(Shot.episode).selectinload(Episode.series).selectinload(Series.locations),
            )
            .filter_by(id=shot_id)
        )
        shot = result.scalars().first()
        if not shot:
            raise ValueError(f"Shot {shot_id} not found")

        episode = shot.episode
        series = episode.series
        resolution = "360p" if pass_number == 1 else "720p"
        cost_credits = settings.PASS1_CREDITS if pass_number == 1 else settings.PASS2_CREDITS
        pass_field_status = "pass1_status" if pass_number == 1 else "pass2_status"
        pass_field_url = "pass1_video_url" if pass_number == 1 else "pass2_video_url"

        # 1. Billing Pre-check
        user_res = await db.execute(select(User).filter_by(id=1))
        user = user_res.scalars().first()
        if not user or user.credits_balance < cost_credits:
            raise PermissionError(
                f"Insufficient credits: {cost_credits} required, balance is {user.credits_balance if user else 0}."
            )

        setattr(shot, pass_field_status, "processing")
        shot.last_error_message = None
        await db.commit()

        target_dir = get_shot_storage_dir(series.id, episode.id)
        ts = int(time.time())
        filename = f"shot_{shot.id}_pass{pass_number}_{ts}.mp4"
        output_file = target_dir / filename
        video_url = f"/storage/series_{series.id}/ep_{episode.id}/{filename}?v={ts}"

        prompt_to_use = shot.compiled_prompt
        if edit_instruction:
            prompt_to_use = f"{shot.compiled_prompt}. Targeted Edit: {edit_instruction}"

        # 2. Local Pre-Flight Prominent People Safety Guard (zero credits deducted)
        flagged_keywords = ["elon musk", "taylor swift", "donald trump", "barack obama"]
        if any(k in prompt_to_use.lower() for k in flagged_keywords):
            setattr(shot, pass_field_status, "failed")
            shot.last_error_message = (
                "Safety Policy Violation: Prominent people likeness detected. Reframe safely."
            )
            await db.commit()
            return {
                "status": "safety_violation",
                "message": shot.last_error_message,
                "can_reframe": True,
                "shot_id": shot.id,
            }

        # 3. Live Gemini Omni 1.2 Flash Interactions API (google-genai 2.33.0 contract) or Mock Mode
        api_key = settings.GEMINI_API_KEY
        use_mock = (
            settings.MOCK_VIDEO_MODE
            or not api_key
            or api_key == "your_gemini_api_key_here"
            or genai is None
        )
        interaction_id: Optional[str] = None

        if not use_mock:
            try:
                client = genai.Client(api_key=api_key)
                reference_anchors = collect_reference_anchors(series, shot)

                input_items: List[Dict[str, Any]] = [{"type": "text", "text": prompt_to_use}]
                for p in reference_anchors:
                    if p.exists():
                        b64_data = base64.b64encode(p.read_bytes()).decode("ascii")
                        input_items.append(
                            {
                                "type": "image",
                                "data": b64_data,
                                "mime_type": "image/jpeg",
                            }
                        )

                task_type = "edit" if (edit_instruction and shot.previous_interaction_id) else (
                    "reference_to_video" if reference_anchors else "text_to_video"
                )

                create_kwargs: Dict[str, Any] = {
                    "model": settings.OMNI_VIDEO_MODEL,
                    "input": input_items,
                    "response_modalities": ["video"],
                    "response_format": {
                        "type": "video",
                        "aspect_ratio": "9:16",
                        "duration": "15s",
                        "resolution": resolution,
                        "delivery": "uri",
                    },
                    "generation_config": {
                        "video_config": {
                            "task": task_type,
                        }
                    },
                    "background": True,
                }
                if edit_instruction and shot.previous_interaction_id:
                    create_kwargs["previous_interaction_id"] = shot.previous_interaction_id

                logger.info(
                    f"[OmniVideo] Starting live {settings.OMNI_VIDEO_MODEL} render: "
                    f"shot={shot.id}, pass={pass_number} ({resolution}), task={task_type}, anchors={len(reference_anchors)}"
                )
                resp = await asyncio.to_thread(client.interactions.create, **create_kwargs)
                interaction_id = getattr(resp, "id", None)
                logger.info(f"[OmniVideo] Created interaction {interaction_id} (status={getattr(resp, 'status', None)})")

                # Poll until completed or failed
                max_polls = 120  # up to ~6 minutes
                poll_obj = resp
                for _ in range(max_polls):
                    status_val = str(getattr(poll_obj, "status", "in_progress")).lower()
                    if status_val == "completed":
                        break
                    if status_val in ("failed", "cancelled", "incomplete", "budget_exceeded"):
                        err_list = getattr(poll_obj, "errors", None) or []
                        err_text = "; ".join(str(e) for e in err_list) or f"Interaction ended with status: {status_val}"
                        if _is_safety_rejection(err_text):
                            setattr(shot, pass_field_status, "failed")
                            shot.last_error_message = f"Safety Policy Violation: {err_text}"
                            await db.commit()
                            return {
                                "status": "safety_violation",
                                "message": shot.last_error_message,
                                "can_reframe": True,
                                "shot_id": shot.id,
                            }
                        raise RuntimeError(err_text)
                    await asyncio.sleep(3)
                    poll_obj = await asyncio.to_thread(client.interactions.get, interaction_id)

                # Extract video URI or inline bytes from poll_obj.output_video
                out_vid = getattr(poll_obj, "output_video", None)
                downloaded = False
                if out_vid:
                    vid_uri = getattr(out_vid, "uri", None)
                    vid_data = getattr(out_vid, "data", None)
                    if vid_uri:
                        logger.info(f"[OmniVideo] Downloading rendered MP4 from URI for shot={shot.id}...")
                        async with httpx.AsyncClient(timeout=180.0, follow_redirects=True) as hclient:
                            r = await hclient.get(vid_uri, headers={"x-goog-api-key": api_key})
                            r.raise_for_status()
                            output_file.write_bytes(r.content)
                            downloaded = True
                            logger.info(f"[OmniVideo] Downloaded {len(r.content)} bytes to {output_file.name}")
                    elif vid_data:
                        raw_bytes = base64.b64decode(vid_data) if isinstance(vid_data, str) else vid_data
                        output_file.write_bytes(raw_bytes)
                        downloaded = True

                if not downloaded:
                    raise RuntimeError("Gemini Omni interaction completed without output_video payload.")

            except Exception as api_err:
                err_str = str(api_err)
                logger.error(f"[OmniVideo] Live API error on shot {shot.id}: {err_str}")
                setattr(shot, pass_field_status, "failed")
                if _is_safety_rejection(err_str):
                    shot.last_error_message = f"Safety Policy Violation: {err_str}"
                    await db.commit()
                    return {
                        "status": "safety_violation",
                        "message": shot.last_error_message,
                        "can_reframe": True,
                        "shot_id": shot.id,
                    }
                # Never silently charge credits for a mock placeholder in LIVE mode!
                shot.last_error_message = f"Gemini Omni API Error: {err_str}"
                await db.commit()
                raise RuntimeError(shot.last_error_message)

        if use_mock:
            title_label = f"Shot {shot.shot_number}: {shot.beat_type}"
            pass_label = f"Pass {pass_number}"
            await asyncio.to_thread(
                generate_mock_video,
                output_file,
                title_label,
                pass_label,
                resolution,
                15,
            )
            interaction_id = f"mock_interaction_{shot.id}_pass{pass_number}_{ts}"

        # 4. Atomic Credit Deduction on Success
        user.credits_balance -= cost_credits
        action_label = "Targeted Edit" if edit_instruction else f"Render Pass {pass_number}"
        ledger = CreditLedger(
            user_id=user.id,
            amount=-cost_credits,
            balance_after=user.credits_balance,
            reason=f"{action_label} ({resolution}) - Shot {shot.shot_number}",
            meta_info=f"Episode #{episode.episode_number}, Shot ID {shot.id}",
        )
        db.add(ledger)

        # 5. Update Shot record
        setattr(shot, pass_field_status, "completed")
        setattr(shot, pass_field_url, video_url)
        shot.previous_interaction_id = interaction_id
        if pass_number == 1 and not shot.pass2_video_url:
            shot.final_video_url = video_url
            shot.selected_pass = "pass1"
        elif pass_number == 2:
            shot.final_video_url = video_url
            shot.selected_pass = "pass2"

        # Update Episode status
        all_shots_res = await db.execute(select(Shot).filter_by(episode_id=episode.id))
        all_shots = all_shots_res.scalars().all()
        if all(s.pass2_status == "completed" for s in all_shots):
            episode.status = "pass2_rendered"
        elif all(s.pass1_status == "completed" for s in all_shots):
            episode.status = "pass1_rendered"

        await db.commit()

        return {
            "status": "completed",
            "shot_id": shot.id,
            "pass_number": pass_number,
            "resolution": resolution,
            "video_url": video_url,
            "interaction_id": interaction_id,
            "credits_deducted": cost_credits,
            "balance_remaining": user.credits_balance,
            "mode": "mock" if use_mock else "live",
        }

    @classmethod
    async def reframe_safely_and_retry(cls, shot_id: int, db: AsyncSession) -> Dict[str, Any]:
        """Automatically reframes a shot that hit prominent-people safety policy into OTS / hands / profile framing."""
        result = await db.execute(select(Shot).filter_by(id=shot_id))
        shot = result.scalars().first()
        if not shot:
            raise ValueError(f"Shot {shot_id} not found")

        safe_prefix = (
            "9:16 vertical over-the-shoulder framing from behind the figure, cinematic side-profile silhouette "
            "with soft rim lighting, focusing on expressive hands, posture, and scene props with no direct facial likeness."
        )
        shot.compiled_prompt = (
            f"{safe_prefix} Continuity context: {shot.spatial_blocking}. "
            f"NO background music, NO soundtrack, quiet room tone and realistic dialogue only, no text, no cuts."
        )
        shot.safety_retry_count += 1
        shot.last_error_message = None
        await db.commit()

        return await cls.render_shot(shot_id=shot.id, pass_number=1, db=db)
