from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
import datetime

from app.db.database import get_db
from app.db.models import User, CreditLedger
from app.config import settings

router = APIRouter()

class BalanceResponse(BaseModel):
    user_id: int
    name: str
    email: str
    credits_balance: int
    usd_equivalent: float
    rates: dict

class LedgerItem(BaseModel):
    id: int
    amount: int
    balance_after: int
    reason: str
    meta_info: Optional[str]
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class AddCreditsRequest(BaseModel):
    amount: int  # in credits

@router.get("/balance", response_model=BalanceResponse)
async def get_balance(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter_by(id=1))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return BalanceResponse(
        user_id=user.id,
        name=user.name,
        email=user.email,
        credits_balance=user.credits_balance,
        usd_equivalent=round(user.credits_balance * 0.01, 2),
        rates={
            "pass1_360p_usd": settings.PASS1_COST_USD,
            "pass2_720p_usd": settings.PASS2_COST_USD,
            "pass1_credits": settings.PASS1_CREDITS,
            "pass2_credits": settings.PASS2_CREDITS,
            "image_credits": settings.IMAGE_GEN_CREDITS
        }
    )

@router.get("/ledger", response_model=List[LedgerItem])
async def get_ledger(limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CreditLedger)
        .filter_by(user_id=1)
        .order_by(CreditLedger.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()

@router.post("/topup", response_model=BalanceResponse)
async def topup_credits(req: AddCreditsRequest, db: AsyncSession = Depends(get_db)):
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    result = await db.execute(select(User).filter_by(id=1))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.credits_balance += req.amount
    ledger = CreditLedger(
        user_id=user.id,
        amount=req.amount,
        balance_after=user.credits_balance,
        reason=f"Manual Balance Topup (+{req.amount} credits)",
        meta_info="Credit Purchase"
    )
    db.add(ledger)
    await db.commit()
    await db.refresh(user)

    return BalanceResponse(
        user_id=user.id,
        name=user.name,
        email=user.email,
        credits_balance=user.credits_balance,
        usd_equivalent=round(user.credits_balance * 0.01, 2),
        rates={
            "pass1_360p_usd": settings.PASS1_COST_USD,
            "pass2_720p_usd": settings.PASS2_COST_USD,
            "pass1_credits": settings.PASS1_CREDITS,
            "pass2_credits": settings.PASS2_CREDITS,
            "image_credits": settings.IMAGE_GEN_CREDITS
        }
    )
