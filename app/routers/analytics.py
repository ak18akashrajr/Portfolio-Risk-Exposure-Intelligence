from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.database import get_session
from app.services.analytics import calculate_risk_metrics, run_stress_test
from uuid import UUID

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/{portfolio_id}/risk")
def get_portfolio_risk(portfolio_id: UUID, session: Session = Depends(get_session)):
    return calculate_risk_metrics(session, portfolio_id)

@router.get("/{portfolio_id}/stress/{scenario}")
def get_stress_test(portfolio_id: UUID, scenario: str, session: Session = Depends(get_session)):
    return run_stress_test(session, portfolio_id, scenario)
