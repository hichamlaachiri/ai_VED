import asyncio
import httpx
from app.main import app

async def test_backend_routes():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Trigger startup event explicitly if needed
        from app.db.database import init_db, AsyncSessionLocal
        from app.db.models import User, CreditLedger
        from app.config import settings
        from sqlalchemy import select
        
        await init_db()
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(User).filter_by(id=1))
            if not res.scalars().first():
                user = User(id=1, email="director@microdrama.studio", name="Head Director", credits_balance=1000)
                session.add(user)
                session.add(CreditLedger(user_id=1, amount=1000, balance_after=1000, reason="Initial Bonus"))
                await session.commit()
                
        # 1. Health check
        r = await client.get("/health")
        print("Health status:", r.status_code, r.json())
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"
        
        # 2. Billing balance
        r = await client.get("/api/billing/balance")
        print("Balance check:", r.status_code, r.json())
        assert r.status_code == 200
        assert r.json()["credits_balance"] >= 1000
        
        # 3. Create a series
        payload = {
            "title": "The Billionaire's Secret Identity",
            "premise": "An undercover heir runs an elevator service at a megacorp.",
            "genre": "Suspense Thriller",
            "characters": [
                {
                    "name": "Marcus Kane",
                    "role_description": "Undercover heir, discreet suit",
                    "visual_tags": "sharp eyes, navy blazer",
                    "default_screen_position": "RIGHT"
                },
                {
                    "name": "Victoria Croft",
                    "role_description": "Corporate Auditor",
                    "visual_tags": "crimson dress, gold watch",
                    "default_screen_position": "LEFT"
                }
            ],
            "location": {
                "name": "Executive Boardroom",
                "visual_tags": "Dark oak table, floor-to-ceiling glass, sunset"
            }
        }
        r = await client.post("/api/series", json=payload)
        print("Create series:", r.status_code, r.json()["title"])
        assert r.status_code == 200
        series_id = r.json()["id"]
        
        # 4. List series
        r = await client.get("/api/series")
        print("List series count:", len(r.json()))
        assert len(r.json()) >= 1
        
        # 5. Cost estimate
        r = await client.get("/api/shots/estimate?shot_count=4")
        print("Render estimate:", r.status_code, r.json())
        assert r.status_code == 200
        assert r.json()["duration_total_sec"] == 60

        print("--- ALL BACKEND CHECKS PASSED SUCCESSFULLY! ---")

if __name__ == "__main__":
    asyncio.run(test_backend_routes())
