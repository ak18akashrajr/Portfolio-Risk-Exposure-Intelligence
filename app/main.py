from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import create_db_and_tables
from app.routers import portfolio, analytics, commodities

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(title="Portfolio Risk Intelligence Platform", lifespan=lifespan)

app.include_router(portfolio.router)
app.include_router(analytics.router)
app.include_router(commodities.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Portfolio Risk Intelligence Platform (India-Focused)"}
