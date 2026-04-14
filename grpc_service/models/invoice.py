"""Invoice model for the invoice management system."""

import os
import sys
from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.sql import func

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.database import Base

class Invoice(Base):
    """Database model for an invoice."""
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, index=True)
    supplier = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String, default="pending")  # pending, paid, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
