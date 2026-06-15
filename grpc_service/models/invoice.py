"""Invoice model for the invoice management system."""

import os
import sys
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.database import Base

class Invoice(Base):
    """Schlanke Datenbank für Duplikatsprüfung und globales Status-Tracking."""
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, index=True)
    supplier = Column(String, nullable=False, index=True)
    customer_number = Column(String, nullable=True)
    amount_gross = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, validated, approved, erp_exported, rejected
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
