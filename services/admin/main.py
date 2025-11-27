from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db

app = FastAPI(title="Admin Service")


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Admin Service is running"}


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    await db.execute("SELECT 1")
    return {"status": "healthy", "database": "connected"}
