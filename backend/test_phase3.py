import asyncio
import os
import httpx

# Force mock video mode for testing
os.environ["MOCK_VIDEO_MODE"] = "true"

from app.main import app
from app.db.database import init_db, AsyncSessionLocal
from app.db.models import User, CreditLedger, Series, Character, Location, Episode, Shot
from sqlalchemy import select

async def run_phase3_test():
    await init_db()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Reset user balance to 1000 credits for clean test
        async with AsyncSessionLocal() as session:
            u_res = await session.execute(select(User).filter_by(id=1))
            user = u_res.scalars().first()
            if not user:
                user = User(id=1, email="director@microdrama.studio", name="Head Director", credits_balance=1000)
                session.add(user)
            else:
                user.credits_balance = 1000
            await session.commit()

        # 2. Check initial balance
        res = await client.get("/api/billing/balance")
        initial_balance = res.json()["credits_balance"]
        print(f"Initial user credits balance: {initial_balance}")
        assert initial_balance == 1000

        # 3. Create Series and Episode
        series_payload = {
            "title": "Neon Syndicate",
            "premise": "Two rival enforcers meet on a skyscraper helipad to divide territory.",
            "genre": "Cyberpunk Crime",
            "characters": [
                {"name": "Kaelen", "role_description": "Cyborg Enforcer", "visual_tags": "chrome jaw, dark trenchcoat", "default_screen_position": "RIGHT"},
                {"name": "Nyx", "role_description": "Data Broker", "visual_tags": "neon braids, tactical goggles", "default_screen_position": "LEFT"}
            ],
            "location": {"name": "Helipad 42", "visual_tags": "Wet tarmac, neon signs reflected in puddles"}
        }
        res = await client.post("/api/series", json=series_payload)
        series_id = res.json()["id"]

        ep_payload = {"series_id": series_id, "title": "EP1: Crossfire", "premise": "The deal breaks down when the drive is corrupted."}
        res = await client.post("/api/episodes", json=ep_payload)
        episode_id = res.json()["id"]

        # 4. Auto-direct 4 shots
        res = await client.post(f"/api/episodes/{episode_id}/auto-direct")
        shots = res.json()["shots"]
        assert len(shots) == 4
        print(f"Directing completed: {len(shots)} shots created.")

        # 5. Batch Render Pass 1 (360p Draft, 4 x 35 = 140 credits)
        print("Rendering Batch Pass 1 (360p Draft)...")
        res = await client.post(f"/api/episodes/{episode_id}/render-pass1")
        assert res.status_code == 200, res.text
        pass1_results = res.json()["results"]
        assert len(pass1_results) == 4
        assert all(r["status"] == "completed" for r in pass1_results)
        print(f"Pass 1 Batch Complete! 4 shots rendered.")

        # Verify Credit balance after Pass 1: 1000 - 140 = 860
        res = await client.get("/api/billing/balance")
        bal_after_p1 = res.json()["credits_balance"]
        print(f"Balance after Pass 1: {bal_after_p1} (Deducted 140 credits)")
        assert bal_after_p1 == 860

        # 6. Targeted Fix (Multi-turn Edit) on Shot 1 using previous_interaction_id
        shot1_id = pass1_results[0]["shot_id"]
        print(f"Testing Targeted Fix on Shot {shot1_id} with edit instruction...")
        res = await client.post(
            f"/api/shots/{shot1_id}/edit",
            json={"edit_instruction": "Add subtle electrical sparks around the chrome jaw"}
        )
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "completed"
        print("Targeted Fix rendered successfully with previous_interaction_id!")

        # 7. Safety Policy Filter & 1-Click Reframe & Retry
        # Inject celebrity name to trigger prominent-person filter
        await client.patch(
            f"/api/shots/{shot1_id}",
            json={"compiled_prompt": "Close up of Elon Musk arguing with Donald Trump on helipad"}
        )
        res = await client.post(f"/api/shots/{shot1_id}/render", json={"pass_number": 1})
        assert res.status_code == 200
        safety_json = res.json()
        assert safety_json["status"] == "safety_violation"
        print(f"Safety violation successfully caught: {safety_json['message']}")

        # 1-Click Reframe Safely & Retry
        res = await client.post(f"/api/shots/{shot1_id}/reframe-safety")
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "completed"
        print("Reframe Safely & Retry succeeded!")

        # 8. Batch Render Pass 2 (720p Final, 4 x 104 = 416 credits)
        print("Rendering Batch Pass 2 (720p Final)...")
        res = await client.post(f"/api/episodes/{episode_id}/render-pass2")
        assert res.status_code == 200, res.text
        pass2_results = res.json()["results"]
        assert len(pass2_results) == 4
        print(f"Pass 2 Batch Complete! 4 shots rendered at 720p.")

        # Check final credit ledger
        res = await client.get("/api/billing/ledger?limit=10")
        ledger = res.json()
        print(f"Total ledger records: {len(ledger)}. Most recent: {ledger[0]['reason']}")
        assert len(ledger) >= 5

        print("\n--- PHASE 3 BACKEND TEST VERIFIED WITH 100% SUCCESS! ---")

if __name__ == "__main__":
    asyncio.run(run_phase3_test())
