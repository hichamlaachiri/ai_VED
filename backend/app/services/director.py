import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.models import Episode, Series, Shot, Character, Location

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


# Structured Output Schemas for Gemini
class DialogueLineSchema(BaseModel):
    speaker: str
    text: str
    start_sec: float = Field(ge=0.0, le=15.0)
    end_sec: float = Field(ge=0.0, le=15.0)


class DirectedShotSchema(BaseModel):
    shot_number: int = Field(ge=1, le=4)
    beat_name: str
    camera_angle: str
    camera_movement: str
    spatial_blocking: str
    props_continuity: str
    dialogue_lines: List[DialogueLineSchema]
    raw_prompt: str


class DirectorScriptSchema(BaseModel):
    outline_summary: str
    continuity_notes: str
    shots: List[DirectedShotSchema]


DIRECTOR_SYSTEM_INSTRUCTION = """
You are an expert Short Drama Film Director and AI Video Prompt Engineer optimized for Gemini Omni 1.2 Flash 9:16 vertical video.
Your goal is to turn a premise into an emotionally gripping 60-second micro-drama episode broken into 4 exact 15-second shots.

STRICT CONTINUITY & SPATIAL RULES:
1. 180-Degree Spatial Blocking:
   - Respect each character's locked default_screen_position (e.g., Char A SCREEN-RIGHT facing LEFT, Char B SCREEN-LEFT facing RIGHT).
   - Never cross the 180-degree axis across all 4 shots.
2. Two-Shots and Over-The-Shoulder (OTS):
   - Every shot must visually feature or anchor BOTH characters via Two-Shots, Over-the-Shoulder framing, or deep-focus staging. Avoid isolated single-character talking heads.
3. 4-Beat Structure (4 x 15s = 60s total):
   - Shot 1: Hook (0-15s) - Peak emotional or visual conflict entry.
   - Shot 2: Escalation (15-30s) - Direct confrontation, physical proximity, raising stakes.
   - Shot 3: Turn (30-45s) - Hidden truth revealed, sharp power shift, prop discovery.
   - Shot 4: Cliffhanger (45-60s) - Unanswered question, dramatic freeze or micro-expression, gasping cut.
4. Dialogue with Timestamps:
   - Provide realistic, punchy micro-drama dialogue with relative start_sec / end_sec within that 15s window (e.g., 1.5s to 6.5s) for accurate subtitle burning.
5. Camera Angles:
   - Alternate cleanly between "Angle A (Front)" and "Angle B (Reverse)" adhering to the locked location.
"""


def compile_final_prompt(raw_prompt: str, locked_lighting: str) -> str:
    """Appends strict lighting consistency string and audio/cut guardrails."""
    clean_raw = raw_prompt.strip().rstrip(".")
    clean_light = locked_lighting.strip().rstrip(".")
    mandatory_guardrails = (
        "NO background music, NO soundtrack, quiet room tone and realistic dialogue only, no text, no cuts."
    )
    if mandatory_guardrails.lower() in clean_raw.lower():
        return clean_raw
    return f"{clean_raw}. Lighting: {clean_light}. {mandatory_guardrails}"


def get_smart_fallback_script(
    series_title: str,
    episode_title: str,
    premise: str,
    char_a: Optional[Character],
    char_b: Optional[Character],
    loc: Optional[Location],
    locked_lighting: str,
) -> Dict[str, Any]:
    """Generates a dynamic, character-aware 4-beat micro-drama script when API key is offline or in mock mode."""
    char_a_name = char_a.name if char_a else "Protagonist"
    char_b_name = char_b.name if char_b else "Rival"
    pos_a = (char_a.default_screen_position if char_a else "RIGHT").upper()
    pos_b = (char_b.default_screen_position if char_b else "LEFT").upper()
    facing_a = "LEFT" if pos_a == "RIGHT" else "RIGHT"
    facing_b = "RIGHT" if pos_b == "LEFT" else "LEFT"
    loc_name = loc.name if loc else "Primary Set"

    shots = [
        {
            "shot_number": 1,
            "beat_name": "Hook (0-15s)",
            "camera_angle": "Angle A (Front)",
            "camera_movement": "Slow intense push-in at eye level, 9:16 vertical frame",
            "spatial_blocking": f"{char_a_name} SCREEN-{pos_a} facing {facing_a}; {char_b_name} SCREEN-{pos_b} facing {facing_b} stepping forward.",
            "props_continuity": "Sealed dossier folder in hand, distinctive watch/ring glint.",
            "dialogue_lines": [
                {
                    "speaker": char_b_name,
                    "text": f"Did you really think nobody would uncover your secret, {char_a_name}?",
                    "start_sec": 1.8,
                    "end_sec": 6.8,
                },
                {
                    "speaker": char_a_name,
                    "text": f"Lower your voice, {char_b_name}. You have no idea what you're holding.",
                    "start_sec": 8.0,
                    "end_sec": 13.5,
                },
            ],
            "raw_prompt": (
                f"9:16 vertical two-shot in {loc_name}. "
                f"{char_a_name} ({char_a.role_description if char_a else 'lead character'}) stands SCREEN-{pos_a} facing {facing_a}. "
                f"{char_b_name} ({char_b.role_description if char_b else 'rival'}) confronts them from SCREEN-{pos_b} facing {facing_b}, holding up a sealed dossier. "
                f"Context: {premise[:160]}. Slow steady camera push-in capturing intense eye contact."
            ),
        },
        {
            "shot_number": 2,
            "beat_name": "Escalation (15-30s)",
            "camera_angle": "Angle B (Reverse)",
            "camera_movement": f"Over-the-shoulder medium shot from behind {char_a_name} toward {char_b_name}",
            "spatial_blocking": f"OTS {char_a_name} on SCREEN-{pos_a}, focusing sharply on {char_b_name} on SCREEN-{pos_b}.",
            "props_continuity": "Dossier placed firmly onto table between both characters.",
            "dialogue_lines": [
                {
                    "speaker": char_b_name,
                    "text": "Everything changes tonight. Sign the transfer before midnight.",
                    "start_sec": 1.5,
                    "end_sec": 6.8,
                },
                {
                    "speaker": char_a_name,
                    "text": "And destroy the one safeguard protecting your own family?",
                    "start_sec": 8.2,
                    "end_sec": 13.8,
                },
            ],
            "raw_prompt": (
                f"9:16 vertical over-the-shoulder cinematic shot in {loc_name} Angle B reverse view. "
                f"Framed past {char_a_name}'s shoulder on SCREEN-{pos_a} directly at {char_b_name} on SCREEN-{pos_b}. "
                f"{char_b_name} smiles coldly, sliding the document forward. Subtle handheld camera tension."
            ),
        },
        {
            "shot_number": 3,
            "beat_name": "Turn (30-45s)",
            "camera_angle": "Angle A (Front)",
            "camera_movement": "Tight two-shot profile tracking shot with shallow depth of field",
            "spatial_blocking": f"{char_a_name} SCREEN-{pos_a} leans in closely; {char_b_name} SCREEN-{pos_b} reacts in visible shock.",
            "props_continuity": "Glowing smartphone screen revealing the counter-proof.",
            "dialogue_lines": [
                {
                    "speaker": char_a_name,
                    "text": "Check your phone. I already closed the deal twenty minutes ago.",
                    "start_sec": 1.8,
                    "end_sec": 7.4,
                },
                {
                    "speaker": char_b_name,
                    "text": "No... that's impossible. How did you—",
                    "start_sec": 8.8,
                    "end_sec": 13.2,
                },
            ],
            "raw_prompt": (
                f"9:16 vertical intimate profile two-shot in {loc_name}. "
                f"{char_a_name} on SCREEN-{pos_a} steps close to {char_b_name} on SCREEN-{pos_b}, "
                f"turning a glowing phone screen toward them. {char_b_name}'s confident expression shatters into shock."
            ),
        },
        {
            "shot_number": 4,
            "beat_name": "Cliffhanger (45-60s)",
            "camera_angle": "Angle B (Reverse)",
            "camera_movement": "Dynamic low-angle slow pull-out holding both figures in freeze-frame tension",
            "spatial_blocking": f"{char_a_name} SCREEN-{pos_a} turns slightly; {char_b_name} SCREEN-{pos_b} freezes as the entry door clicks open.",
            "props_continuity": "Phone lowered, shadowy silhouette entering through background doorway.",
            "dialogue_lines": [
                {
                    "speaker": char_a_name,
                    "text": "Decide right now: partner, or enemy?",
                    "start_sec": 1.2,
                    "end_sec": 5.8,
                },
                {
                    "speaker": char_b_name,
                    "text": f"{char_a_name}... look behind you.",
                    "start_sec": 7.8,
                    "end_sec": 12.2,
                },
            ],
            "raw_prompt": (
                f"9:16 vertical dramatic low-angle pull-out in {loc_name} Angle B reverse view. "
                f"{char_a_name} on SCREEN-{pos_a} starts to turn as {char_b_name} on SCREEN-{pos_b} gasps toward the doorway. "
                f"A dark silhouette steps into the frame behind them. Extreme micro-drama cliffhanger tension."
            ),
        },
    ]

    for s in shots:
        s["compiled_prompt"] = compile_final_prompt(s["raw_prompt"], locked_lighting)

    return {
        "outline_summary": (
            f"4-Beat Micro-Drama for '{episode_title}' ({series_title}): "
            f"{char_b_name} confronts {char_a_name}, triggering a sharp power reversal and a sudden doorway cliffhanger."
        ),
        "continuity_notes": (
            f"180° Axis Lock: {char_a_name} strictly SCREEN-{pos_a}, {char_b_name} strictly SCREEN-{pos_b}. "
            f"Carry dossier prop from Shot 1-2 and glowing phone prop from Shot 3-4 under identical locked lighting."
        ),
        "shots": shots,
    }


class DirectorService:

    @classmethod
    async def direct_episode(cls, episode_id: int, db: AsyncSession) -> Dict[str, Any]:
        """Generates 4x15s structured script & compiled prompts using Gemini structured output or smart director fallback."""
        result = await db.execute(
            select(Episode)
            .options(
                selectinload(Episode.series).selectinload(Series.characters),
                selectinload(Episode.series).selectinload(Series.locations),
                selectinload(Episode.shots),
            )
            .filter_by(id=episode_id)
        )
        episode = result.scalars().first()
        if not episode:
            raise ValueError(f"Episode {episode_id} not found")

        series = episode.series
        char_a = series.characters[0] if len(series.characters) > 0 else None
        char_b = series.characters[1] if len(series.characters) > 1 else char_a
        loc = series.locations[0] if series.locations else None

        script_data = None
        api_key = settings.GEMINI_API_KEY

        # Attempt calling Gemini text model with strict Pydantic structured output
        if api_key and api_key != "your_gemini_api_key_here" and genai is not None and not settings.MOCK_VIDEO_MODE:
            try:
                client = genai.Client(api_key=api_key)
                pos_a = char_a.default_screen_position if char_a else "RIGHT"
                pos_b = char_b.default_screen_position if char_b else "LEFT"

                prompt_content = f"""
Series Title: {series.title}
Episode Title: {episode.title}
Genre: {series.genre}
Series Premise: {series.premise}
Episode Premise: {episode.premise}
Locked Lighting: {series.locked_lighting}

Main Characters:
- Character A (LOCKED SCREEN-{pos_a}): {char_a.name if char_a else 'Char A'} ({char_a.role_description if char_a else ''}; {char_a.visual_tags if char_a else ''})
- Character B (LOCKED SCREEN-{pos_b}): {char_b.name if char_b else 'Char B'} ({char_b.role_description if char_b else ''}; {char_b.visual_tags if char_b else ''})

Primary Location: {loc.name if loc else 'Main Set'} ({loc.visual_tags if loc else ''})

Write the exact 4 shots (Shot 1 Hook 0-15s, Shot 2 Escalation 15-30s, Shot 3 Turn 30-45s, Shot 4 Cliffhanger 45-60s).
"""
                response = client.models.generate_content(
                    model=settings.DIRECTOR_MODEL,
                    contents=prompt_content,
                    config=types.GenerateContentConfig(
                        system_instruction=DIRECTOR_SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        response_schema=DirectorScriptSchema,
                    ),
                )
                if response.text:
                    parsed = json.loads(response.text)
                    if "shots" in parsed and len(parsed["shots"]) == 4:
                        for s in parsed["shots"]:
                            s["compiled_prompt"] = compile_final_prompt(s["raw_prompt"], series.locked_lighting)
                        script_data = parsed
            except Exception as e:
                print(f"[Director] Gemini LLM notice, using smart fallback: {e}")

        if not script_data:
            script_data = get_smart_fallback_script(
                series_title=series.title,
                episode_title=episode.title,
                premise=episode.premise,
                char_a=char_a,
                char_b=char_b,
                loc=loc,
                locked_lighting=series.locked_lighting,
            )

        # Clear existing shots if re-directing
        for old_shot in episode.shots:
            await db.delete(old_shot)
        await db.flush()

        # Persist episode outline & continuity notes
        episode.outline_summary = script_data.get("outline_summary")
        episode.continuity_notes = script_data.get("continuity_notes")

        # Insert the 4 new shots with exact structured dialogue_lines_json & props_continuity
        for s in script_data["shots"]:
            dialogue_lines = s.get("dialogue_lines", [])
            dialogue_text = "\n".join([f'{d["speaker"]}: "{d["text"]}"' for d in dialogue_lines])
            shot_obj = Shot(
                episode_id=episode.id,
                shot_number=s["shot_number"],
                beat_type=s["beat_name"],
                duration_sec=15,
                camera_angle=s["camera_angle"],
                camera_movement=s["camera_movement"],
                spatial_blocking=s["spatial_blocking"],
                props_continuity=s.get("props_continuity", ""),
                dialogue=dialogue_text,
                dialogue_lines_json=json.dumps(dialogue_lines),
                compiled_prompt=s["compiled_prompt"],
                pass1_status="pending",
                pass2_status="pending",
            )
            db.add(shot_obj)

        episode.status = "scripted"
        await db.commit()

        return {
            "status": "success",
            "outline_summary": episode.outline_summary,
            "continuity_notes": episode.continuity_notes,
            "episode_id": episode.id,
            "shots": script_data["shots"],
        }
