"""Database operations and invoice management helpers.

This module provides helper functions for database operations used by
the gRPC server and payment service.
"""

import os
import sys
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# Add root directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logging_config import StructuredLogger

if TYPE_CHECKING:
    from grpc_service.models.invoice import Invoice


logger = StructuredLogger.for_module(__name__)


def get_invoice_or_none(db: Session, invoice_id: str) -> Optional["Invoice"]:
    """Retrieve an invoice by ID.
    
    Args:
        db: Database session
        invoice_id: Invoice ID to retrieve
        
    Returns:
        Invoice object or None if not found

    Raises:
        SQLAlchemyError: If the database query fails.
    """
    from grpc_service.models.invoice import Invoice
    
    try:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()

        if not invoice:
            logger.log_warning("Invoice not found", invoice_id=invoice_id)
            return None

        logger.log_debug("Invoice retrieved", invoice_id=invoice_id, status=invoice.status)
        return invoice
    except SQLAlchemyError as exc:
        logger.log_error("Failed to fetch invoice", exc_info=exc, invoice_id=invoice_id)
        raise


def create_invoice(
    db: Session,
    invoice_id: str,
    supplier: str,
    amount: float
) -> Optional["Invoice"]:
    """Create a new invoice.
    
    Validates that the invoice doesn't already exist before creating.
    
    Args:
        db: Database session
        invoice_id: Unique invoice ID
        supplier: Supplier name
        amount: Invoice amount
        
    Returns:
        Created Invoice object or None if already exists

    Raises:
        SQLAlchemyError: If the create transaction fails.
    """
    from grpc_service.models.invoice import Invoice
    
    try:
        existing = db.query(Invoice).filter(Invoice.id == invoice_id).first()

        if existing:
            logger.log_warning("Invoice already exists", invoice_id=invoice_id)
            return None

        invoice = Invoice(
            id=invoice_id,
            supplier=supplier,
            amount=amount,
            status="pending"
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)

        logger.log_db_operation(
            "CREATE",
            "invoice",
            status="SUCCESS",
            invoice_id=invoice_id,
            supplier=supplier,
            amount=amount
        )

        return invoice
    except SQLAlchemyError as exc:
        db.rollback()
        logger.log_error("Failed to create invoice", exc_info=exc, invoice_id=invoice_id)
        raise


def update_invoice(
    db: Session,
    invoice_id: str,
    supplier: Optional[str] = None,
    amount: Optional[float] = None
) -> Optional["Invoice"]:
    """Update an invoice.
    
    Args:
        db: Database session
        invoice_id: Invoice ID to update
        supplier: New supplier name (optional)
        amount: New amount (optional)
        
    Returns:
        Updated Invoice object or None if not found

    Raises:
        SQLAlchemyError: If the update transaction fails.
    """
    try:
        invoice = get_invoice_or_none(db, invoice_id)

        if not invoice:
            return None

        if supplier is not None:
            invoice.supplier = supplier
        if amount is not None:
            invoice.amount = amount

        db.commit()
        db.refresh(invoice)

        logger.log_db_operation(
            "UPDATE",
            "invoice",
            status="SUCCESS",
            invoice_id=invoice_id
        )

        return invoice
    except SQLAlchemyError as exc:
        db.rollback()
        logger.log_error("Failed to update invoice", exc_info=exc, invoice_id=invoice_id)
        raise


def update_invoice_status(
    db: Session,
    invoice_id: str,
    new_status: str
) -> Optional["Invoice"]:
    """Update only the status of an invoice.
    
    Args:
        db: Database session
        invoice_id: Invoice ID to update
        new_status: New status (pending, paid, cancelled)
        
    Returns:
        Updated Invoice or None if not found

    Raises:
        SQLAlchemyError: If the update transaction fails.
    """
    try:
        invoice = get_invoice_or_none(db, invoice_id)

        if not invoice:
            return None

        old_status = invoice.status
        invoice.status = new_status
        db.commit()
        db.refresh(invoice)

        logger.log_db_operation(
            "UPDATE",
            "invoice",
            status="SUCCESS",
            invoice_id=invoice_id,
            old_status=old_status,
            new_status=new_status
        )

        return invoice
    except SQLAlchemyError as exc:
        db.rollback()
        logger.log_error("Failed to update invoice status", exc_info=exc, invoice_id=invoice_id)
        raise


def delete_invoice(db: Session, invoice_id: str) -> bool:
    """Delete an invoice.
    
    Args:
        db: Database session
        invoice_id: Invoice ID to delete
        
    Returns:
        True if deleted, False if not found

    Raises:
        SQLAlchemyError: If the delete transaction fails.
    """
    try:
        invoice = get_invoice_or_none(db, invoice_id)

        if not invoice:
            return False

        db.delete(invoice)
        db.commit()

        logger.log_db_operation(
            "DELETE",
            "invoice",
            status="SUCCESS",
            invoice_id=invoice_id
        )

        return True
    except SQLAlchemyError as exc:
        db.rollback()
        logger.log_error("Failed to delete invoice", exc_info=exc, invoice_id=invoice_id)
        raise


def list_invoices(
    db: Session,
    skip: int = 0,
    limit: int = 100
) -> tuple[List["Invoice"], int]:
    """List invoices with pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        Tuple of (invoices list, total count)

    Raises:
        SQLAlchemyError: If list or count queries fail.
    """
    from grpc_service.models.invoice import Invoice
    
    try:
        invoices = db.query(Invoice).offset(skip).limit(limit).all()
        total = db.query(Invoice).count()

        logger.log_debug("Invoices listed", skip=skip, limit=limit, count=len(invoices), total=total)

        return invoices, total
    except SQLAlchemyError as exc:
        logger.log_error("Failed to list invoices", exc_info=exc, skip=skip, limit=limit)
        raise
