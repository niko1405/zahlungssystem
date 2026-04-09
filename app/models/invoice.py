from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.sql import func
from app.config.database import Base

class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(String, primary_key=True, index=True)
    supplier = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
