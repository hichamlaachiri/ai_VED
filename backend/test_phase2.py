import asyncio
import httpx
from app.main import app
from app.db.database import init_db

async def test_phase2():
    await init_db()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Create a Series
        series_payload = {
            "title": "Vengeance of the Concubine",
            "premise": "An exiled heiress returns in disguise to confront the CEO who ruined her family dynasty.",
            "genre": "Revenge Thriller",
            "characters": [
                {
                    "name": "Alexander Sterling",
                    "role_description": "Cold Ruthless CEO",
                    "visual_tags": "Slicked back black hair, tailored charcoal three-piece suit, platinum watch",
                    "default_screen_position": "RIGHT"
                },
                {
                    "name": "Mei Lin",
                    "role_description": "Undercover Heiress",
                    "visual_tags": "Long silk evening dress, ruby pendant, piercing cold gaze",
                    "default_screen_position": "LEFT"
                }
            ],
            "location": {
                "name": "The High-Rise Glass Penthouse",
                "visual_tags": "Floor-to-ceiling glass, rainy midnight cityscape, polished marble flooring"
            }
        }
        res = await client.post("/api/series", json=series_payload)
        assert res.status_code == 200, res.text
        series_data = res.json()
        series_id = series_data["id"]
        char_a_id = series_data["characters"][0]["id"]
        print(f"Created Series #{series_id}: {series_data['title']}")

        # 2. Generate all 6 visual bible assets
        res = await client.post(f"/api/series/{series_id}/visual-bible/generate-all")
        assert res.status_code == 200, res.text
        assets = res.json()["assets"]
        print(f"Generated Visual Bible Assets: {list(assets.keys())}")
        assert len(assets) == 6

        # 3. Regenerate a single asset (Char A portrait)
        res = await client.post(
            f"/api/series/{series_id}/visual-bible/regenerate-asset",
            json={"asset_type": "char_portrait", "target_id": char_a_id}
        )
        assert res.status_code == 200, res.text
        print("Regenerated single asset URL:", res.json()["url"])

        # 4. Create an episode
        ep_payload = {
            "series_id": series_id,
            "title": "Episode 1: The Midnight Gala",
            "premise": "Mei Lin corners Alexander by the panoramic window, revealing the stolen ledger."
        }
        res = await client.post("/api/episodes", json=ep_payload)
        assert res.status_code == 200, res.text
        episode_id = res.json()["id"]
        print(f"Created Episode #{episode_id}: {res.json()['title']}")

        # 5. Auto-Direct 4-Beat Script & Prompt Compiler
        res = await client.post(f"/api/episodes/{episode_id}/auto-direct")
        assert res.status_code == 200, res.text
        script = res.json()
        assert len(script["shots"]) == 4
        print(f"Directing completed! Generated {len(script['shots'])} shots:")
        for s in script["shots"]:
            print(f" - Shot {s['shot_number']} [{s['beat_name']}]: Angle={s['camera_angle']}, Blocking={s['spatial_blocking'][:40]}...")
            assert "NO background music, NO soundtrack, quiet room tone and realistic dialogue only, no text, no cuts." in s["compiled_prompt"]
            print(f"   Compiled prompt ends correctly with guardrails.")

        # 6. Verify Episode retrieval with shots from DB
        res = await client.get(f"/api/episodes/{episode_id}")
        assert res.status_code == 200
        ep_with_shots = res.json()
        assert len(ep_with_shots["shots"]) == 4
        assert ep_with_shots["status"] == "scripted"

        print("\n--- PHASE 2 BACKEND TEST VERIFIED WITH 100% SUCCESS! ---")

if __name__ == "__main__":
    asyncio.run(test_phase2())
