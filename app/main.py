from fastapi import FastAPI
from app.routers import invoice_router
from app.config.database import engine
from app.models import Base

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Invoice Service API",
    description="A FastAPI service for managing invoice metadata",
    version="1.0.0"
)

app.include_router(invoice_router.router)

@app.get("/")
async def root():
    return {"message": "Invoice Service API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
