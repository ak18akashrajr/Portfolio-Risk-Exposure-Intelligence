from fastapi import APIRouter
from app.services.gold_silver import get_gold_silver_data

router = APIRouter(prefix="/commodities", tags=["commodities"])

@router.get("/gold-silver")
def get_gold_silver_ratio():
    return get_gold_silver_data()
