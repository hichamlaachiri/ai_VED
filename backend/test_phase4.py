import asyncio
import os
from pathlib import Path
import httpx

os.environ["MOCK_VIDEO_MODE"] = "true"

from app.main import app
from app.db.database import init_db, AsyncSessionLocal
from app.db.models import User, Series, Character, Location, Episode, Shot
from sqlalchemy import select

async def run_phase4_end_to_end_test():
    await init_db()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Reset user balance
        async with AsyncSessionLocal() as session:
            u_res = await session.execute(select(User).filter_by(id=1))
            user = u_res.scalars().first()
            if not user:
                user = User(id=1, email="director@microdrama.studio", name="Head Director", credits_balance=2000)
                session.add(user)
            else:
                user.credits_balance = 2000
            await session.commit()

        # 2. Create Series with locked constraints
        series_payload = {
            "title": "Crown of Shadows",
            "premise": "A disgraced royal advisor corners the usurper queen in her private armory.",
            "genre": "Royal Revenge Drama",
            "locked_lighting": "Subtle candlelight with dramatic amber rim light, dark moody royal chamber",
            "characters": [
                {"name": "Cassian", "role_description": "Exiled royal strategist", "visual_tags": "scarred cheek, velvet hooded cloak", "default_screen_position": "RIGHT"},
                {"name": "Queen Vanya", "role_description": "The usurper monarch", "visual_tags": "golden diadem, embroidered corset", "default_screen_position": "LEFT"}
            ],
            "location": {"name": "The Royal Armory", "visual_tags": "Display cases with ornate swords, arched stone vaults"}
        }
        res = await client.post("/api/series", json=series_payload)
        assert res.status_code == 200, res.text
        series_id = res.json()["id"]
        print(f"1. Created Series #{series_id}: {res.json()['title']}")

        # 3. Create Episode
        ep_payload = {
            "series_id": series_id,
            "title": "Episode 1: The Queen's Gambit",
            "premise": "Cassian reveals the royal seal was never destroyed."
        }
        res = await client.post("/api/episodes", json=ep_payload)
        episode_id = res.json()["id"]
        print(f"2. Created Episode #{episode_id}: {res.json()['title']}")

        # 4. Auto-direct 4-beat script
        res = await client.post(f"/api/episodes/{episode_id}/auto-direct")
        assert res.status_code == 200, res.text
        script_shots = res.json()["shots"]
        assert len(script_shots) == 4
        print(f"3. Auto-directed 4 shots with 180-deg spatial blocking and dialogue timestamps.")

        # 5. Batch render Pass 1 (360p draft)
        res = await client.post(f"/api/episodes/{episode_id}/render-pass1")
        assert res.status_code == 200, res.text
        print("4. Pass 1 Draft clips rendered.")

        # 6. Assemble Full Episode with FFmpeg
        print("5. Running FFmpeg Auto-Assembly Pipeline...")
        res = await client.post(f"/api/episodes/{episode_id}/assemble")
        assert res.status_code == 200, res.text
        assembly_result = res.json()
        print("Assembly output:", assembly_result)

        assert assembly_result["status"] == "completed"
        assert assembly_result["duration_sec"] >= 60.0
        assert assembly_result["file_size_mb"] > 0.1
        final_video_url = assembly_result["final_video_url"]
        print(f"Final Master Episode URL: {final_video_url}")

        # Check physical file exists (strip cache-busting query string)
        clean_video_path = final_video_url.split("?", 1)[0].lstrip("/")
        local_file_path = Path("backend") / clean_video_path
        if not local_file_path.exists():
            local_file_path = Path(clean_video_path)
        print(f"Final MP4 file exists on disk: {local_file_path.exists()}, size: {local_file_path.stat().st_size} bytes")
        assert local_file_path.exists()
        assert local_file_path.stat().st_size > 50000

        # Verify Episode model state
        res = await client.get(f"/api/episodes/{episode_id}")
        ep_data = res.json()
        assert ep_data["status"] == "assembled"
        assert ep_data["final_video_url"] is not None

        print("\n--- PHASE 4 END-TO-END VERIFICATION PASSED WITH 100% SUCCESS! ---")

if __name__ == "__main__":
    asyncio.run(run_phase4_end_to_end_test())
